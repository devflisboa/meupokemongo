from io import BytesIO
from flask import render_template, redirect, url_for, flash, request, abort, make_response
from flask_login import login_user, logout_user, login_required, current_user
from . import bp
from ...extensions import db
from ...models.user import User
from ...models.friendship import Friendship
from ...models.collection import UserCollection
from ...models.pokemon import Form
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

        elif action == "avatar":
            file = request.files.get("avatar")
            if not file or not file.filename:
                flash("Nenhum arquivo selecionado.", "warning")
                return redirect(url_for("auth.perfil"))
            allowed = {"image/jpeg", "image/png", "image/webp"}
            mime = file.content_type or ""
            if mime not in allowed:
                flash("Formato inválido. Use JPEG, PNG ou WebP.", "warning")
                return redirect(url_for("auth.perfil"))
            raw = file.read()
            if len(raw) > 2 * 1024 * 1024:
                flash("Imagem muito grande. Máximo 2 MB.", "warning")
                return redirect(url_for("auth.perfil"))
            try:
                from PIL import Image
                img = Image.open(BytesIO(raw)).convert("RGB")
                w, h = img.size
                side = min(w, h)
                img = img.crop(((w - side) // 2, (h - side) // 2,
                                (w + side) // 2, (h + side) // 2))
                img = img.resize((200, 200), Image.LANCZOS)
                buf = BytesIO()
                img.save(buf, format="JPEG", quality=85)
                current_user.avatar = buf.getvalue()
                current_user.avatar_mime = "image/jpeg"
                db.session.commit()
                flash("Foto de perfil atualizada!", "success")
            except Exception:
                flash("Erro ao processar a imagem.", "danger")

        return redirect(url_for("auth.perfil"))

    stats = get_collection_stats(current_user.id)
    return render_template("auth/perfil.html", stats=stats)


@bp.route("/treinador/<username>")
def perfil_publico(username: str):
    profile_user = db.session.query(User).filter_by(username=username).first_or_404()

    # Redireciona para o próprio perfil se for o usuário logado
    if current_user.is_authenticated and current_user.id == profile_user.id:
        return redirect(url_for("auth.perfil"))

    # Verifica visibilidade
    can_view = False
    if profile_user.visibility == "public":
        can_view = True
    elif profile_user.visibility == "friends" and current_user.is_authenticated:
        friendship = db.session.query(Friendship).filter(
            db.or_(
                db.and_(
                    Friendship.requester_id == current_user.id,
                    Friendship.addressee_id == profile_user.id,
                ),
                db.and_(
                    Friendship.requester_id == profile_user.id,
                    Friendship.addressee_id == current_user.id,
                ),
            ),
            Friendship.status == "accepted",
        ).first()
        can_view = friendship is not None

    if not can_view:
        abort(403)

    stats = get_collection_stats(profile_user.id)

    # Primeiros 24 Pokémon capturados
    sample_owned = (
        db.session.query(Form)
        .join(UserCollection, UserCollection.form_id == Form.id)
        .filter(
            UserCollection.user_id == profile_user.id,
            UserCollection.owned.is_(True),
            UserCollection.quantity > 0,
        )
        .order_by(Form.species_id)
        .limit(24)
        .all()
    )

    # Pokémon disponíveis para troca
    trade_forms = (
        db.session.query(Form)
        .join(UserCollection, UserCollection.form_id == Form.id)
        .filter(
            UserCollection.user_id == profile_user.id,
            UserCollection.owned.is_(True),
            UserCollection.for_trade.is_(True),
        )
        .order_by(Form.species_id)
        .all()
    )

    return render_template(
        "auth/perfil_publico.html",
        profile_user=profile_user,
        stats=stats,
        sample_owned=sample_owned,
        trade_forms=trade_forms,
    )


@bp.route("/avatar/<int:user_id>")
def avatar(user_id: int):
    user = db.session.get(User, user_id)
    if not user or not user.avatar:
        abort(404)
    resp = make_response(user.avatar)
    resp.headers["Content-Type"] = user.avatar_mime or "image/jpeg"
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))
