"""Cloud Student Portal — Flask app entrypoint (Phase 2).

Uvicorn (supervisor) imports `app` from this module. Since Flask is WSGI, we
wrap it with asgiref.wsgi.WsgiToAsgi so it can run under an ASGI server.
"""
import os
import time
import logging
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from flask import Flask, render_template, g, request
from asgiref.wsgi import WsgiToAsgi

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from routes.main import main_bp
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.students import students_bp
from routes.courses import courses_bp
from routes.profile import profile_bp
from routes.admin import admin_bp
from db import get_db
from seed import seed_all


# --- runtime metrics (module-level so counters survive across requests) ---
APP_START_TS = time.time()
REQUEST_COUNTER = {"count": 0}


def _uptime_str() -> str:
    secs = int(time.time() - APP_START_TS)
    d, r = divmod(secs, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    if d:
        return f"{d}d {h}h {m}m"
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def create_app() -> Flask:
    flask_app = Flask(
        __name__,
        template_folder=str(ROOT_DIR / "templates"),
        static_folder=str(ROOT_DIR / "static"),
    )
    flask_app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "cloud-student-portal-dev-secret")
    flask_app.config["SESSION_COOKIE_HTTPONLY"] = True
    flask_app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # blueprints
    flask_app.register_blueprint(main_bp)
    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(dashboard_bp)
    flask_app.register_blueprint(students_bp)
    flask_app.register_blueprint(courses_bp)
    flask_app.register_blueprint(profile_bp)
    flask_app.register_blueprint(admin_bp)

    # request counter middleware
    @flask_app.before_request
    def _count_request():
        # ignore static assets so the metric reflects real app traffic
        if request.endpoint != "static":
            REQUEST_COUNTER["count"] += 1

    # expose runtime metrics helper globally for templates
    @flask_app.context_processor
    def _inject_runtime():
        return {"csp_uptime": _uptime_str, "csp_requests": lambda: REQUEST_COUNTER["count"]}

    # error handlers
    @flask_app.errorhandler(404)
    def _404(err):
        return render_template("404.html"), 404

    @flask_app.errorhandler(500)
    def _500(err):
        logging.getLogger(__name__).exception("500 error")
        return render_template("500.html"), 500

    # seed on startup (idempotent) — tolerate DB unavailability
    with flask_app.app_context():
        try:
            seed_all(get_db())
        except Exception as exc:
            logging.getLogger(__name__).warning("Seed skipped: %s", exc)

    return flask_app


flask_app = create_app()
# ASGI wrapper — uvicorn loads this as `server:app`
app = WsgiToAsgi(flask_app)
