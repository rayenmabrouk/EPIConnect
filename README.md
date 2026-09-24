# EPIConnect

**A campus community platform for EPI Digital School, modernised from a single Azure VM to a containerised, security-gated deployment on AWS.**

[![CI/CD](https://github.com/rayenmabrouk/EPIConnect/actions/workflows/pipeline.yml/badge.svg)](https://github.com/rayenmabrouk/EPIConnect/actions/workflows/pipeline.yml)
[![CodeQL](https://github.com/rayenmabrouk/EPIConnect/actions/workflows/codeql.yml/badge.svg)](https://github.com/rayenmabrouk/EPIConnect/actions/workflows/codeql.yml)

Students report lost and found items, buy and sell on a marketplace, ask for help on a Q&A wall (anonymously if they want), chat, and earn points and badges for helping each other. Only students whose ID has been verified by an administrator can post.

Django 6 · PostgreSQL · Docker · AWS ECS Fargate · RDS · S3 · CloudFront · Terraform · GitHub Actions

---

## Architecture

```mermaid
flowchart LR
    user["Browser"] -->|HTTPS| cf["CloudFront"]
    cf -->|"only CloudFront allowed"| alb["ALB"] --> ecs["ECS Fargate<br/>Django + Gunicorn"]
    cf -->|"/media/* via OAC"| s3[("S3 uploads")]
    ecs --> rds[("RDS PostgreSQL<br/>private subnets")]
    ecs --> s3
    sm[("Secrets Manager")] -.-> ecs
    ecs --> cw["CloudWatch<br/>logs, security metrics, alarms"]
    gh["GitHub Actions<br/>tests, security gates"] -->|image| ecr[("ECR")] -.-> ecs
```

Why these services, the request path, and the trade-offs: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## What this project demonstrates

| Area | Highlights |
|---|---|
| **Modernisation** | Audited a broken codebase (it did not start), fixed it, and moved it from VM + systemd + Jenkins to immutable containers on ECS Fargate with RDS, S3 and CloudFront |
| **DevSecOps** | Pipeline gates: gitleaks, Bandit, CodeQL, pip-audit, npm audit, Checkov, hadolint, zizmor, Trivy (+ SBOM), OWASP ZAP against the running container; hash-pinned dependencies and SHA-pinned actions |
| **Application security** | Fixed a spoofable-IP rate-limit/lockout bypass, stored XSS via uploads, a wallet race condition and points-farming flaws, each with a regression test; nonce-based CSP |
| **Delivery** | Build once, deploy the same image: ECR -> migration as a one-off task -> rolling update -> smoke test -> automatic rollback |
| **Operations** | Structured JSON logs turned into CloudWatch security metrics and alarms; dashboard; one-click destroy/recreate for cost control |

## How this was built


My other project, [CloudPulse](https://github.com/rayenmabrouk/cloudpulse), is the complement: an existing open-source app with AWS infrastructure (EC2, Terraform modules, Prometheus/Grafana) built around it.

## Run it

```bash
docker compose up --build    # http://localhost:8000
```

Deploying to AWS, operations, rollback, cost control and troubleshooting: [docs/RUNBOOK.md](docs/RUNBOOK.md).

## Repository layout

| Path | Contents |
|---|---|
| `users/ lostfound/ marketplace/ social/ messaging/ notifications/ wallet/ auditlog/ core/` | Django apps |
| `epiconnect/settings.py` | Environment-driven settings (security headers, CSP, storage, logging) |
| `templates/`, `static/`, `frontend/` | Templates, JS, Tailwind build config |
| `Dockerfile`, `docker/`, `compose.yaml` | Container image and local environment |
| `infra/` | Terraform for the AWS environment |
| `.github/workflows/` | CI/CD, CodeQL, Infrastructure, Ops |
| `scripts/` | Deploy, one-off task, smoke test, container test, state bootstrap |
| `docs/` | Architecture, runbook, interview preparation, CV summary |

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - application, original deployment, AWS design, CI/CD, DevSecOps, monitoring, cost
- [Runbook](docs/RUNBOOK.md) - local run, deployment, rollback, observability, troubleshooting
- [Interview defense](docs/INTERVIEW_DEFENSE.md) - questions and answers about the implementation
- [CV project summary](docs/CV_PROJECT_SUMMARY.md)
- [Security policy](SECURITY.md)
