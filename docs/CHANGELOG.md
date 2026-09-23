# Changelog

## v1.1.0: 2026-09-23 (audit, fixes and documentation)

### Fixed
- **Build:** unresolved merge-conflict markers in `users/views.py` (the app couldn't start).
- **Build:** uninstallable `requirements.txt` (`django-prometheus 2.4.1` requires Django < 6). Now 2.5.0.
- **CVEs:** Django 6.0.4 → 6.0.8, Pillow 12.2.0 → 12.3.0, sqlparse 0.5.5 → 0.6.0.
- **Security:** real client IP behind Nginx for axes, ratelimit and the audit log (stops the site-wide lockout and the `X-Forwarded-For` spoofing).
- **Security:** CSRF behind the proxy fixed with `SECURE_PROXY_SSL_HEADER` (secure cookies back on).
- **Security:** chat uploads validated as real images (max 5 MB); `/media/` sandboxed in Nginx.
- **Security:** stored XSS in the notification dropdown.
- **Security:** notification redirect limited to internal URLs; `SECRET_KEY` required in production.
- **Logic:** points farming through like/unlike and item-status flipping (idempotent awards); race condition on perk redemption (atomic + row locks).
- **Logic:** comments now require a verified student, like posts; like notifications are sent only once.
- Password help text said 6 characters while the validator requires 8.

### Added
- Prometheus integration in the code: `django_prometheus` app, middleware, DB and cache wrappers, loopback-only `/metrics`.
- `/healthz/` endpoint (app + DB).
- Audit log entries for item, listing and post create/update/delete, and account lockouts.
- 50 automated tests covering all apps.
- `deploy/`: Nginx config (TLS, headers, CSP), systemd unit, Prometheus config, Grafana datasource provisioning, backup script.
- `infra/terraform/`: NSG as code.
- `.env.example`, `requirements-dev.txt`.
- Full documentation in `docs/`.

### Changed
- Jenkins pipeline: `rsync` instead of `cp`; new **Security Scan** and **Check & Test** gates; `/healthz/` verification with retries; no concurrent builds.
- Security dashboard: 403 for non-superusers instead of a redirect loop; aggregation done in SQL.
- Leaderboard: removed an N+1 query.
- Time zone `Africa/Tunis` by default.

## v1.0.0: 2026-05-03
- Security: django-axes, django-ratelimit, audit log, security dashboard, CVE fixes.

## v0.2.0: 2026-04-22
- Jenkins CI/CD pipeline (7 stages) and GitHub webhook.

## v0.1.0: 2026-04-13
- Initial release: users, lost & found, marketplace, Help Wall, messaging, notifications, wallet & gamification.
