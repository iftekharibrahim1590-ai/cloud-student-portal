"""Course CRUD."""
import re
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from db import get_db
from auth_utils import login_required
import activity

courses_bp = Blueprint("courses", __name__)

CODE_RE = re.compile(r"^[A-Z0-9]{3,10}$")


def _validate(form, db, existing_code: str | None = None):
    data = {
        "course_code": (form.get("course_code") or "").strip().upper(),
        "course_name": (form.get("course_name") or "").strip(),
        "instructor":  (form.get("instructor") or "").strip(),
        "credits":     (form.get("credits") or "").strip(),
    }
    errors = []
    if not CODE_RE.match(data["course_code"]):
        errors.append("Course code must be 3–10 chars, letters/digits only (e.g. CS101).")
    if len(data["course_name"]) < 3:
        errors.append("Course name is too short.")
    if len(data["instructor"]) < 2:
        errors.append("Instructor name is required.")
    try:
        data["credits"] = int(data["credits"])
        if not (1 <= data["credits"] <= 12):
            raise ValueError
    except Exception:
        errors.append("Credits must be an integer between 1 and 12.")

    if not errors:
        # if editing and code unchanged → skip uniqueness check
        if not (existing_code and existing_code == data["course_code"]):
            if db["courses"].find_one({"course_code": data["course_code"]}):
                errors.append("A course with that code already exists.")
    return data, errors


@courses_bp.route("/courses")
@login_required
def list_courses():
    db = get_db()
    docs = list(db["courses"].find(
        {},
        {"course_code": 1, "course_name": 1, "instructor": 1, "credits": 1, "created_at": 1},
    ).sort("course_code", 1).limit(500))
    # single aggregation for enrolment counts — no N+1
    counts = {r["_id"]: r["count"] for r in db["students"].aggregate([
        {"$group": {"_id": "$course", "count": {"$sum": 1}}}
    ])}
    for d in docs:
        d["students_count"] = counts.get(d["course_code"], 0)
    return render_template("courses.html", user=session.get("user"), courses=docs)


@courses_bp.route("/courses/new", methods=["GET", "POST"])
@login_required
def add_course():
    db = get_db()
    if request.method == "POST":
        data, errors = _validate(request.form, db)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("course_form.html", user=session.get("user"), course=data, mode="new")
        db["courses"].insert_one({**data, "created_at": datetime.now(timezone.utc).isoformat()})
        activity.log("course.create", f"Added course {data['course_code']} · {data['course_name']}",
                     actor_email=(session.get("user") or {}).get("email", "?"), target=data["course_code"])
        flash(f"Course {data['course_code']} added.", "success")
        return redirect(url_for("courses.list_courses"))
    return render_template("course_form.html", user=session.get("user"), course=None, mode="new")


@courses_bp.route("/courses/<code>/edit", methods=["GET", "POST"])
@login_required
def edit_course(code):
    db = get_db()
    course = db["courses"].find_one({"course_code": code})
    if not course:
        abort(404)
    if request.method == "POST":
        data, errors = _validate(request.form, db, existing_code=code)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("course_form.html", user=session.get("user"),
                                   course={**course, **data}, mode="edit")
        db["courses"].update_one({"course_code": code}, {"$set": data})
        activity.log("course.update", f"Updated course {code} → {data['course_code']}",
                     actor_email=(session.get("user") or {}).get("email", "?"), target=code)
        flash(f"Course {code} updated.", "success")
        return redirect(url_for("courses.list_courses"))
    return render_template("course_form.html", user=session.get("user"), course=course, mode="edit")


@courses_bp.route("/courses/<code>/delete", methods=["POST"])
@login_required
def delete_course(code):
    db = get_db()
    doc = db["courses"].find_one({"course_code": code})
    if not doc:
        abort(404)
    in_use = db["students"].count_documents({"course": code})
    if in_use:
        flash(f"Cannot delete {code} — {in_use} student(s) are enrolled.", "danger")
        return redirect(url_for("courses.list_courses"))
    db["courses"].delete_one({"course_code": code})
    activity.log("course.delete", f"Deleted course {code}",
                 actor_email=(session.get("user") or {}).get("email", "?"), target=code)
    flash(f"Course {code} deleted.", "info")
    return redirect(url_for("courses.list_courses"))
