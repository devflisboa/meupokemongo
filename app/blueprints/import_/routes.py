from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from . import bp
from ...services.import_service import (
    detect_format, parse_pokegenie, parse_csv, parse_json,
    store_import_session, load_import_session, apply_import,
)


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("Nenhum arquivo enviado.", "warning")
            return redirect(request.url)

        raw = file.read()
        ext = file.filename.rsplit(".", 1)[-1].lower()
        fmt = detect_format(raw, ext)

        if fmt == "pokegenie":
            rows, errors = parse_pokegenie(raw)
        elif fmt == "csv":
            rows, errors = parse_csv(raw)
        elif fmt == "json":
            rows, errors = parse_json(raw)
        else:
            flash("Formato não suportado. Use CSV do PokeGenie ou JSON.", "danger")
            return redirect(request.url)

        if not rows and errors:
            flash(f"Arquivo inválido: {errors[0]}", "danger")
            return redirect(request.url)

        # Armazena no banco para evitar limite de cookie em imports grandes
        key = store_import_session(current_user.id, rows, fmt)
        session["import_key"] = key

        return render_template("import_/preview.html", rows=rows, errors=errors, fmt=fmt)

    return render_template("import_/index.html")


@bp.route("/confirmar", methods=["POST"])
@login_required
def confirmar():
    key = session.pop("import_key", None)
    if not key:
        flash("Sessão expirada. Envie o arquivo novamente.", "warning")
        return redirect(url_for("import_.index"))

    rows, fmt = load_import_session(key)
    if not rows:
        flash("Nenhum dado para importar.", "warning")
        return redirect(url_for("import_.index"))

    report = apply_import(current_user.id, rows)
    flash(
        f"Importação concluída: {report['created']} Pokémon adicionados, "
        f"{report['updated']} atualizados.",
        "success",
    )
    return redirect(url_for("collection.index"))
