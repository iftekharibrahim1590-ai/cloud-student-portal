"""Admin monitoring dashboard."""
import json
from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template, session, current_app
from db import get_db
from auth_utils import admin_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@admin_required
def monitoring():
    db = get_db()

    total_users     = db["users"].count_documents({})
    total_students  = db["students"].count_documents({})
    total_courses   = db["courses"].count_documents({})

    # "active sessions" ≈ distinct users who logged in within the last 30 min
    since = datetime.now(timezone.utc) - timedelta(minutes=30)
    active_sessions = len(db["activity_logs"].distinct(
        "actor_email", {"action": "auth.login", "timestamp": {"$gte": since}}
    ))

    # students-by-department (for pie chart)
    dept_pipeline = [
        {"$group": {"_id": "$department", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    dept_rows = list(db["students"].aggregate(dept_pipeline))
    dept_labels = [r["_id"] or "—" for r in dept_rows]
    dept_values = [r["count"] for r in dept_rows]

    # activity-per-day (last 7 days)
    end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    start = end - timedelta(days=7)
    daily = {(start + timedelta(days=i)).strftime("%Y-%m-%d"): 0 for i in range(7)}
    logs = list(db["activity_logs"].find({"timestamp": {"$gte": start}}, {"timestamp": 1}))
    for l in logs:
        ts = l.get("timestamp")
        if isinstance(ts, datetime):
            key = ts.strftime("%Y-%m-%d")
            if key in daily:
                daily[key] += 1
    activity_labels = list(daily.keys())
    activity_values = list(daily.values())

    # server-side runtime metrics come from context processor (csp_uptime, csp_requests)
    metrics = {
        "total_users": total_users,
        "total_students": total_students,
        "total_courses": total_courses,
        "active_sessions": active_sessions,
        "app_status": "Online",
        "server_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }

    charts = {
        "dept_labels": json.dumps(dept_labels),
        "dept_values": json.dumps(dept_values),
        "activity_labels": json.dumps(activity_labels),
        "activity_values": json.dumps(activity_values),
    }

    return render_template("admin.html", user=session.get("user"), metrics=metrics, charts=charts)
