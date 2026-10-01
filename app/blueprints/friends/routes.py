from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from . import bp
from ...extensions import db
from ...models.friendship import Friendship
from ...models.user import User


@bp.route("/")
@login_required
def index():
    friends = db.session.query(Friendship).filter(
        db.or_(
            db.and_(Friendship.requester_id == current_user.id, Friendship.status == "accepted"),
            db.and_(Friendship.addressee_id == current_user.id, Friendship.status == "accepted"),
        )
    ).all()
    pending_received = db.session.query(Friendship).filter_by(
        addressee_id=current_user.id, status="pending"
    ).all()
    return render_template("friends/index.html", friends=friends, pending=pending_received)


@bp.route("/convidar", methods=["POST"])
@login_required
def convidar():
    username = request.form.get("username", "").strip()
    addressee = db.session.query(User).filter_by(username=username).first()
    if not addressee or addressee.id == current_user.id:
        flash("Usuário não encontrado.", "warning")
        return redirect(url_for("friends.index"))

    existing = db.session.query(Friendship).filter(
        db.or_(
            db.and_(Friendship.requester_id == current_user.id, Friendship.addressee_id == addressee.id),
            db.and_(Friendship.requester_id == addressee.id, Friendship.addressee_id == current_user.id),
        )
    ).first()
    if existing:
        flash("Já existe um vínculo com esse treinador.", "info")
        return redirect(url_for("friends.index"))

    f = Friendship(requester_id=current_user.id, addressee_id=addressee.id)
    db.session.add(f)
    db.session.commit()
    flash(f"Convite enviado para {username}.", "success")
    return redirect(url_for("friends.index"))


@bp.route("/aceitar/<int:friendship_id>")
@login_required
def aceitar(friendship_id: int):
    f = db.session.get(Friendship, friendship_id)
    if not f or f.addressee_id != current_user.id:
        abort(403)
    f.status = "accepted"
    db.session.commit()
    return redirect(url_for("friends.index"))


@bp.route("/recusar/<int:friendship_id>")
@login_required
def recusar(friendship_id: int):
    f = db.session.get(Friendship, friendship_id)
    if not f or f.addressee_id != current_user.id:
        abort(403)
    db.session.delete(f)
    db.session.commit()
    return redirect(url_for("friends.index"))


@bp.route("/remover/<int:friendship_id>", methods=["POST"])
@login_required
def remover(friendship_id: int):
    f = db.session.get(Friendship, friendship_id)
    if not f or (f.requester_id != current_user.id and f.addressee_id != current_user.id):
        abort(403)
    db.session.delete(f)
    db.session.commit()
    flash("Amizade removida.", "info")
    return redirect(url_for("friends.index"))
