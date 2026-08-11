"""Password hashing + session decorators."""
from functools import wraps
import bcrypt
from flask import session, redirect, url_for, flash, abort


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def login_required(view_fn):
    @wraps(view_fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return view_fn(*args, **kwargs)

    return wrapper


def admin_required(view_fn):
    @wraps(view_fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        if (session.get("user") or {}).get("role") != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("dashboard.dashboard"))
        return view_fn(*args, **kwargs)

    return wrapper
