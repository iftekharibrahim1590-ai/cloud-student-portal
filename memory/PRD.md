# Cloud Student Portal — PRD

## Original problem statement
Build a production-quality cloud-ready web application named **Cloud Student
Portal** using **Python Flask** as the backend, MongoDB, Bootstrap 5, deployable
on Render, containerised with Docker.

## Architecture
- **Flask** app at `/app/backend/server.py` wrapped with `asgiref.wsgi.WsgiToAsgi`
  so uvicorn/supervisor can run it as ASGI.
- **Node reverse-proxy** on port 3000 (`/app/frontend/proxy.js`) forwards
  non-`/api` traffic to Flask on 8001, letting Jinja pages render at `/`,
  `/login`, `/dashboard`, etc.
- **MongoDB Atlas** (`cloud_student_portal` db) via sync PyMongo — collections:
  `users`, `students`, `courses`, `activity_logs`.
- Session auth with **bcrypt** + Flask sessions.
- Blueprint layout: `main`, `auth`, `dashboard`, `students`, `courses`,
  `profile`, `admin`. Runtime metrics (uptime + request counter) via a
  request-count middleware and context processor.

## User personas
- **Admin** — full access, monitoring dashboard, all CRUD.
- **Registered user** — Students/Courses/Profile access, no monitoring.

## Implemented so far

### Phase 1 (2026-02-17)
- Landing page (hero / features / about / contact)
- Auth (register / login / logout, bcrypt, duplicate-email guard, session)
- Dashboard with stats + quick actions
- Seeded admin (`ibrahim@cloud.com` / `admin123`)
- `/api/health` endpoint
- Flask + ASGI + Node proxy wiring

### MongoDB Atlas connect (2026-02-17)
- `.env` switched to Atlas SRV URI + `cloud_student_portal` db.
- 5s server-selection timeout for fast failure.
- Seed tolerant of Atlas outage.

### Phase 2 (2026-02-17)
- **`activity_logs` collection** with `activity.log()` / `activity.recent()`.
  Auto-writes on register, login, logout, student CRUD, course CRUD,
  profile update, password change.
- **Student CRUD** at `/students`: search (name/email/id/dept/course),
  8-per-page pagination, auto-generated `STU-XXX` IDs, unique-email guard.
  Seeded 10 sample students.
- **Course CRUD** at `/courses`: card grid with per-course enrollment count;
  in-use protection blocks deletion when students are enrolled. Seeded 5
  sample courses.
- **Profile** at `/profile`: update name + change password (bcrypt).
- **Admin monitoring** at `/admin` (admin-only): total users/students/courses,
  active sessions (30 min), uptime, request counter, application status;
  **Chart.js** doughnut (students by department) + bar (activity by day).
- Custom **404** & **500** pages.
- Dashboard now reads real activity from Atlas; stat cards clickable.
- Role-aware navbar (Dashboard / Students / Courses / Profile / [Monitoring] / Logout).
- **Testing:** 32/32 pytest backend + 100% Playwright UI smoke pass
  (`/app/test_reports/iteration_2.json`).

## Deferred backlog

### P0 — deployment story
- **Dockerfile** + `.dockerignore` for containerised Flask.
- **Render** deployment: `render.yaml`, `Procfile`, `PORT` env handling,
  deploy guide in `README.md`.
- Production `SESSION_COOKIE_SECURE=True`, `FLASK_DEBUG=0`.

### P1 — hardening
- **Flask-WTF CSRF** on all POST forms.
- Rate limiting on `/login` (brute-force guard).
- Padded / counter-based `student_id` sequence (current lexicographic sort
  breaks past STU-099).
- Structured logging for `activity.log()` failures.

### P2 — feature polish
- CSV import/export for students (10× student-mgmt speed).
- Loading spinners & optimistic UI on delete.
- Email verification on registration.
- Password strength meter.
- Screenshots section in README.

## Next tasks
1. Ship Dockerfile + render.yaml + README deploy guide.
2. Add CSRF to POST forms.
3. Extend seed / ID generator to handle scale (>99 students).
4. CSV import/export for students.
