"""User dashboard — stats + recent activity from Atlas."""
from datetime import datetime, timezone
from flask import Blueprint, render_template, session
from db import get_db
from auth_utils import login_required
import activity

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    stats = {
        "total_users": db["users"].count_documents({}),
        "total_students": db["students"].count_documents({}),
        "total_courses": db["courses"].count_documents({}),
        "server_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    activities = activity.recent(limit=8)
    return render_template(
        "dashboard.html",
        user=session.get("user"),
        stats=stats,
        activities=activities,
    )
