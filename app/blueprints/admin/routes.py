import json
import queue
import threading
from functools import wraps

from flask import render_template, abort, Response, stream_with_context, current_app, request
from flask_login import login_required, current_user
from . import bp
from ...extensions import db
from ...models.user import User
from ...models.event import AnalyticsEvent
from ...models.trade import TradeMatch
from ...models.pokemon import Species, Form
from ...models.collection import UserCollection


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@bp.route("/")
@admin_required
def index():
    total_users = db.session.query(User).count()
    total_events = db.session.query(AnalyticsEvent).count()
    total_matches = db.session.query(TradeMatch).count()
    total_species = db.session.query(Species).count()
    total_forms = db.session.query(Form).count()
    total_owned = db.session.query(UserCollection).filter(
        UserCollection.owned.is_(True), UserCollection.quantity > 0
    ).count()
    return render_template(
        "admin/index.html",
        total_users=total_users,
        total_events=total_events,
        total_matches=total_matches,
        total_species=total_species,
        total_forms=total_forms,
        total_owned=total_owned,
    )


@bp.route("/sync")
@admin_required
def sync_page():
    return render_template("admin/sync.html")


@bp.route("/sync/run")
@admin_required
def sync_run():
    limit = request.args.get("limit", 151, type=int)
    offset = request.args.get("offset", 0, type=int)

    q: queue.Queue = queue.Queue()
    app = current_app._get_current_object()

    def run_in_thread():
        with app.app_context():
            from ...services.sync_service import sync_pokemon
            report = sync_pokemon(limit=limit, offset=offset, log=lambda msg: q.put({"line": msg}))
            q.put({"done": True, "report": report})

    threading.Thread(target=run_in_thread, daemon=True).start()

    def generate():
        while True:
            try:
                msg = q.get(timeout=120)
            except queue.Empty:
                yield f"data: {json.dumps({'error': 'timeout'})}\n\n"
                break
            yield f"data: {json.dumps(msg)}\n\n"
            if msg.get("done") or msg.get("error"):
                break

    return Response(
        stream_with_context(generate()),
        content_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@bp.route("/usuarios")
@admin_required
def usuarios():
    users = db.session.query(User).order_by(User.created_at.desc()).all()
    return render_template("admin/usuarios.html", users=users)


@bp.route("/logs")
@admin_required
def logs():
    events = (
        db.session.query(AnalyticsEvent)
        .order_by(AnalyticsEvent.created_at.desc())
        .limit(200)
        .all()
    )
    return render_template("admin/logs.html", events=events)
