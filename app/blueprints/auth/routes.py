from io import BytesIO
from flask import render_template, redirect, url_for, flash, request, abort, make_response
from flask_login import login_user, logout_user, login_required, current_user
from . import bp
from ...extensions import db, limiter
from ...models.user import User
from ...models.collection import UserCollection
from ...models.pokemon import Form
from ...services.collection_service import get_collection_stats
from ...services.profile_service import (
    resolve_city, normalize_whatsapp, format_whatsapp, delete_account,
)


def resolve_species(raw: str) -> int | None:
    """'#025 Pikachu', '25' ou 'pikachu' → 25. None se não achar."""
    from ...models.pokemon import Species
    raw = raw.strip()
    digits = raw.lstrip("#").split(" ")[0]
    if digits.isdigit():
        sp = db.session.get(Species, int(digits))
        return sp.id if sp else None
    key = raw.lower().replace(" ", "-")
    sp = db.session.query(Species).filter(
        db.or_(db.func.lower(Species.name_pt) == raw.lower(), db.func.lower(Species.name) == key)
    ).first()
    return sp.id if sp else None


def _apply_trade_profile(user, form) -> str | None:
    """
    Aplica os campos do perfil de troca (#23) vindos de um formulário.
    Retorna mensagem de erro ou None. Campos ausentes do form não são alterados.
    """
    if "trainer_code" in form:
        raw = form.get("trainer_code", "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if raw and (len(digits) != 12 or any(ch.isalpha() for ch in raw)):
            return "O código de amigo tem 12 números (ex.: 1234 5678 9012)."
        # formato padrão do jogo: 1234 5678 9012
        user.trainer_code = f"{digits[:4]} {digits[4:8]} {digits[8:]}" if digits else None

    if "state" in form or "city" in form:
        state, city = form.get("state", "").strip(), form.get("city", "").strip()
        if state or city:
            uf, name = resolve_city(state, city)
            if not uf:
                return "Cidade não encontrada para o estado escolhido. Escolha uma opção da lista."
            user.state, user.city = uf, name
        else:
            user.state = user.city = None

    if "favorite" in form:
        raw = form.get("favorite", "").strip()
        if raw:
            species_id = resolve_species(raw)
            if not species_id:
                return "Pokémon favorito não encontrado. Escolha uma opção da lista."
            user.favorite_species_id = species_id
        else:
            user.favorite_species_id = None

    if "trade_profile" in form:  # checkboxes: ausentes = desmarcados
        user.visibility = "public" if form.get("show_in_trades") == "on" else "private"
        user.can_trade_remote = form.get("can_trade_remote") == "on"
        allow = form.get("allow_whatsapp") == "on"
        raw = form.get("whatsapp", "").strip()
        if raw:
            number = normalize_whatsapp(raw)
            if not number:
                return "WhatsApp inválido. Use DDD + número, ex.: (85) 99999-1234."
            user.whatsapp = number
        elif not allow:
            user.whatsapp = None
        if allow and not user.whatsapp:
            return "Informe o número para liberar o contato por WhatsApp."
        user.allow_whatsapp = allow
    return None


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute;60 per hour", methods=["POST"])  # anti força bruta
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
@limiter.limit("5 per hour", methods=["POST"])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if db.session.query(User).filter_by(username=username).first():
            flash("Nome de usuário já em uso.", "warning")
            return render_template("auth/registro.html")
        if db.session.query(User).filter_by(email=email).first():
            flash("E-mail já cadastrado.", "warning")
            return render_template("auth/registro.html")
        user = User(username=username, email=email)  # código de amigo vem no onboarding
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Conta criada! Falta só um passo para aparecer nas trocas.", "success")
        return redirect(url_for("auth.onboarding"))
    return render_template("auth/registro.html")


@bp.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    """Perfil de troca em 1 tela curta: código de amigo → cidade → contato."""
    if request.method == "POST":
        error = _apply_trade_profile(current_user, request.form)
        if error:
            db.session.rollback()
            flash(error, "warning")
            return render_template("auth/onboarding.html", form=request.form)
        db.session.commit()
        flash("Pronto! Agora outros treinadores encontram você nas trocas.", "success")
        return redirect(url_for("wishlist.index"))
    return render_template("auth/onboarding.html", form=None)


@bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "dados":
            email = request.form.get("email", "").strip()
            if email != current_user.email:
                if db.session.query(User).filter(
                    User.email == email, User.id != current_user.id
                ).first():
                    flash("E-mail já está em uso por outro treinador.", "warning")
                    return redirect(url_for("auth.perfil"))
            error = _apply_trade_profile(current_user, request.form)
            if error:
                db.session.rollback()
                flash(error, "warning")
                return redirect(url_for("auth.perfil"))
            current_user.email = email
            db.session.commit()
            flash("Perfil atualizado com sucesso!", "success")

        elif action == "excluir":
            if request.form.get("confirm_username", "").strip() != current_user.username:
                flash("Para apagar a conta, digite seu nome de usuário exatamente.", "warning")
                return redirect(url_for("auth.perfil"))
            user = db.session.get(User, current_user.id)
            logout_user()
            delete_account(user)
            flash("Sua conta e todos os seus dados foram apagados.", "success")
            return redirect(url_for("main.index"))

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
    return render_template("auth/perfil.html", stats=stats,
                           whatsapp_display=format_whatsapp(current_user.whatsapp))


@bp.route("/treinador/<username>")
def perfil_publico(username: str):
    profile_user = db.session.query(User).filter_by(username=username).first_or_404()

    # Redireciona para o próprio perfil se for o usuário logado
    if current_user.is_authenticated and current_user.id == profile_user.id:
        return redirect(url_for("auth.perfil"))

    # Todos se enxergam (D1); só quem desligou "aparecer nas trocas" fica oculto
    if not profile_user.show_in_trades:
        abort(404)

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
