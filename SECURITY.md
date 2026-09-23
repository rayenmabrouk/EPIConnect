# Security Policy — EPIConnect

The full description of the security measures, the threat model and the scan results is in **[docs/SECURITY.md](docs/SECURITY.md)**.

## Summary
- django-axes: lockout after 5 failed logins (per username / real client IP), 1 h cool-off
- django-ratelimit on register, login, posts and comments
- Custom audit log + superuser security dashboard (`/security/dashboard/`)
- Strong password validation, secure cookies, CSRF, HSTS, CSP — securityheaders.com grade A
- Bandit: 0 issues · pip-audit: 0 known CVEs (enforced in the Jenkins pipeline)
- NSG port lockdown managed by Terraform; Microsoft Defender for Cloud; daily backups

## Reporting a vulnerability
Please email **rayenmabrouk9@gmail.com** instead of opening a public issue.
