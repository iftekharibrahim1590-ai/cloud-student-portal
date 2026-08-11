# ---- Cloud Student Portal · production image ----
# Slim Python base, gunicorn, MongoDB Atlas ready.
FROM python:3.11-slim

# Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

WORKDIR /app

# System deps kept minimal — bcrypt has wheels for slim, so no build tools needed
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps first (better layer caching)
COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# App code
COPY backend/ ./

# Non-root user (best practice)
RUN useradd --create-home --uid 1000 csp && chown -R csp:csp /app
USER csp

EXPOSE 8000

# Cloud health check (Render / Kubernetes / etc.)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS http://127.0.0.1:${PORT}/api/health || exit 1

# `sh -c` so the shell expands ${PORT} at runtime (Render injects it)
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --timeout 60 --access-logfile - --error-logfile - wsgi:app"]
