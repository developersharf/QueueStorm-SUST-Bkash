# syntax=docker/dockerfile:1.6

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# System deps for psycopg[binary] and healthcheck curl.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps first so this layer is cached when only code changes.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy the project.
COPY . .

# Collect static files at build time (WhiteNoise serves them at runtime).
RUN python manage.py collectstatic --noinput

# Run as non-root.
RUN useradd --create-home --uid 1000 app \
 && chown -R app:app /app
USER app

EXPOSE 8000

# Container-level healthcheck against /health.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:${PORT}/health || exit 1

# Apply migrations on each release, then hand off to gunicorn.
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn ticketsort.wsgi --bind 0.0.0.0:${PORT} --workers ${GUNICORN_WORKERS:-3} --timeout ${GUNICORN_TIMEOUT:-60} --access-logfile - --error-logfile -"]