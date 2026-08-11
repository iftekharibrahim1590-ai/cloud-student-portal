"""WSGI entrypoint for production servers (gunicorn, uWSGI, mod_wsgi).

The `server.py` module exports two things:
  - `flask_app` — the raw Flask (WSGI) application
  - `app`      — the ASGI-wrapped Flask, needed only by our dev environment
                  where supervisor runs `uvicorn server:app`

For real deployments (Render / Docker / Heroku) we don't need ASGI, so
gunicorn imports the plain Flask app from here:

    gunicorn --bind 0.0.0.0:$PORT wsgi:app
"""
from server import flask_app as app  # noqa: F401
