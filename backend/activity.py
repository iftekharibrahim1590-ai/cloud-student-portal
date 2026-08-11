"""Activity log writer + reader.

Every meaningful state-change writes here. The admin monitoring dashboard
and the user dashboard both read from it.
"""
from datetime import datetime, timezone
from db import get_db


# icon per action prefix — kept short so templates stay clean
_ICONS = {
    "auth.login":       "fa-right-to-bracket",
    "auth.logout":      "fa-arrow-right-from-bracket",
    "auth.register":    "fa-user-plus",
    "student.create":   "fa-user-graduate",
    "student.update":   "fa-user-pen",
    "student.delete":   "fa-user-minus",
    "course.create":    "fa-book-open",
    "course.update":    "fa-book",
    "course.delete":    "fa-book-open-reader",
    "profile.update":   "fa-id-card",
    "profile.password": "fa-key",
}


def icon_for(action: str) -> str:
    return _ICONS.get(action, "fa-wave-square")


def log(action: str, description: str, *, actor_email: str = "system", target: str | None = None) -> None:
    """Insert one activity entry. Never raises — logging must never break a request."""
    try:
        get_db()["activity_logs"].insert_one({
            "action": action,
            "description": description,
            "actor_email": actor_email,
            "target": target,
            "timestamp": datetime.now(timezone.utc),
        })
    except Exception:
        pass


def recent(limit: int = 8):
    """Latest activities, newest first, with an icon + human timestamp."""
    try:
        docs = list(
            get_db()["activity_logs"].find(
                {},
                {"action": 1, "description": 1, "actor_email": 1, "target": 1, "timestamp": 1},
            ).sort("timestamp", -1).limit(limit)
        )
    except Exception:
        return []
    for d in docs:
        d["icon"] = icon_for(d.get("action", ""))
        ts = d.get("timestamp")
        if isinstance(ts, datetime):
            d["time"] = ts.strftime("%Y-%m-%d %H:%M UTC")
        else:
            d["time"] = str(ts)
    return docs
