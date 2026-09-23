# Security (DevSecOps)

Security is built into every layer: the network, the host, the proxy, the application, the code and the pipeline.

## Security measures

| # | Layer | Measure | Where |
|---|---|---|---|
| 1 | Network | **NSG port lockdown with Terraform.** Only 80/443 are public. SSH, Jenkins, Grafana and Prometheus are open to the admin IP only. Gunicorn's 8000 is closed. | `infra/terraform/` |
| 2 | Network | Gunicorn binds to **127.0.0.1** only. PostgreSQL listens on localhost only. | `deploy/systemd/gunicorn.service` |
| 3 | Transport | **HTTPS with Let's Encrypt**, HTTP→HTTPS redirect, auto-renewal, HSTS (1 year) | `deploy/nginx/epiconnect.conf` |
| 4 | Proxy | **Security headers, securityheaders.com grade A**: CSP, HSTS, X-Frame-Options DENY, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, `server_tokens off` | nginx conf |
| 5 | Proxy | `/metrics` denied publicly. Uploads limited to 10 MB. `/media/` served with a sandbox CSP and nosniff so uploads can't run as HTML/JS. | nginx conf |
| 6 | App | **django-axes brute-force protection**: lockout after 5 failures per username or IP, 1 h cool-off, custom lockout page, admin view of attempts | `settings.py` |
| 7 | App | **django-ratelimit**: register 5/min, login 10/min, posts 10/min, comments 20/min | views |
| 8 | App | **Real client IP** from Nginx's `X-Real-IP`; `X-Forwarded-For` is ignored because clients can spoof it | `core/utils.py` |
| 9 | App | **Custom audit log**: logins, logouts, failed logins, lockouts, registrations, profile and content changes, with IP and user agent. Read-only in the admin. | `auditlog/` |
| 10 | App | **Security dashboard** for superusers | `/security/dashboard/` |
| 11 | App | **Strong password policy**: min 8 chars, not common, not numeric-only, not similar to the username | `AUTH_PASSWORD_VALIDATORS` |
| 12 | App | Secure cookies (`Secure`, `HttpOnly`), CSRF on every POST, `SECURE_PROXY_SSL_HEADER`, clickjacking protection. `SECRET_KEY` is required in production (startup fails without it). | `settings.py` |
| 13 | App | **Authorization checks**: verified-student gate, owner-only edit/delete, conversation participants only, superuser-only dashboard | mixins and views |
| 14 | App | **Upload validation**: chat images must decode with Pillow, max 5 MB | `messaging/views.py` |
| 15 | App | **Business-logic integrity**: idempotent point awards (no farming), atomic balance updates, row locking on redemptions (no double spend) | `wallet/utils.py`, `wallet/views.py` |
| 16 | App | **XSS-safe rendering**: Django auto-escaping, and notification JSON is escaped before `innerHTML` | `templates/base.html` |
| 17 | Code | **Bandit SAST**: 0 issues on 2,781 lines | [reports/bandit-report.txt](reports/bandit-report.txt) |
| 18 | Supply chain | **pip-audit SCA**: 0 known CVEs in runtime dependencies. Runtime and dev tooling are split. | [reports/pip-audit-report.json](reports/pip-audit-report.json) |
| 19 | Pipeline | Scans and tests **gate the deployment**: a finding stops the pipeline before the app restarts | `Jenkinsfile` stage 3–4 |
| 20 | Cloud | **Microsoft Defender for Cloud** (Foundational CSPM) with Secure Score recommendations | Azure portal |
| 21 | Ops | Daily **Azure Backup** of the VM, plus a DB and media dump to Blob Storage | `deploy/scripts/backup_db.sh` |

## Threat model (STRIDE summary)

| Threat | Example | Mitigation (#) |
|---|---|---|
| **S**poofing | Password brute force; spoofing `X-Forwarded-For` to dodge the lockout | 6, 7, 8, 11 |
| **T**ampering | CSRF; tampering with another user's item or listing | 12, 13 |
| **R**epudiation | "I never deleted that listing" | 9 |
| **I**nformation disclosure | Reading others' chats; exposing `/metrics` or Grafana | 1, 2, 5, 13 |
| **D**enial of service | Registration spam, large uploads | 5, 7 |
| **E**levation of privilege | Unverified user posting; non-admin opening the dashboard | 13 |
| (Web) XSS / malicious upload | HTML file uploaded as a "photo"; item title with `<script>` | 5, 14, 16 |
| (Logic) Abuse | Like/unlike loop to farm points; double-click redeem | 15 |

## Security fixes in v1.1 (September 2026)

A code audit before the final documentation found these issues, all now fixed and covered by tests:

| Severity | Issue | Fix |
|---|---|---|
| **Critical** | Unresolved git merge-conflict markers committed in `users/views.py`, so the app couldn't start from a clean clone | Resolved; kept the version with audit logging |
| **High** | `requirements.txt` couldn't be installed: `django-prometheus 2.4.1` requires Django < 6 | Upgraded to `django-prometheus 2.5.0`; split dev tools into `requirements-dev.txt` |
| **High** | Known CVEs in Django 6.0.4, Pillow 12.2.0 and sqlparse 0.5.5 | Django 6.0.8, Pillow 12.3.0, sqlparse 0.6.0; pip-audit clean |
| **High** | Behind Nginx every request came from `127.0.0.1`, so 5 failed logins **by anyone** locked **everyone** out (axes IP lockout) | Real IP from `X-Real-IP` (#8) |
| **Medium** | Rate-limit key `X-Forwarded-For` is client-controlled and could be bypassed by changing the header | `key='ip'` with the trusted helper |
| **Medium** | Chat accepted any file as an "image" (stored XSS via `/media/`) | Pillow validation, size limit, sandboxed `/media/` |
| **Medium** | Notification dropdown built HTML from item titles (stored XSS) | JS escaping |
| **Medium** | Points farming: like/unlike toggling and flipping item status repeatedly | Idempotent awards with a unique `(wallet, reference)` constraint |
| **Medium** | Race condition on perk redemption (double spend, overselling) | `transaction.atomic` + `select_for_update` + `F()` |
| Low | Hard-coded fallback `SECRET_KEY` in production | Required outside DEBUG |
| Low | CSRF errors behind Nginx worked around with `CSRF_COOKIE_SECURE=False` | Proper fix: `SECURE_PROXY_SSL_HEADER` |
| Low | Unverified users could comment (and earn points) | Comments need a verified student |
| Low | Notification redirect followed any URL | Internal links only |

## Reproducing the scans

```bash
bandit -r . -x ./venv,./staticfiles,./media -f txt -o bandit-report.txt
pip-audit -r requirements.txt
python manage.py check --deploy
```

## Known limitations

- The Tailwind CDN requires `'unsafe-inline'` in the CSP `script-src`. A compiled Tailwind build would let the CSP drop it.
- Rate-limit counters live in a per-process cache, so the effective limit is the rate × 3 Gunicorn workers. Redis would make them strict.
- Jenkins UI on port 8080 is plain HTTP, restricted to the admin IP and GitHub.

## Reporting a vulnerability

Email rayenmabrouk9@gmail.com. Please don't open a public issue.
