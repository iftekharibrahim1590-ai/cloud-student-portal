"""User profile: update name + change password."""
from bson import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_db
from auth_utils import login_required, hash_password, verify_password
import activity

profile_bp = Blueprint("profile", __name__)


def _current_user(db):
    uid = session.get("user_id")
    if not uid:
        return None
    try:
        return db["users"].find_one({"_id": ObjectId(uid)})
    except Exception:
        return None


@profile_bp.route("/profile", methods=["GET"])
@login_required
def profile():
    db = get_db()
    user_doc = _current_user(db)
    if not user_doc:
        session.clear()
        flash("Session expired. Please sign in again.", "warning")
        return redirect(url_for("auth.login"))
    return render_template("profile.html", user=session.get("user"), user_doc=user_doc)


@profile_bp.route("/profile/update", methods=["POST"])
@login_required
def update_profile():
    db = get_db()
    user_doc = _current_user(db)
    if not user_doc:
        session.clear()
        return redirect(url_for("auth.login"))

    full_name = (request.form.get("full_name") or "").strip()
    if len(full_name) < 2:
        flash("Full name must be at least 2 characters.", "danger")
        return redirect(url_for("profile.profile"))

    db["users"].update_one({"_id": user_doc["_id"]}, {"$set": {"full_name": full_name}})
    session["user"]["full_name"] = full_name
    session.modified = True
    activity.log("profile.update", f"Profile name updated to '{full_name}'",
                 actor_email=user_doc["email"])
    flash("Profile updated.", "success")
    return redirect(url_for("profile.profile"))


@profile_bp.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    db = get_db()
    user_doc = _current_user(db)
    if not user_doc:
        session.clear()
        return redirect(url_for("auth.login"))

    current = request.form.get("current_password") or ""
    new = request.form.get("new_password") or ""
    confirm = request.form.get("confirm_password") or ""

    errors = []
    if not verify_password(current, user_doc["password_hash"]):
        errors.append("Current password is incorrect.")
    if len(new) < 6:
        errors.append("New password must be at least 6 characters.")
    if new != confirm:
        errors.append("New passwords do not match.")
    if current and new and current == new:
        errors.append("New password must differ from current password.")

    if errors:
        for e in errors:
            flash(e, "danger")
        return redirect(url_for("profile.profile"))

    db["users"].update_one({"_id": user_doc["_id"]}, {"$set": {"password_hash": hash_password(new)}})
    activity.log("profile.password", "Password changed", actor_email=user_doc["email"])
    flash("Password changed.", "success")
    return redirect(url_for("profile.profile"))
