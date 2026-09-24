# Security Policy - EPIConnect

## Reporting a vulnerability

Please do not open a public issue. Use GitHub's private vulnerability reporting (Security tab -> "Report a vulnerability") or e-mail the maintainer. Expect an answer within a week.

## Controls in place

The full description, with the reason for each control, is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#8-devsecops-and-security). Summary:

**Delivery pipeline** - gitleaks (secrets, full history), Bandit and CodeQL (SAST), pip-audit and npm audit (dependencies), hash-pinned dependencies, Checkov (Terraform, Dockerfile, workflows), hadolint, zizmor, Trivy image gate (fixable HIGH/CRITICAL) with SBOM, container runtime checks, OWASP ZAP baseline, Django deployment checklist, post-deploy smoke test with rollback. Actions pinned to commit SHAs, minimal token permissions.

**Application** - django-axes lockout (5 failures / 1 h), rate limiting (IP and per user, DB-backed), non-spoofable client IP behind CloudFront + ALB, image upload validation, nonce-based Content-Security-Policy, HSTS and security headers, Secure/HttpOnly/SameSite cookies, CSRF protection, strong password validation, authorization on every update/delete, student verification, race-free wallet operations, open-redirect guard, audit log (database + structured logs).

**Infrastructure (AWS)** - HTTPS via CloudFront; ALB reachable only from CloudFront (prefix list + secret header); database in private subnets, TLS enforced, encrypted; private S3 uploads via Origin Access Control; secrets in AWS Secrets Manager injected at runtime; non-root, read-only containers; immutable image tags with scan on push; CloudWatch alarms on failed-login spikes and errors.

## Known limitations (AWS Academy environment)

- IAM roles and OIDC cannot be created in the lab: the tasks use `LabRole` and CI uses short-lived lab session credentials. Least-privilege roles are defined in `infra/iam.tf` for a normal account.
- No custom domain: CloudFront -> ALB traffic is HTTP inside AWS (the ALB cannot be reached directly).
- No WAF, single task, single-AZ database (cost / lab limits).
