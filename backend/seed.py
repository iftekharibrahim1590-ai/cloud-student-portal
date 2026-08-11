"""Idempotent seed: admin user + sample students + sample courses."""
from datetime import datetime, timezone
from auth_utils import hash_password

ADMIN_EMAIL = "ibrahim@cloud.com"
ADMIN_PASSWORD = "admin123"
ADMIN_NAME = "Ibrahim (Admin)"

COURSES = [
    {"course_code": "CS101", "course_name": "Introduction to Computer Science", "instructor": "Dr. Alan Turing",   "credits": 4},
    {"course_code": "CS210", "course_name": "Data Structures & Algorithms",     "instructor": "Dr. Grace Hopper", "credits": 4},
    {"course_code": "EE201", "course_name": "Digital Electronics",              "instructor": "Dr. Nikola Bose",  "credits": 3},
    {"course_code": "ME150", "course_name": "Thermodynamics I",                 "instructor": "Dr. Sadi Carnot",  "credits": 3},
    {"course_code": "MA202", "course_name": "Linear Algebra",                   "instructor": "Dr. Emmy Noether", "credits": 3},
]

STUDENTS = [
    ("STU-001", "Aarav Sharma",     "aarav.sharma@campus.edu",   "+91-9812340001", "CS101", 1, "Computer Science"),
    ("STU-002", "Isabella Rossi",   "isabella.rossi@campus.edu", "+39-3391112201", "CS210", 2, "Computer Science"),
    ("STU-003", "Kwame Mensah",     "kwame.mensah@campus.edu",   "+233-244001122", "EE201", 3, "Electrical Engineering"),
    ("STU-004", "Mei Lin",          "mei.lin@campus.edu",        "+86-1381234567", "MA202", 2, "Mathematics"),
    ("STU-005", "Diego Alvarez",    "diego.alvarez@campus.edu",  "+34-611223344",  "ME150", 4, "Mechanical Engineering"),
    ("STU-006", "Fatima Zahra",     "fatima.zahra@campus.edu",   "+212-661778899", "CS101", 1, "Computer Science"),
    ("STU-007", "Jonas Weber",      "jonas.weber@campus.edu",    "+49-176501234",  "EE201", 2, "Electrical Engineering"),
    ("STU-008", "Priya Nair",       "priya.nair@campus.edu",     "+91-9847112233", "CS210", 3, "Computer Science"),
    ("STU-009", "Liam O'Connor",    "liam.oconnor@campus.edu",   "+353-871122334", "MA202", 1, "Mathematics"),
    ("STU-010", "Sofia Petrova",    "sofia.petrova@campus.edu",  "+7-9161234500",  "ME150", 3, "Mechanical Engineering"),
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def seed_admin(db):
    users = db["users"]
    if not users.find_one({"email": ADMIN_EMAIL}):
        users.insert_one({
            "email": ADMIN_EMAIL,
            "password_hash": hash_password(ADMIN_PASSWORD),
            "full_name": ADMIN_NAME,
            "role": "admin",
            "created_at": _now_iso(),
        })


def seed_courses(db):
    col = db["courses"]
    for c in COURSES:
        if not col.find_one({"course_code": c["course_code"]}):
            doc = dict(c)
            doc["created_at"] = _now_iso()
            col.insert_one(doc)


def seed_students(db):
    col = db["students"]
    for (sid, name, email, phone, course, year, dept) in STUDENTS:
        if not col.find_one({"student_id": sid}):
            col.insert_one({
                "student_id": sid,
                "full_name": name,
                "email": email,
                "phone": phone,
                "course": course,
                "year": year,
                "department": dept,
                "created_at": _now_iso(),
            })


def seed_all(db):
    seed_admin(db)
    seed_courses(db)
    seed_students(db)
