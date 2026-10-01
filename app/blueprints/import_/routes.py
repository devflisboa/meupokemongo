from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from . import bp
from ...services.import_service import parse_csv, parse_json, apply_import


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("Nenhum arquivo enviado.", "warning")
            return redirect(request.url)

        raw = file.read()
        ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""

        if ext == "csv":
            rows, errors = parse_csv(raw)
        elif ext == "json":
            rows, errors = parse_json(raw)
        else:
            flash("Formato não suportado. Use CSV ou JSON.", "danger")
            return redirect(request.url)

        # Guarda preview na sessão para confirmação
        session["import_preview"] = rows
        session["import_errors"] = errors
        return render_template("import_/preview.html", rows=rows, errors=errors)

    return render_template("import_/index.html")


@bp.route("/confirmar", methods=["POST"])
@login_required
def confirmar():
    rows = session.pop("import_preview", [])
    if not rows:
        flash("Sessão expirada. Envie o arquivo novamente.", "warning")
        return redirect(url_for("import_.index"))

    report = apply_import(current_user.id, rows)
    flash(f"Importação concluída: {report['created']} criados, {report['updated']} atualizados.", "success")
    return redirect(url_for("collection.index"))
