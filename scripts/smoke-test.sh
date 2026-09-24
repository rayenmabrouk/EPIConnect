#!/usr/bin/env bash
# Post-deployment checks against the public URL (through CloudFront).
#   scripts/smoke-test.sh https://dxxxxxxxx.cloudfront.net
set -euo pipefail
URL="${1:?usage: smoke-test.sh <base-url>}"
URL="${URL%/}"
FAIL=0

check() { # name, expected, actual
  if [ "$2" = "$3" ]; then echo "PASS  $1"; else echo "FAIL  $1 (expected '$2', got '$3')"; FAIL=1; fi
}
status() { curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$@"; }

# Retry the first request: a fresh deployment may still be warming up
for _ in $(seq 1 12); do
  code=$(status "$URL/healthz/") && [ "$code" = "200" ] && break
  echo "waiting for $URL/healthz/ ($code)..."; sleep 10
done

check "liveness /healthz/"                  200 "$(status "$URL/healthz/")"
check "readiness /readyz/ (database)"       200 "$(status "$URL/readyz/")"
check "home page"                           200 "$(status "$URL/")"
check "login page"                          200 "$(status "$URL/users/login/")"
check "private page redirects to login"     302 "$(status "$URL/users/dashboard/")"
check "HTTP redirected to HTTPS"            301 "$(status "http://${URL#https://}/")"

headers=$(curl -s -D - -o /dev/null --max-time 20 "$URL/")
has() { if grep -qiE "$1" <<<"$headers"; then echo yes; else echo no; fi; }
check "HSTS header"          yes "$(has '^strict-transport-security: max-age=31536000')"
check "CSP with nonce"       yes "$(has "^content-security-policy: .*script-src 'self' 'nonce-")"
check "X-Frame-Options DENY" yes "$(has '^x-frame-options: DENY')"
check "Secure CSRF cookie"   yes "$(has '^set-cookie: csrftoken=.*; Secure')"

css=$(curl -s --max-time 20 "$URL/" | grep -o '/static/css/app\.[0-9a-f]*\.css' | head -1 || true)
if [ -n "$css" ]; then
  check "hashed stylesheet served via CloudFront" 200 "$(status "$URL$css")"
else
  check "hashed stylesheet referenced" yes no
fi

exit $FAIL
