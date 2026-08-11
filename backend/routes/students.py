"""Student CRUD with search + pagination."""
import re
from datetime import datetime, timezone
from math import ceil
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from db import get_db
from auth_utils import login_required
import activity

students_bp = Blueprint("students", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
YEARS = [1, 2, 3, 4]
PAGE_SIZE = 8


def _next_student_id(db) -> str:
    last = list(db["students"].find({}, {"student_id": 1}).sort("student_id", -1).limit(1))
    if not last:
        return "STU-001"
    m = re.match(r"STU-(\d+)", last[0].get("student_id", "STU-000"))
    n = int(m.group(1)) + 1 if m else 1
    return f"STU-{n:03d}"


def _validate(form, db, existing_id: str | None = None) -> tuple[dict, list[str]]:
    data = {
        "full_name": (form.get("full_name") or "").strip(),
        "email":     (form.get("email") or "").strip().lower(),
        "phone":     (form.get("phone") or "").strip(),
        "course":    (form.get("course") or "").strip(),
        "year":      (form.get("year") or "").strip(),
        "department":(form.get("department") or "").strip(),
    }
    errors = []
    if len(data["full_name"]) < 2:
        errors.append("Full name must be at least 2 characters.")
    if not EMAIL_RE.match(data["email"]):
        errors.append("Please enter a valid email.")
    if len(data["phone"]) < 4:
        errors.append("Phone is too short.")
    if not data["course"]:
        errors.append("Please choose a course.")
    if not data["department"]:
        errors.append("Department is required.")
    try:
        data["year"] = int(data["year"])
        if data["year"] not in YEARS:
            raise ValueError
    except Exception:
        errors.append("Year must be 1, 2, 3 or 4.")

    # unique email (ignoring current student if editing)
    if not errors:
        q = {"email": data["email"]}
        if existing_id:
            q["student_id"] = {"$ne": existing_id}
        if db["students"].find_one(q):
            errors.append("Another student already uses this email.")

    return data, errors


@students_bp.route("/students")
@login_required
def list_students():
    db = get_db()
    q = (request.args.get("q") or "").strip()
    page = max(1, int(request.args.get("page", 1) or 1))

    filt = {}
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        filt = {"$or": [
            {"student_id": rx}, {"full_name": rx}, {"email": rx},
            {"department": rx}, {"course": rx},
        ]}

    total = db["students"].count_documents(filt)
    pages = max(1, ceil(total / PAGE_SIZE))
    page = min(page, pages)

    docs = list(
        db["students"].find(filt, {
            "student_id": 1, "full_name": 1, "email": 1,
            "phone": 1, "course": 1, "year": 1, "department": 1,
        })
        .sort("student_id", 1)
        .skip((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    )
    return render_template(
        "students.html",
        user=session.get("user"),
        students=docs,
        q=q,
        page=page,
        pages=pages,
        total=total,
        page_size=PAGE_SIZE,
    )


@students_bp.route("/students/new", methods=["GET", "POST"])
@login_required
def add_student():
    db = get_db()
    courses = list(db["courses"].find({}, {"course_code": 1, "course_name": 1}).sort("course_code", 1).limit(500))

    if request.method == "POST":
        data, errors = _validate(request.form, db)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("student_form.html", user=session.get("user"),
                                   student=data, courses=courses, mode="new")
        sid = _next_student_id(db)
        db["students"].insert_one({
            "student_id": sid,
            **data,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        activity.log("student.create", f"Added student {sid} · {data['full_name']}",
                     actor_email=(session.get("user") or {}).get("email", "?"), target=sid)
        flash(f"Student {sid} added.", "success")
        return redirect(url_for("students.list_students"))

    return render_template("student_form.html", user=session.get("user"),
                           student=None, courses=courses, mode="new")


@students_bp.route("/students/<sid>/edit", methods=["GET", "POST"])
@login_required
def edit_student(sid):
    db = get_db()
    student = db["students"].find_one({"student_id": sid})
    if not student:
        abort(404)
    courses = list(db["courses"].find({}, {"course_code": 1, "course_name": 1}).sort("course_code", 1).limit(500))

    if request.method == "POST":
        data, errors = _validate(request.form, db, existing_id=sid)
        if errors:
            for e in errors:
                flash(e, "danger")
            merged = {**student, **data}
            return render_template("student_form.html", user=session.get("user"),
                                   student=merged, courses=courses, mode="edit")
        db["students"].update_one({"student_id": sid}, {"$set": data})
        activity.log("student.update", f"Updated student {sid} · {data['full_name']}",
                     actor_email=(session.get("user") or {}).get("email", "?"), target=sid)
        flash(f"Student {sid} updated.", "success")
        return redirect(url_for("students.list_students"))

    return render_template("student_form.html", user=session.get("user"),
                           student=student, courses=courses, mode="edit")


@students_bp.route("/students/<sid>/delete", methods=["POST"])
@login_required
def delete_student(sid):
    db = get_db()
    doc = db["students"].find_one({"student_id": sid})
    if not doc:
        abort(404)
    db["students"].delete_one({"student_id": sid})
    activity.log("student.delete", f"Deleted student {sid} · {doc.get('full_name','')}",
                 actor_email=(session.get("user") or {}).get("email", "?"), target=sid)
    flash(f"Student {sid} deleted.", "info")
    return redirect(url_for("students.list_students", q=request.args.get("q", ""), page=request.args.get("page", 1)))
