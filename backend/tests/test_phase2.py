"""Phase 2 e2e backend tests — Cloud Student Portal.

Server-rendered Flask app; we drive it with requests.Session over the public
proxied URL. All state changes are asserted via flash messages, redirects,
and follow-up GETs that verify data-testid markers in the returned HTML.
"""
import os
import re
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("PUBLIC_BASE_URL") or "https://flask-student-hub.preview.emergentagent.com"
ADMIN_EMAIL = "ibrahim@cloud.com"
ADMIN_PASSWORD = "admin123"


# ---------- helpers ----------
def _login(session: requests.Session, email: str, password: str) -> requests.Response:
    r = session.post(
        f"{BASE_URL}/login",
        data={"email": email, "password": password},
        allow_redirects=True,
        timeout=30,
    )
    return r


def _logout(session: requests.Session) -> requests.Response:
    return session.get(f"{BASE_URL}/logout", allow_redirects=True, timeout=30)


def _flash_categories(html: str):
    return re.findall(r'data-testid="flash-([a-z]+)"', html)


def _flash_messages(html: str):
    # returns list of (category, message-text)
    out = []
    for m in re.finditer(r'data-testid="flash-([a-z]+)"[^>]*>\s*([^<]+?)\s*<', html):
        out.append((m.group(1), m.group(2).strip()))
    return out


# ---------- fixtures ----------
@pytest.fixture
def admin_session():
    s = requests.Session()
    r = _login(s, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert r.status_code == 200, f"Admin login failed: {r.status_code}"
    assert "dashboard-title" in r.text, "Admin login did not land on dashboard"
    yield s
    try:
        _logout(s)
    except Exception:
        pass


@pytest.fixture
def anon_session():
    s = requests.Session()
    yield s


# =========================================================
# 1) Health + landing
# =========================================================
class TestHealth:
    def test_api_health(self):
        r = requests.get(f"{BASE_URL}/api/health", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "ok"

    def test_landing_page(self):
        r = requests.get(f"{BASE_URL}/", timeout=15)
        assert r.status_code == 200
        assert "hero-cta-register" in r.text or "nav-register" in r.text


# =========================================================
# 2) Auth + admin login
# =========================================================
class TestAuth:
    def test_admin_login(self):
        s = requests.Session()
        r = _login(s, ADMIN_EMAIL, ADMIN_PASSWORD)
        assert r.status_code == 200
        assert 'data-testid="dashboard-title"' in r.text
        assert "Welcome back" in r.text or "Ibrahim" in r.text

    def test_dashboard_requires_auth(self):
        r = requests.get(f"{BASE_URL}/dashboard", timeout=15, allow_redirects=False)
        assert r.status_code in (301, 302)
        assert "/login" in r.headers.get("Location", "")


# =========================================================
# 3) Students CRUD + search + pagination
# =========================================================
class TestStudents:
    def test_list_pagination(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/students", timeout=20)
        assert r.status_code == 200
        assert 'data-testid="students-title"' in r.text
        # 10 students → 2 pages of 8
        assert "total:</span> 10" in r.text
        assert "pagination-page-1" in r.text
        assert "pagination-page-2" in r.text
        # STU-001..008 visible on page 1 (sorted by student_id asc)
        for i in range(1, 9):
            assert f"student-row-STU-{i:03d}" in r.text, f"missing STU-{i:03d} on page 1"

    def test_pagination_page2(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/students?page=2", timeout=20)
        assert r.status_code == 200
        for sid in ("STU-009", "STU-010"):
            assert f"student-row-{sid}" in r.text

    def test_search_by_name(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/students?q=Sharma", timeout=20)
        assert r.status_code == 200
        assert "Sharma" in r.text
        # Expect only rows containing Sharma
        row_ids = re.findall(r'data-testid="student-row-(STU-\d+)"', r.text)
        assert len(row_ids) >= 1

    def test_search_by_department(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/students?q=Computer Science", timeout=20)
        assert r.status_code == 200
        assert "Computer Science" in r.text
        row_ids = re.findall(r'data-testid="student-row-(STU-\d+)"', r.text)
        assert len(row_ids) >= 1

    def test_search_empty_restores_all(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/students?q=", timeout=20)
        assert r.status_code == 200
        assert "total:</span> 10" in r.text

    def test_add_student_form_renders(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/students/new", timeout=20)
        assert r.status_code == 200
        for tid in ("student-form", "student-field-name", "student-field-email",
                    "student-field-phone", "student-field-department",
                    "student-field-course", "student-field-year", "student-form-submit"):
            assert f'data-testid="{tid}"' in r.text

    def test_add_student_validation_errors(self, admin_session):
        # short name + bad email + missing course + year=5 + dup email
        r = admin_session.post(
            f"{BASE_URL}/students/new",
            data={
                "full_name": "A",
                "email": "aarav.sharma@campus.edu",  # duplicate of seed
                "phone": "12",
                "department": "",
                "course": "",
                "year": "5",
            },
            allow_redirects=True, timeout=20,
        )
        assert r.status_code == 200
        cats = _flash_categories(r.text)
        assert "danger" in cats, f"expected danger flashes, got: {_flash_messages(r.text)}"
        # form re-rendered
        assert 'data-testid="student-form"' in r.text

    def test_add_student_valid_creates_stu011(self, admin_session):
        # ensure baseline
        list_before = admin_session.get(f"{BASE_URL}/students", timeout=20).text
        # sanity: STU-011 not yet present
        assert "student-row-STU-011" not in list_before

        r = admin_session.post(
            f"{BASE_URL}/students/new",
            data={
                "full_name": "TEST_NewStudent Phase2",
                "email": f"test_newstu_{uuid.uuid4().hex[:6]}@campus.edu",
                "phone": "9998887777",
                "department": "Computer Science",
                "course": "CS101",
                "year": "2",
            },
            allow_redirects=True, timeout=20,
        )
        assert r.status_code == 200
        # After success, we're redirected to /students; success flash mentions STU-011
        assert "Student STU-011 added." in r.text, \
            f"expected success flash for STU-011, flashes={_flash_messages(r.text)}"
        # STU-011 sorted last → shows on page 2 (not page 1). Total should be 11.
        assert "total:</span> 11" in r.text
        r2 = admin_session.get(f"{BASE_URL}/students?page=2", timeout=20)
        assert "student-row-STU-011" in r2.text

    def test_edit_student_prefill_and_update(self, admin_session):
        # GET edit form for STU-001
        r = admin_session.get(f"{BASE_URL}/students/STU-001/edit", timeout=20)
        assert r.status_code == 200
        assert 'data-testid="student-form"' in r.text
        # Extract current values to reuse
        name_m = re.search(r'name="full_name"[^>]*value="([^"]*)"', r.text)
        email_m = re.search(r'name="email"[^>]*value="([^"]*)"', r.text)
        phone_m = re.search(r'name="phone"[^>]*value="([^"]*)"', r.text)
        dept_m = re.search(r'name="department"[^>]*value="([^"]*)"', r.text)
        assert name_m and email_m and phone_m and dept_m
        original_name = name_m.group(1)

        # currently selected course + year
        course_m = re.search(r'<option value="([^"]+)"\s+selected', r.text)
        year_m = re.search(r'<option value="(\d)" selected>Year \d</option>', r.text)
        course_val = course_m.group(1) if course_m else "CS101"
        year_val = year_m.group(1) if year_m else "1"

        new_name = original_name + " (edited)"
        r2 = admin_session.post(
            f"{BASE_URL}/students/STU-001/edit",
            data={
                "full_name": new_name,
                "email": email_m.group(1),
                "phone": phone_m.group(1),
                "department": dept_m.group(1),
                "course": course_val,
                "year": year_val,
            },
            allow_redirects=True, timeout=20,
        )
        assert r2.status_code == 200
        assert "updated" in r2.text.lower()
        # Verify persistence via edit-form GET
        r3 = admin_session.get(f"{BASE_URL}/students/STU-001/edit", timeout=20)
        assert new_name in r3.text

        # revert
        admin_session.post(
            f"{BASE_URL}/students/STU-001/edit",
            data={
                "full_name": original_name,
                "email": email_m.group(1),
                "phone": phone_m.group(1),
                "department": dept_m.group(1),
                "course": course_val,
                "year": year_val,
            },
            allow_redirects=True, timeout=20,
        )

    def test_delete_student_stu011_created_earlier(self, admin_session):
        # We should have STU-011 from the earlier create. Delete it.
        r = admin_session.post(
            f"{BASE_URL}/students/STU-011/delete", allow_redirects=True, timeout=20,
        )
        assert r.status_code == 200
        assert "student-row-STU-011" not in r.text
        # info flash
        assert "info" in _flash_categories(r.text) or "deleted" in r.text.lower()

    def test_delete_missing_student_404(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/students/STU-999/delete",
                               allow_redirects=False, timeout=20)
        assert r.status_code == 404


# =========================================================
# 4) Courses CRUD
# =========================================================
class TestCourses:
    def test_list_courses_seeded(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/courses", timeout=20)
        assert r.status_code == 200
        assert 'data-testid="courses-title"' in r.text
        for code in ("CS101", "CS210", "EE201", "ME150", "MA202"):
            assert f"course-card-{code}" in r.text
        # each seeded course shows an enrolled count (>=1); accept "2 enrolled" seeded
        assert "enrolled" in r.text

    def test_add_course_tst101(self, admin_session):
        # ensure clean
        del_before = admin_session.get(f"{BASE_URL}/courses", timeout=20).text
        if "course-card-TST101" in del_before:
            admin_session.post(f"{BASE_URL}/courses/TST101/delete",
                               allow_redirects=True, timeout=20)

        r = admin_session.post(
            f"{BASE_URL}/courses/new",
            data={
                "course_code": "TST101",
                "course_name": "Test Course Phase 2",
                "instructor": "Dr. Testy McTest",
                "credits": "3",
            },
            allow_redirects=True, timeout=20,
        )
        assert r.status_code == 200
        assert "course-card-TST101" in r.text
        assert "Course TST101 added." in r.text or "TST101" in r.text

    def test_edit_course_preserves_code(self, admin_session):
        # Edit CS101 without changing code — must not trip duplicate check
        r = admin_session.get(f"{BASE_URL}/courses/CS101/edit", timeout=20)
        assert r.status_code == 200
        assert 'data-testid="course-form"' in r.text
        # Grab current values
        name = re.search(r'name="course_name"[^>]*value="([^"]*)"', r.text).group(1)
        instr = re.search(r'name="instructor"[^>]*value="([^"]*)"', r.text).group(1)
        credits = re.search(r'name="credits"[^>]*value="([^"]*)"', r.text).group(1)

        r2 = admin_session.post(
            f"{BASE_URL}/courses/CS101/edit",
            data={
                "course_code": "CS101",  # unchanged
                "course_name": name,
                "instructor": instr,
                "credits": credits,
            },
            allow_redirects=True, timeout=20,
        )
        assert r2.status_code == 200
        # no danger flash
        cats = _flash_categories(r2.text)
        assert "danger" not in cats, f"unexpected danger flash: {_flash_messages(r2.text)}"

    def test_delete_course_with_enrollments_blocked(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/courses/CS101/delete",
                               allow_redirects=True, timeout=20)
        assert r.status_code == 200
        # still present
        assert "course-card-CS101" in r.text
        cats = _flash_categories(r.text)
        assert "danger" in cats

    def test_delete_tst101_no_enrollments(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/courses/TST101/delete",
                               allow_redirects=True, timeout=20)
        assert r.status_code == 200
        assert "course-card-TST101" not in r.text

    def test_course_validation(self, admin_session):
        r = admin_session.post(
            f"{BASE_URL}/courses/new",
            data={
                "course_code": "ab",       # too short + lowercase after upper still fails length
                "course_name": "",         # missing
                "instructor": "Someone",
                "credits": "99",           # out of range
            },
            allow_redirects=True, timeout=20,
        )
        assert r.status_code == 200
        cats = _flash_categories(r.text)
        assert "danger" in cats
        # multiple errors surfaced
        msgs = " ".join(m for _, m in _flash_messages(r.text))
        assert "code" in msgs.lower() or "credits" in msgs.lower() or "name" in msgs.lower()


# =========================================================
# 5) Profile + change password
# =========================================================
class TestProfile:
    def test_profile_page(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/profile", timeout=20)
        assert r.status_code == 200
        for tid in ("profile-title", "profile-info-form", "profile-field-name",
                    "profile-info-submit", "profile-password-form",
                    "profile-current-password", "profile-new-password",
                    "profile-confirm-password", "profile-password-submit"):
            assert f'data-testid="{tid}"' in r.text
        # email disabled + role disabled
        assert 'name="full_name"' in r.text
        # role field is disabled (admin)
        assert 'value="admin"' in r.text

    def test_profile_update_name_persists(self, admin_session):
        # Get current name
        r0 = admin_session.get(f"{BASE_URL}/profile", timeout=20)
        m = re.search(r'name="full_name"[^>]*value="([^"]*)"', r0.text)
        original = m.group(1)
        temp = original + " (t)"
        r1 = admin_session.post(f"{BASE_URL}/profile/update",
                                data={"full_name": temp},
                                allow_redirects=True, timeout=20)
        assert r1.status_code == 200
        assert temp in r1.text
        # navbar/dashboard greeting on next load
        rd = admin_session.get(f"{BASE_URL}/dashboard", timeout=20)
        assert temp in rd.text
        # revert
        admin_session.post(f"{BASE_URL}/profile/update",
                           data={"full_name": original}, allow_redirects=True, timeout=20)

    def test_change_password_flow(self, admin_session):
        # Wrong current password
        r = admin_session.post(f"{BASE_URL}/profile/password",
                               data={"current_password": "wrong-pass",
                                     "new_password": "newpass123",
                                     "confirm_password": "newpass123"},
                               allow_redirects=True, timeout=20)
        assert r.status_code == 200
        assert "danger" in _flash_categories(r.text)

        # Mismatched confirm
        r = admin_session.post(f"{BASE_URL}/profile/password",
                               data={"current_password": ADMIN_PASSWORD,
                                     "new_password": "newpass123",
                                     "confirm_password": "different99"},
                               allow_redirects=True, timeout=20)
        assert "danger" in _flash_categories(r.text)

        # Valid change
        new_pw = "TempPass987"
        r = admin_session.post(f"{BASE_URL}/profile/password",
                               data={"current_password": ADMIN_PASSWORD,
                                     "new_password": new_pw,
                                     "confirm_password": new_pw},
                               allow_redirects=True, timeout=20)
        assert "success" in _flash_categories(r.text), _flash_messages(r.text)

        # Change back to admin123 for future test runs
        r = admin_session.post(f"{BASE_URL}/profile/password",
                               data={"current_password": new_pw,
                                     "new_password": ADMIN_PASSWORD,
                                     "confirm_password": ADMIN_PASSWORD},
                               allow_redirects=True, timeout=20)
        assert "success" in _flash_categories(r.text), \
            f"CRITICAL: could not restore admin password. flashes: {_flash_messages(r.text)}"


# =========================================================
# 6) Admin monitoring + access control
# =========================================================
class TestAdmin:
    def test_admin_dashboard_ok(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/admin", timeout=20)
        assert r.status_code == 200
        for tid in ("admin-title", "admin-stat-users", "admin-stat-students",
                    "admin-stat-courses", "admin-stat-sessions", "admin-uptime",
                    "admin-requests", "admin-appstatus", "admin-chart-departments",
                    "admin-chart-activity"):
            assert f'data-testid="{tid}"' in r.text, f"missing {tid} on /admin"
        # chart.js loaded
        assert "chart.umd.min.js" in r.text

    def test_non_admin_cannot_access(self):
        s = requests.Session()
        # register a fresh user
        email = f"testuser_{uuid.uuid4().hex[:6]}@example.com"
        pw = "secret123"
        r = s.post(f"{BASE_URL}/register",
                   data={"full_name": "Test User", "email": email,
                         "password": pw, "confirm_password": pw},
                   allow_redirects=True, timeout=20)
        assert r.status_code == 200
        # login
        r2 = _login(s, email, pw)
        assert r2.status_code == 200
        assert 'data-testid="dashboard-title"' in r2.text
        # hit /admin
        r3 = s.get(f"{BASE_URL}/admin", allow_redirects=True, timeout=20)
        assert r3.status_code == 200
        # We should have been redirected to /dashboard with danger flash
        cats = _flash_categories(r3.text)
        msgs = " ".join(m for _, m in _flash_messages(r3.text))
        assert "danger" in cats, f"expected danger flash, got: {_flash_messages(r3.text)}"
        assert "Admin access required" in msgs
        # nav should NOT show monitoring link
        assert 'data-testid="nav-admin"' not in r3.text
        _logout(s)


# =========================================================
# 7) 404 error page
# =========================================================
class TestErrorPages:
    def test_404_page(self):
        r = requests.get(f"{BASE_URL}/does-not-exist", timeout=15)
        assert r.status_code == 404
        assert "This page drifted into the clouds" in r.text
        assert 'data-testid="err-home"' in r.text


# =========================================================
# 8) Nav bar role-based links
# =========================================================
class TestNav:
    def test_logged_out_nav(self):
        r = requests.get(f"{BASE_URL}/", timeout=15)
        for tid in ("nav-features", "nav-about", "nav-contact", "nav-login", "nav-register"):
            assert f'data-testid="{tid}"' in r.text
        for tid in ("nav-dashboard", "nav-students", "nav-courses",
                    "nav-profile", "nav-logout", "nav-admin"):
            assert f'data-testid="{tid}"' not in r.text

    def test_admin_nav(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/dashboard", timeout=15)
        for tid in ("nav-dashboard", "nav-students", "nav-courses",
                    "nav-profile", "nav-logout", "nav-admin"):
            assert f'data-testid="{tid}"' in r.text, f"admin nav missing {tid}"

    def test_regular_user_nav_no_admin(self):
        s = requests.Session()
        email = f"navtest_{uuid.uuid4().hex[:6]}@example.com"
        pw = "secret123"
        s.post(f"{BASE_URL}/register",
               data={"full_name": "Nav Test", "email": email,
                     "password": pw, "confirm_password": pw},
               allow_redirects=True, timeout=20)
        _login(s, email, pw)
        r = s.get(f"{BASE_URL}/dashboard", timeout=15)
        for tid in ("nav-dashboard", "nav-students", "nav-courses",
                    "nav-profile", "nav-logout"):
            assert f'data-testid="{tid}"' in r.text
        assert 'data-testid="nav-admin"' not in r.text
        _logout(s)


# =========================================================
# 9) Dashboard shows real activity (not hardcoded)
# =========================================================
class TestDashboardActivity:
    def test_activity_feed_from_atlas(self, admin_session):
        # generate a fresh activity event
        admin_session.get(f"{BASE_URL}/dashboard", timeout=15)
        r = admin_session.get(f"{BASE_URL}/dashboard", timeout=15)
        assert 'data-testid="activity-panel"' in r.text
        # our admin's login event should be listed
        assert ADMIN_EMAIL in r.text
        # stat cards clickable → link targets
        assert 'href="/students"' in r.text or "/students" in r.text
        assert 'href="/courses"' in r.text or "/courses" in r.text


# =========================================================
# 10) Session isolation after logout
# =========================================================
class TestSessionIsolation:
    def test_logout_blocks_protected_routes(self):
        s = requests.Session()
        _login(s, ADMIN_EMAIL, ADMIN_PASSWORD)
        _logout(s)
        for path in ("/students", "/courses", "/profile", "/admin"):
            r = s.get(f"{BASE_URL}{path}", allow_redirects=False, timeout=15)
            assert r.status_code in (301, 302), f"expected redirect for {path}, got {r.status_code}"
            assert "/login" in r.headers.get("Location", ""), f"{path} did not redirect to login"
