#!/usr/bin/env bash
# Run the freshly built image the way ECS runs it (read-only root filesystem,
# no capabilities, non-root) against a throwaway PostgreSQL, and check it works.
#   scripts/ci-container-test.sh <image>
# Leaves the app listening on http://localhost:8000 for the DAST scan.
set -euo pipefail
IMAGE="${1:?usage: ci-container-test.sh <image>}"
NET=epiconnect-ci
DB_PASSWORD="ci-only-$(date +%s)"

docker network create "$NET" >/dev/null 2>&1 || true
docker run -d --name ci-db --network "$NET" \
  -e POSTGRES_DB=epiconnect -e POSTGRES_USER=epiconnect -e POSTGRES_PASSWORD="$DB_PASSWORD" \
  postgres:17-alpine >/dev/null
until docker exec ci-db pg_isready -U epiconnect -d epiconnect >/dev/null 2>&1; do sleep 1; done

COMMON=(--network "$NET"
  -e DATABASE_URL="postgres://epiconnect:${DB_PASSWORD}@ci-db:5432/epiconnect"
  -e SECRET_KEY="ci-container-test-$(openssl rand -hex 32)"
  -e "ALLOWED_HOSTS=localhost,127.0.0.1"
  -e CSRF_TRUSTED_ORIGINS=http://localhost:8000
  -e SECURE_SSL_REDIRECT=false -e SECURE_HSTS_SECONDS=0
  --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges)

echo "--- migrate (one-off container, same as the ECS one-off task)"
docker run --rm "${COMMON[@]}" "$IMAGE" migrate

echo "--- start web"
docker run -d --name ci-web -p 8000:8000 "${COMMON[@]}" "$IMAGE" >/dev/null

for _ in $(seq 1 30); do
  [ "$(docker inspect -f '{{.State.Health.Status}}' ci-web)" = "healthy" ] && break
  sleep 2
done

fail=0
check() { if [ "$2" = "$3" ]; then echo "PASS  $1"; else echo "FAIL  $1 (expected '$2', got '$3')"; fail=1; fi; }
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }

check "Docker HEALTHCHECK reports healthy" healthy "$(docker inspect -f '{{.State.Health.Status}}' ci-web)"
check "runs as non-root uid 10001"         10001   "$(docker exec ci-web id -u)"
check "root filesystem is read-only"       denied  "$(docker exec ci-web sh -c 'touch /app/x 2>/dev/null && echo writable || echo denied')"
check "/healthz/"                          200     "$(code http://localhost:8000/healthz/)"
check "/readyz/ (database reachable)"      200     "$(code http://localhost:8000/readyz/)"
check "home page"                          200     "$(code http://localhost:8000/)"
check "register page"                      200     "$(code http://localhost:8000/users/register/)"
check "unknown Host rejected"              400     "$(code -H 'Host: evil.example' http://localhost:8000/)"
css=$(curl -s http://localhost:8000/ | grep -o '/static/css/app\.[0-9a-f]*\.css' | head -1 || true)
check "compiled Tailwind CSS served"       200     "$(code "http://localhost:8000${css:-/missing}")"

if [ "$fail" != 0 ]; then docker logs ci-web | tail -50; exit 1; fi
echo "container checks passed"
