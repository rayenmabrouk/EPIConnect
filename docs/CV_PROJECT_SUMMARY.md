# EPIConnect - CV Project Summary

What you can put on a CV, and what you can defend. Everything below exists in the repository and was deployed; nothing is aspirational. Items that were designed but could not run in AWS Academy are marked.

## Project ownership

**Legitimately yours:**
- Product owner of EPIConnect: the platform's purpose, features and rules (student verification, points economy, moderation via admin).
- Audit of the existing codebase and deployment; prioritising what to fix.
- Architecture and technology decisions for the AWS migration (Fargate vs EC2/EKS/Lambda, pre-signed S3 URLs for private uploads, no NAT gateway, CloudWatch instead of Prometheus/Grafana, removing Jenkins) and the trade-offs behind them.
- Providing and operating the AWS environment: deploying, verifying, monitoring, rolling back, destroying/recreating within a $50 budget.
- Security design: which controls, where, and why.
- The documentation and being able to explain every part of the system.

**Say it honestly:**
- Much of the modernisation code (Dockerfile, Terraform, workflows, scripts) was also implemented with an AI assistant under your direction. The honest framing is the one already used in CloudPulse: *"built with an AI assistant as a pair programmer; I made the decisions, ran and verified the deployment, and can explain every part."*

## Application

Campus community platform for EPI Digital School (Django 6, PostgreSQL): lost & found with photos and a status workflow, student marketplace, Q&A "Help Wall" with anonymous posts, one-to-one chat with images, notifications, and a gamified points/badges/perks system. Student-ID verification by admins, security audit dashboard. 9 Django apps, 17 models, 49 automated tests.

## AWS

Actually deployed (us-east-1, AWS Academy Learner Lab):
- **Amazon ECS on AWS Fargate** - the Django container, rolling deployments with the deployment circuit breaker
- **Application Load Balancer** - public entry point, health checks, zero-downtime rollouts
- **Amazon RDS for PostgreSQL 17** - private subnets, encryption at rest, TLS enforced
- **Amazon S3** - private bucket for user uploads served through pre-signed URLs; separate encrypted, versioned bucket for Terraform state
- **Amazon ECR** - immutable tags, scan on push, lifecycle policy
- **AWS Secrets Manager** - application secrets injected by ECS
- **AWS Systems Manager Parameter Store** - deployment metadata for the pipeline
- **Amazon CloudWatch** - logs, log metric filters, alarms, dashboard; **Amazon SNS** for alarm notifications
- **Amazon VPC** - public/private subnets across 2 AZs, security-group chaining, no NAT gateway

Designed, not deployable in Academy: least-privilege IAM task/execution roles and GitHub OIDC federation (the lab forbids creating IAM roles and identity providers; `LabRole` and session credentials are used instead), and HTTPS (no domain, and the lab denies CloudFront: the demo runs over HTTP on the ALB, with the app's HTTPS settings switched back on by removing three environment overrides once a certificate exists).

## DevOps

- Containerisation: multi-stage Docker build (Node asset stage, hash-verified Python dependencies, slim non-root runtime), works with a read-only root filesystem, health check, one image for web and one-off tasks; `docker compose` environment mirroring production.
- CI/CD with GitHub Actions: tests on PostgreSQL, build once and promote the same image, push to ECR by commit SHA, database migrations as a one-off Fargate task, rolling deploy, post-deploy smoke test, automatic rollback.
- Infrastructure as Code: one compact Terraform configuration with remote state in S3 (native locking), separate plan/apply/destroy workflow applying the saved plan.
- Operations: Ops workflow for one-off management commands, Dependabot for all ecosystems, destroy/recreate procedure for cost control.
- Replaced a VM + systemd + Jenkins deployment with an immutable, containerised one.

## DevSecOps

- Security gates in the pipeline: gitleaks (secrets, full history), Bandit and CodeQL (SAST), pip-audit and npm audit (SCA), Trivy (image vulnerabilities + secrets, gate on fixable HIGH/CRITICAL), CycloneDX SBOM, Checkov (Terraform, Dockerfile, workflows), hadolint, zizmor (workflow security), OWASP ZAP baseline (DAST) against the running container, Django deployment checklist.
- Supply chain: hash-pinned Python lock file (`--require-hashes`), GitHub Actions pinned to commit SHAs, minimal workflow token permissions.
- Found and fixed real vulnerabilities, each with a regression test: rate-limit/lockout bypass through a spoofed `X-Forwarded-For`, stored XSS via unvalidated chat uploads, wallet double-spend race condition, points-farming logic flaws, student-verification bypass, DOM XSS sink, vulnerable transitive dependencies.
- Application hardening: nonce-based Content-Security-Policy (removed runtime third-party script), security headers, HTTPS-ready settings (HSTS, secure cookies) verified in CI, brute-force lockout, per-user/IP rate limiting, upload validation.
- Security monitoring: audit events as structured logs -> CloudWatch metrics and alarms (failed-login spikes, lockouts, rate limiting, errors).

## Infrastructure

- Network: VPC with public/private subnets in 2 AZs; internet -> ALB -> task -> database, each hop allowed only from the previous one (security-group references); database without internet route; no NAT gateway (cost).
- Adapting to a restricted platform: discovered and worked around AWS Academy restrictions (CloudFront denied, an SCP breaking Terraform's S3 bucket reads, no IAM role creation) and documented each one.
- Data: RDS PostgreSQL with forced TLS and encryption; S3 with public access blocked, TLS-only policy, versioning.
- Cost engineering: ~$52/month if always on (~$1.7/day), itemised; expensive components (NAT, EKS, Multi-AZ, WAF) consciously excluded and listed as production upgrades.

## Interview claims you can make confidently

After reading `docs/ARCHITECTURE.md` and `docs/INTERVIEW_DEFENSE.md` you should be able to explain:
- Why Fargate for this app, and why not EC2, EKS, App Runner or Lambda.
- The full request path and the controls on each hop, why the lab demo is HTTP and exactly what turns HTTPS on.
- How a deployment works, why migrations run in a one-off task, and the three different failure/rollback paths.
- How secrets and AWS credentials are handled, the Academy limitation, and what OIDC would change.
- Each pipeline security tool: what it catches and why it is (or isn't) a blocking gate.
- The vulnerabilities found: cause, impact, fix and test.
- Monitoring: how log lines become metrics and alarms.
- Cost breakdown and what you'd change for production.

## Suggested CV entry

**EPIConnect - Campus platform modernised to AWS with DevSecOps** *(Django, Docker, AWS ECS Fargate, RDS, S3, Terraform, GitHub Actions)*
- Migrated a Django campus platform from a single Azure VM to AWS: containerised (non-root, read-only), ECS Fargate behind an ALB, RDS PostgreSQL in private subnets, private S3 uploads via pre-signed URLs, Secrets Manager; infrastructure in Terraform.
- Built a GitHub Actions pipeline that tests on PostgreSQL, gates on SAST/SCA/secret/IaC/image scans (Bandit, CodeQL, pip-audit, gitleaks, Checkov, Trivy) and a ZAP DAST scan, then deploys the same image with one-off migration tasks, rolling updates, smoke tests and automatic rollback.
- Audited the codebase and fixed security flaws with regression tests (spoofable client-IP rate limiting, upload stored XSS, wallet race condition); added nonce-based CSP and CloudWatch security alerting from structured logs.
- AI-assisted implementation; owned architecture, deployment and operations.

Keep "AI-assisted" (or say it in the interview) - it is consistent with CloudPulse and protects your credibility.
