import shutil
import uuid
from pathlib import Path

from flask import render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_required, current_user

from . import bp
from ...extensions import db, limiter
from ...models.pokemon import Species, Form
from ...models.individual import UserPokemon
from ...models.collection import UserCollection
from ...services.ocr_service import process_images, build_name_index
from ...config import now_br

_ALLOWED = {"jpg", "jpeg", "png", "webp"}
_MAX_BYTES = 10 * 1024 * 1024
_MAX_FILES = 10


def _allowed(name: str) -> bool:
    return "." in name and name.rsplit(".", 1)[-1].lower() in _ALLOWED


def _thumb_dir(key: str) -> Path:
    d = Path(current_app.static_folder) / "scan_temp" / key
    d.mkdir(parents=True, exist_ok=True)
    return d


@bp.route("/", methods=["GET"])
@login_required
def index():
    return render_template("scan/index.html")


@bp.route("/upload", methods=["POST"])
@login_required
@limiter.limit("5 per minute; 30 per hour")
def upload():
    files = request.files.getlist("files")
    valid: list[bytes] = []

    for f in files[:_MAX_FILES]:
        if not f.filename or not _allowed(f.filename):
            flash(f"'{f.filename}' não é suportado (JPG/PNG/WebP).", "warning")
            continue
        data = f.read()
        if len(data) > _MAX_BYTES:
            flash(f"'{f.filename}' excede 10 MB.", "warning")
            continue
        valid.append(data)

    if not valid:
        flash("Nenhuma imagem válida enviada.", "warning")
        return redirect(url_for("scan.index"))

    species_all = db.session.query(Species).all()
    name_index = build_name_index(species_all)

    key = uuid.uuid4().hex
    results = process_images(valid, name_index, thumb_dir=_thumb_dir(key))

    session["scan_key"] = key
    session["scan_results"] = [r.to_dict() for r in results]
    return redirect(url_for("scan.preview"))


@bp.route("/preview")
@login_required
def preview():
    results = session.get("scan_results")
    if not results:
        flash("Sessão expirada. Envie as imagens novamente.", "warning")
        return redirect(url_for("scan.index"))

    species_all = db.session.query(Species).order_by(Species.id).all()
    return render_template("scan/preview.html", results=results, species_all=species_all)


@bp.route("/confirmar", methods=["POST"])
@login_required
def confirmar():
    results = session.pop("scan_results", None)
    key = session.pop("scan_key", None)

    if not results:
        flash("Sessão expirada.", "warning")
        return redirect(url_for("scan.index"))

    saved = skipped = 0
    today = now_br().strftime("%Y-%m-%d")

    for i in range(len(results)):
        if request.form.get(f"skip_{i}"):
            skipped += 1
            continue

        species_id = request.form.get(f"species_id_{i}", type=int)
        if not species_id:
            skipped += 1
            continue

        form = (
            db.session.query(Form).filter_by(species_id=species_id, form_name="normal").first()
            or db.session.query(Form).filter_by(species_id=species_id).first()
        )
        if not form:
            skipped += 1
            continue

        cp       = request.form.get(f"cp_{i}", type=int)
        hp_max   = request.form.get(f"hp_max_{i}", type=int)
        atk_iv   = request.form.get(f"atk_iv_{i}", type=int)
        def_iv   = request.form.get(f"def_iv_{i}", type=int)
        sta_iv   = request.form.get(f"sta_iv_{i}", type=int)
        is_shiny = bool(request.form.get(f"is_shiny_{i}"))

        iv_pct = None
        if all(v is not None for v in [atk_iv, def_iv, sta_iv]):
            iv_pct = round((atk_iv + def_iv + sta_iv) / 45 * 100, 1)

        poke = UserPokemon(
            user_id=current_user.id,
            form_id=form.id,
            source="scan",
            cp=cp,
            hp=hp_max,
            atk_iv=atk_iv,
            def_iv=def_iv,
            sta_iv=sta_iv,
            iv_pct=iv_pct,
            is_shiny=is_shiny,
            scan_date=today,
        )
        db.session.add(poke)

        col = db.session.query(UserCollection).filter_by(
            user_id=current_user.id, form_id=form.id
        ).first()
        if not col:
            col = UserCollection(user_id=current_user.id, form_id=form.id)
            db.session.add(col)

        col.owned = True
        col.quantity = (col.quantity or 0) + 1
        if is_shiny:
            col.has_shiny = True
            col.shiny_qty = (col.shiny_qty or 0) + 1
        if iv_pct == 100.0:
            col.has_perfect = True

        saved += 1

    db.session.commit()

    # Limpa thumbnails
    if key:
        shutil.rmtree(
            Path(current_app.static_folder) / "scan_temp" / key,
            ignore_errors=True,
        )

    msg = f"{saved} Pokémon catalogado{'s' if saved != 1 else ''}."
    if skipped:
        msg += f" {skipped} pulado{'s' if skipped != 1 else ''}."
    flash(msg, "success" if saved else "warning")
    return redirect(url_for("collection.index"))
