from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from . import bp
from ...extensions import db
from ...models.user import User
from ...services.collection_service import get_collection_stats


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db.session.query(User).filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(request.args.get("next") or url_for("main.index"))
        flash("Usuário ou senha incorretos.", "danger")
    return render_template("auth/login.html")


@bp.route("/registro", methods=["GET", "POST"])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        trainer_code = request.form.get("trainer_code", "").strip() or None
        if db.session.query(User).filter_by(username=username).first():
            flash("Nome de usuário já em uso.", "warning")
            return render_template("auth/registro.html")
        if db.session.query(User).filter_by(email=email).first():
            flash("E-mail já cadastrado.", "warning")
            return render_template("auth/registro.html")
        user = User(username=username, email=email, trainer_code=trainer_code)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Conta criada com sucesso! Bem-vindo, treinador!", "success")
        return redirect(url_for("main.index"))
    return render_template("auth/registro.html")


@bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "dados":
            email = request.form.get("email", "").strip()
            trainer_code = request.form.get("trainer_code", "").strip() or None
            visibility = request.form.get("visibility", "public")
            if visibility not in ("public", "friends", "private"):
                visibility = "public"

            if email != current_user.email:
                if db.session.query(User).filter(
                    User.email == email, User.id != current_user.id
                ).first():
                    flash("E-mail já está em uso por outro treinador.", "warning")
                    return redirect(url_for("auth.perfil"))

            current_user.email = email
            current_user.trainer_code = trainer_code
            current_user.visibility = visibility
            db.session.commit()
            flash("Perfil atualizado com sucesso!", "success")

        elif action == "senha":
            current_pwd = request.form.get("current_password", "")
            new_pwd = request.form.get("new_password", "")
            if not current_user.check_password(current_pwd):
                flash("Senha atual incorreta.", "danger")
                return redirect(url_for("auth.perfil"))
            if len(new_pwd) < 8:
                flash("A nova senha deve ter pelo menos 8 caracteres.", "warning")
                return redirect(url_for("auth.perfil"))
            current_user.set_password(new_pwd)
            db.session.commit()
            flash("Senha alterada com sucesso!", "success")

        return redirect(url_for("auth.perfil"))

    stats = get_collection_stats(current_user.id)
    return render_template("auth/perfil.html", stats=stats)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))
