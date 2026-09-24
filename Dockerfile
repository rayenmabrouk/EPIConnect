# syntax=docker/dockerfile:1.7
#
# EPIConnect production image
#   stage 1 "assets"  : compile Tailwind CSS (Node is not shipped in the final image)
#   stage 2 "builder" : install hash-pinned Python dependencies into a virtualenv
#   stage 3 "runtime" : slim Python + venv + code, non-root, read-only friendly
#
# Base images are pinned by tag (literal FROM lines so Dependabot can bump them).

# ---------------------------------------------------------------------------
FROM node:25-bookworm-slim AS assets
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
# Tailwind scans templates, forms and JS to decide which classes to emit
COPY frontend/ ./
COPY templates/ /build/templates/
COPY static/ /build/static/
COPY users/forms.py lostfound/forms.py marketplace/forms.py social/forms.py /build/forms/
RUN npm run build

# ---------------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS builder
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
COPY requirements.txt /tmp/requirements.txt
# --require-hashes: every wheel must match the sha256 recorded in the lock file
RUN /opt/venv/bin/pip install --require-hashes --no-deps -r /tmp/requirements.txt

# ---------------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="EPIConnect" \
      org.opencontainers.image.description="Campus community platform (Django)" \
      org.opencontainers.image.source="https://github.com/rayenmabrouk/EPIConnect"

# Apply Debian security updates published after the base image was built
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=epiconnect.settings \
    PORT=8000

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
# Code is owned by root and read-only for the app user
COPY . .
COPY --from=assets /build/static/css/app.css /app/static/css/app.css

# Hashed, compressed static files are baked into the image (served by WhiteNoise).
# The dummy key only satisfies settings import; nothing is signed at build time.
RUN SECRET_KEY=collectstatic-build-only python manage.py collectstatic --noinput --verbosity 0 \
 && python -m compileall -q /app /opt/venv \
 && chmod +x docker/entrypoint.sh \
 && mkdir -p /app/media && chown app:app /app/media

USER 10001:10001
EXPOSE 8000

# Liveness only (no DB): an unreachable database should not get the container killed
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz/', timeout=4).status == 200 else 1)"]

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["web"]
