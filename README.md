# ☁️ Cloud Student Portal

A production-ready, cloud-native student management portal built with
**Python Flask** and **MongoDB Atlas**. Manage students, courses, users,
and system activity from one professionally-designed dashboard.

Built as an engineering **capstone project** — every layer (auth, CRUD,
monitoring, deployment) is production-quality and easy to read.

> Live demo: _deploy your own in ~5 minutes with the Render Blueprint below._

---

## ✨ Features

- **Modern landing page** — hero, features, about, contact sections.
- **Secure authentication** — register, login, logout with bcrypt password
  hashing, HTTP-only Flask sessions, duplicate-email guard.
- **Interactive dashboard** — live stats (users / students / courses),
  real-time activity feed from the `activity_logs` collection, quick actions.
- **Student CRUD** — add, view, edit, delete, **search**, and **paginate**
  (8 per page). Auto-generated `STU-XXX` IDs. Unique-email guard.
- **Course CRUD** — card-based catalog with per-course enrollment count.
  Enrolled-students protection blocks accidental deletion.
- **Profile management** — update name, change password (bcrypt + current
  password verification).
- **Admin monitoring dashboard** — total users / students / courses / active
  sessions (30m), uptime, request counter, application status, plus **Chart.js**
  doughnut (students by department) & bar chart (activity by day).
- **Activity logs** — every login, register, logout, and CRUD action is
  written to MongoDB with actor, target, timestamp.
- **Custom 404 / 500 pages** with a consistent brand aesthetic.
- **Responsive UI** — Bootstrap 5, IBM Plex fonts, cyan-on-navy cloud theme.
- **Production ready** — Dockerfile, Render Blueprint, health check endpoint.

---

## 🏗️ Tech stack

| Layer          | Choice                                             |
| -------------- | -------------------------------------------------- |
| Backend        | Python 3.11 · Flask 3 · Blueprints                 |
| Frontend       | Jinja2 · Bootstrap 5 · vanilla JS · Chart.js       |
| Database       | MongoDB Atlas (via PyMongo, SRV connection)        |
| Auth           | Flask sessions + bcrypt                            |
| WSGI server    | gunicorn (production) · uvicorn+asgiref (local dev)|
| Container      | Docker (python:3.11-slim, non-root user)           |
| Deploy         | Render Blueprint (`render.yaml`)                   |

---

## 📁 Folder structure

```
cloud-student-portal/
├── Dockerfile               # Production container (gunicorn + Flask)
├── Procfile                 # Heroku-style start command
├── render.yaml              # Render Blueprint (one-click deploy)
├── .dockerignore
├── .env.example             # Copy → backend/.env and fill in
├── README.md
├── backend/
│   ├── server.py            # Flask app entrypoint + blueprints + middleware
│   ├── wsgi.py              # Production WSGI entrypoint for gunicorn
│   ├── db.py                # PyMongo connection (5s timeout, lazy)
│   ├── auth_utils.py        # bcrypt + login_required + admin_required
│   ├── activity.py          # activity_logs writer + reader
│   ├── seed.py              # Idempotent seed: admin + 5 courses + 10 students
│   ├── requirements.txt
│   ├── .env                 # (not committed — copy from .env.example)
│   ├── routes/
│   │   ├── main.py          # /  and /api/health
│   │   ├── auth.py          # /register /login /logout
│   │   ├── dashboard.py     # /dashboard
│   │   ├── students.py      # /students (CRUD + search + pagination)
│   │   ├── courses.py       # /courses  (CRUD + card grid)
│   │   ├── profile.py       # /profile  + change password
│   │   └── admin.py         # /admin    (admin-only monitoring)
│   ├── templates/           # Jinja2 templates (Bootstrap 5)
│   │   ├── base.html
│   │   ├── index.html · login.html · register.html
│   │   ├── dashboard.html · profile.html · admin.html
│   │   ├── students.html · student_form.html
│   │   ├── courses.html · course_form.html
│   │   └── 404.html · 500.html
│   └── static/
│       ├── css/style.css    # Custom styles (extends Bootstrap)
│       └── js/main.js
└── docs/
    └── screenshots/         # Add your own PNGs here
```

---

## 🚀 Quick start (local development)

### Prerequisites

- Python **3.11+**
- A **MongoDB** instance — either:
  - Local MongoDB (`mongodb://localhost:27017`) — quickest
  - MongoDB Atlas free tier — recommended for parity with production

### 1 · Clone & install

```bash
git clone https://github.com/<you>/cloud-student-portal.git
cd cloud-student-portal

python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

### 2 · Configure environment

```bash
cp .env.example backend/.env
# then open backend/.env and set MONGO_URL, DB_NAME, SECRET_KEY
```

Generate a strong secret:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3 · Run the app

```bash
cd backend
gunicorn --bind 0.0.0.0:8000 wsgi:app
```

Open **http://localhost:8000**. On first boot the app **auto-seeds** the
admin user + 5 courses + 10 sample students. Log in with:

```
For security, default credentials are not published in this repository.
Set or change the administrator credentials through the application's
secure configuration/seed process before deployment.
```

> **Windows users** who can't run gunicorn: use `waitress-serve --port=8000 wsgi:app`
> after `pip install waitress`.

---

## 🐳 Docker

The included `Dockerfile` builds a slim, non-root, health-checked image
that binds to `$PORT` (defaults to `8000`).

```bash
# Build
docker build -t cloud-student-portal .

# Run — supply your MongoDB URI as an env var (never bake into the image)
docker run --rm -p 8000:8000 \
  -e MONGO_URL="mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/?retryWrites=true&w=majority" \
  -e DB_NAME="cloud_student_portal" \
  -e SECRET_KEY="$(python -c 'import secrets;print(secrets.token_hex(32))')" \
  cloud-student-portal
```

Then open **http://localhost:8000**.

---

## ☁️ Deploy to Render (Blueprint)

The included `render.yaml` deploys the app in one click.

### Steps

1. Push this repo to **GitHub**.
2. In Atlas → **Network Access**, allow `0.0.0.0/0` (or Render's egress IPs)
   so the container can reach your cluster.
3. Log into <https://render.com> → **New → Blueprint**.
4. Point it at your repo. Render detects `render.yaml`.
5. When prompted, paste your `MONGO_URL` (marked `sync:false` so it never
   ends up in git). `SECRET_KEY` is auto-generated by Render.
6. Click **Apply** — Render builds the Docker image, deploys the web service,
   and pings `/api/health` to verify.

Your app is live at `https://cloud-student-portal-<hash>.onrender.com`.

### Or without a Blueprint

- **Web service** → connect repo → **Environment: Docker**
- **Health check path:** `/api/health`
- **Environment variables:**
  - `MONGO_URL` — your Atlas SRV URI (secret)
  - `DB_NAME` — `cloud_student_portal`
  - `SECRET_KEY` — long random string
- **Instance type:** Free tier works for the demo; upgrade to `Starter` for
  always-on.

---

## 🔐 Environment variables

| Variable       | Required | Purpose                                            |
| -------------- | -------- | -------------------------------------------------- |
| `MONGO_URL`    | ✅       | MongoDB Atlas SRV connection string                |
| `DB_NAME`      | ✅       | Database name (defaults suggested: `cloud_student_portal`) |
| `SECRET_KEY`   | ✅       | Random string — signs Flask session cookies        |
| `PORT`         | ⚙️       | Render/Heroku set this; the app binds to it        |
| `CORS_ORIGINS` | ⚙️       | Optional, kept for API compatibility               |

---

## 🧪 Testing

A pytest regression suite covers the full Phase 2 API surface (32 tests):

```bash
cd backend
pytest tests/test_phase2.py -v
```

Reports are written to `/app/test_reports/`.

---

## 📸 Screenshots

Add your own captures under `docs/screenshots/`:

- `landing.png` — hero + features
- `dashboard.png` — stats + activity feed
- `students.png` — table + pagination
- `courses.png` — course cards
- `admin.png` — monitoring dashboard with Chart.js
- `profile.png` — profile & change password

---

## 🗺️ Roadmap

- [x] Landing + auth + dashboard  _(Phase 1)_
- [x] Student CRUD + Course CRUD + Profile + Admin monitoring + activity logs  _(Phase 2)_
- [x] Docker + Render + README deploy guide  _(Phase 3)_
- [ ] CSRF protection on POST forms (Flask-WTF)
- [ ] CSV import / export for students
- [ ] Login rate-limiting (brute-force guard)
- [ ] Email verification on registration

---

## 📜 License

MIT — do whatever you want, just don't hold us liable. Add a `LICENSE` file
of your choosing before publishing.

---

## 🙋 Author

Built as a final-year engineering capstone. Questions or feedback →
**ibrahim@cloud.com**
