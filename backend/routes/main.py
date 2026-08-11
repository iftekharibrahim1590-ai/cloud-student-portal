"""Landing page routes."""
from flask import Blueprint, render_template, session

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    return render_template("index.html", user=session.get("user"))


@main_bp.route("/api/health")
def health():
    return {"status": "ok", "app": "Cloud Student Portal"}
