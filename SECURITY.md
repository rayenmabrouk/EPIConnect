# Security Policy - EPIConnect

## Reporting a vulnerability

Please do not open a public issue. Use GitHub's private vulnerability reporting (Security tab -> "Report a vulnerability") or e-mail the maintainer. Expect an answer within a week.

## Controls in place

The full description, with the reason for each control, is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#8-devsecops-and-security). Summary:

**Delivery pipeline** - gitleaks (secrets, full history), Bandit and CodeQL (SAST), pip-audit and npm audit (dependencies), hash-pinned dependencies, Checkov (Terraform, Dockerfile, workflows), hadolint, zizmor, Trivy image gate (fixable HIGH/CRITICAL) with SBOM, container runtime checks, OWASP ZAP baseline, Django deployment checklist, post-deploy smoke test with rollback. Actions pinned to commit SHAs, minimal token permissions.

**Application** - django-axes lockout (5 failures / 1 h), rate limiting (IP and per user, DB-backed), non-spoofable client IP behind the ALB, image upload validation, nonce-based Content-Security-Policy, security headers, HttpOnly/SameSite cookies (Secure + HSTS whenever served over HTTPS), CSRF protection, strong password validation, authorization on every update/delete, student verification, race-free wallet operations, open-redirect guard, audit log (database + structured logs).

**Infrastructure (AWS)** - ALB as the only public component; tasks reachable only from the ALB; database in private subnets, TLS enforced, encrypted; private S3 uploads via short-lived pre-signed URLs, TLS-only bucket policies; secrets in AWS Secrets Manager injected at runtime; non-root, read-only containers; immutable image tags with scan on push; CloudWatch alarms on failed-login spikes and errors.

## Known limitations (AWS Academy environment)

- IAM roles and OIDC cannot be created in the lab: the tasks use `LabRole` and CI uses short-lived lab session credentials. Least-privilege roles are defined in `infra/iam.tf` for a normal account.
- No HTTPS in the lab deployment: there is no domain for an ACM certificate and the lab denies CloudFront, so the demo is served over HTTP on the ALB with the HTTPS-only Django settings switched off by environment variables. Uploads are still HTTPS (pre-signed S3 URLs).
- No WAF, single task, single-AZ database (cost / lab limits).
