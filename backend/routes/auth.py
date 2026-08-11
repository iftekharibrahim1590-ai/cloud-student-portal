"""Registration, login, logout — with activity logging."""
import re
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_db
from auth_utils import hash_password, verify_password
import activity

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        errors = []
        if len(full_name) < 2:
            errors.append("Full name must be at least 2 characters.")
        if not EMAIL_RE.match(email):
            errors.append("Please enter a valid email address.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")

        db = get_db()
        if not errors and db["users"].find_one({"email": email}):
            errors.append("An account with this email already exists.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("register.html", full_name=full_name, email=email)

        db["users"].insert_one({
            "email": email,
            "password_hash": hash_password(password),
            "full_name": full_name,
            "role": "user",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        activity.log("auth.register", f"New account created: {full_name}", actor_email=email)
        flash("Account created — you can log in now.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        db = get_db()
        user = db["users"].find_one({"email": email})
        if not user or not verify_password(password, user["password_hash"]):
            flash("Invalid email or password.", "danger")
            return render_template("login.html", email=email)

        session["user_id"] = str(user["_id"])
        session["user"] = {
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user.get("role", "user"),
        }
        activity.log("auth.login", f"{user['full_name']} signed in", actor_email=email)
        flash(f"Welcome back, {user['full_name']}!", "success")
        return redirect(url_for("dashboard.dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    u = session.get("user") or {}
    if u.get("email"):
        activity.log("auth.logout", f"{u.get('full_name','user')} signed out", actor_email=u["email"])
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.home"))
