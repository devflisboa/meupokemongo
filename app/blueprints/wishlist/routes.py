from flask import render_template, redirect, url_for, request, abort
from flask_login import login_required, current_user
from . import bp
from ...extensions import db
from ...models.wishlist import Wishlist
from ...models.pokemon import Form, Species


@bp.route("/")
@login_required
def index():
    items = (
        db.session.query(Wishlist)
        .filter_by(user_id=current_user.id)
        .join(Form, Wishlist.form_id == Form.id)
        .join(Species, Form.species_id == Species.id)
        .order_by(
            db.case({"high": 0, "medium": 1, "low": 2}, value=Wishlist.priority),
            Species.id,
        )
        .all()
    )

    all_species = db.session.query(Species).order_by(Species.id).all()
    wished_form_ids = {w.form_id for w in items}

    return render_template(
        "wishlist/index.html",
        items=items,
        all_species=all_species,
        wished_form_ids=wished_form_ids,
    )


@bp.route("/add", methods=["POST"])
@login_required
def add():
    form_id = request.form.get("form_id", type=int)
    priority = request.form.get("priority", "medium")
    if priority not in ("low", "medium", "high"):
        priority = "medium"

    form = db.session.get(Form, form_id)
    if not form:
        abort(404)

    existing = db.session.query(Wishlist).filter_by(
        user_id=current_user.id, form_id=form_id
    ).first()
    if not existing:
        db.session.add(Wishlist(user_id=current_user.id, form_id=form_id, priority=priority))
        db.session.commit()

    return redirect(url_for("wishlist.index"))


@bp.route("/remove/<int:item_id>", methods=["POST"])
@login_required
def remove(item_id: int):
    item = db.session.get(Wishlist, item_id)
    if not item or item.user_id != current_user.id:
        abort(403)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for("wishlist.index"))
