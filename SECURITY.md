# Security Policy — EPIConnect

## Application Security
- django-axes: account lockout after 5 failed attempts
- django-ratelimit: rate limiting on login and register
- Audit logging: all critical actions logged
- Security dashboard at /security/dashboard/ (superuser only)
- Strong password validation
- Bandit scan: 0 issues in 2247 lines of code
- pip-audit: 0 exploitable vulnerabilities

## Infrastructure Security
- NSG: Grafana, Jenkins, Prometheus restricted to admin IP
- Microsoft Defender for Cloud: enabled
- Azure Backup: daily automated VM backup
- SSL: Let's Encrypt with auto-renewal
- Security headers: Grade A on securityheaders.com
