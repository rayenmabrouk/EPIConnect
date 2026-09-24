# EPIConnect - Interview Defense

How to explain the project, question by question. Every answer describes what is actually in this repository; file names are given so you can open the code while you revise. Read `docs/ARCHITECTURE.md` first.

**Golden rule:** be precise about ownership. The Django application was written with heavy AI assistance, and so was much of the modernisation code. Say so if asked, calmly, then move to what you can defend in depth: why the system is built this way, how it behaves, how it fails and how you would operate it. Interviewers reward someone who understands a system far more than someone who claims to have typed it.

---

## 1. The project

### What is EPIConnect?
A campus community platform for EPI Digital School: lost & found with photos and a status workflow, a student marketplace, a "Help Wall" for questions (with anonymous posts), one-to-one chat with images, notifications, and a points/badges/perks system that rewards helping others. Only students whose ID an admin has verified can post. It is a Django 6 monolith with server-rendered templates and PostgreSQL.

I then took it from a single, hand-configured Azure VM to a containerised deployment on AWS with an automated, security-gated delivery pipeline.

### What parts did you work on?
> "The product side - what the platform does and the requirements - and then the engineering to make it production-grade: I audited the codebase and found it didn't even start (merge-conflict markers on main), fixed the security bugs the audit found, containerised it, designed the AWS architecture, wrote it down as Terraform, built the GitHub Actions pipeline with its security gates, deployed it and verified it. I used an AI assistant heavily for the application code and for a lot of the implementation - I'm upfront about that. What I own is the architecture, the decisions and trade-offs, the deployment and operating it, and I can walk you through any part of it."

Be ready to back that up with the audit table in `docs/ARCHITECTURE.md` section 3.

### How does the application work?
- Django class-based views per app (`lostfound`, `marketplace`, `social`, `messaging`, `notifications`, `wallet`, `users`, `auditlog`, `core`); 17 models.
- Auth is Django's session auth with a custom `User` (unique e-mail) and a `StudentProfile` holding the student ID and `is_verified`. `VerifiedStudentMixin` (`users/mixins.py`) blocks posting until an admin verifies the ID (admin action in `users/admin.py`).
- Points: `wallet/utils.award_points()` inserts a `Transaction` and increments the balance in SQL (`F('balance') + n`). A `reference` key with a unique constraint makes one-off rewards idempotent (e.g. `like:<post>:<user>`), so like/unlike toggling cannot farm points.
- Redemption (`wallet/views.RedeemView`) locks the wallet and perk rows with `SELECT ... FOR UPDATE` inside a transaction, so two concurrent requests can't spend the same points.
- Chat is AJAX: the page polls `/messaging/<id>/fetch/?after=<last id>` every 3 s; sending is a POST validated by a `ModelForm` (image type/size check).
- Every security-relevant action goes to `AuditLog` (DB, shown on `/security/dashboard/`) and to the JSON log stream.

---

## 2. Architecture decisions

### Why migrate to AWS?
The Azure setup was one VM running everything (app, database, Jenkins, Prometheus/Grafana): one failure domain, OS patching by hand, deployments that copied files onto a live server, uploads that were never served in production. The goal was an immutable, reproducible deployment with managed data services and a proper delivery pipeline. AWS was the target because it is where I'm building my cloud skills (certifications, CloudPulse) and because AWS Academy gives me an environment to run it.

### Why this AWS architecture?
Start from what the application needs: a stateless web process, PostgreSQL, somewhere durable for uploads, HTTPS, and a way to run migrations. Then:
- Uploads to **S3** make the container stateless -> **Fargate** can run it with no server to manage.
- Fargate task IPs change on every deploy -> an **ALB** gives a stable target, health checks and rolling deploys.
- Uploads stay private in S3; Django hands the browser **pre-signed URLs** that expire after an hour, so nothing is public and user files come from a different origin than the app.
- Data -> **RDS PostgreSQL** in private subnets.
- Secrets -> **Secrets Manager**, injected by ECS.
- Observability -> **CloudWatch**, because JSON logs let me derive security metrics without extra infrastructure.

### Why ECS Fargate? Why not EC2, Kubernetes, App Runner or Lambda?
- **EC2**: works, but I'd be patching an OS, managing Docker on the host and writing rollback logic myself. My other project (CloudPulse) already does EC2 + Docker; Fargate is the better fit here once the app is stateless.
- **EKS**: $73/month for the control plane before running anything, plus cluster upgrades, node groups, ingress controllers - for one service, the operational cost is not justified.
- **App Runner**: closed to new customers since April 2026.
- **Lambda**: possible with the Lambda Web Adapter, but a Django monolith with polling chat means cold starts and a DB connection per concurrent invocation; you end up needing RDS Proxy.
- **Fargate** gives: per-task isolation, a task IAM role, rolling deploys with ALB health checks, a deployment circuit breaker that rolls back automatically, and one-off tasks (migrations, admin bootstrap) with the same image and secrets.

### Isn't the ALB unnecessary cost?
It's the biggest line in the bill (~$16/month), and I looked for a way around it. With Fargate, something has to track task IPs that change on every deployment, and a DNS name can't follow them. The ALB also does the health checking that makes zero-downtime deploys and the circuit breaker work. The only way to avoid it is a fixed host (EC2 + Elastic IP), which is the architecture I chose *not* to repeat. So it's a deliberate trade-off, not an oversight.

### Why no NAT gateway? Aren't the tasks in public subnets?
Yes. A NAT gateway is ~$32/month, more than the compute. The tasks get a public IP only so they can reach ECR, S3, CloudWatch and Secrets Manager. Inbound, the task security group allows only port 8000 from the ALB security group, so being in a public subnet doesn't make them reachable. The database is in private subnets with no internet route at all. In production I'd move tasks to private subnets with VPC endpoints or NAT.

### Why is the demo on HTTP? Isn't that insecure?
Yes, for real users it would be, and I say so. HTTPS needs a certificate: either an ACM certificate for a domain on the ALB, or CloudFront's `*.cloudfront.net` certificate. I have no domain, and AWS Academy denies `cloudfront:CreateDistribution` - my first design was CloudFront in front of the ALB, and the apply failed on exactly that. So the lab deployment is HTTP, and the task definition switches off the HTTPS-only Django settings explicitly (`SECURE_SSL_REDIRECT`, `Secure` cookies, HSTS) - otherwise the CSRF cookie would never be sent back over HTTP and every form would fail. The secure values are the defaults and CI checks them with `manage.py check --deploy`. With a domain it's an ACM certificate, a 443 listener, a redirect on port 80 and removing three environment variables. Uploads are already HTTPS (pre-signed S3 URLs, TLS-only bucket policy).

### How did the AWS Academy restrictions change the design?
Three things I only discovered by applying: CloudFront is fully denied (so no CDN and no HTTPS without a domain); an organisation-level service control policy denies `s3:GetBucketObjectLockConfiguration`, which the Terraform AWS provider reads for every bucket, so the two buckets are created by a CLI script instead; IAM role and OIDC creation are denied, so tasks use `LabRole` and CI uses session credentials. A good answer here: "I designed for the target, tested against the real environment, and adapted where the platform said no - and I documented each constraint and what I'd do in a normal account."

### Why Terraform, if CloudPulse already shows Terraform?
Because the environment must be destroyable and recreatable (Academy credits), and clicking it together would not be reproducible. But I kept it deliberately small: one flat configuration (`infra/`), no modules. The interesting part of this project is the application delivery and security, which lives in the pipeline. Terraform owns the infrastructure and the *shape* of the task definition; the pipeline owns which image runs (`ignore_changes` on the service's task definition).

### Why did you remove Jenkins and Prometheus/Grafana?
Jenkins needed a permanent server with sudo access to the host it deployed to; with immutable images and ECS there's no host to copy files to, and two CI systems would just double the maintenance. Prometheus/Grafana monitored a VM; on Fargate there is no VM, and running them would mean more always-on containers with storage to pay for and secure. ALB/ECS/RDS metrics are native in CloudWatch, and my JSON logs let me derive security metrics there. What I lose is per-view application metrics; I'd add them with CloudWatch EMF or an OpenTelemetry sidecar.

---

## 3. Delivery

### How does deployment work?
`scripts/ecs-deploy.sh`, called by the pipeline on `main`:
1. Read cluster, service and subnets from SSM parameters that Terraform wrote.
2. Fetch the latest task definition, replace the image with `<ECR>/epiconnect:<commit-sha>`, register a new revision.
3. Run `migrate` as a **one-off Fargate task** with that revision; wait; check the exit code. If migrations fail, stop - the old version is still serving.
4. `update-service` to the new revision. ECS starts the new task, the ALB health-checks `/healthz/`, then the old task is drained (minimum healthy 100 %, maximum 200 %) - no downtime.
5. `wait services-stable`, then verify the service is really running the new revision (if the circuit breaker rolled back, fail).
6. Smoke test against the public URL; if it fails, point the service back to the previous revision.

### Why run migrations as a separate task?
If every container ran `migrate` at start-up, two tasks starting together would race, and a failing migration would crash-loop the new tasks while the old ones keep running against a half-migrated schema. A single one-off task before the rollout runs once, and its failure stops the deploy cleanly. The trade-off is that migrations must stay backward-compatible with the previous version for the few minutes both run (add columns first, remove later).

### How does GitHub Actions work here?
`.github/workflows/pipeline.yml`:
- **test**: ruff, `makemigrations --check`, Django's `check --deploy --fail-level WARNING` with production settings, 50 tests against a PostgreSQL service container, coverage.
- **security**: gitleaks (full history), Bandit, pip-audit, npm audit, hadolint, zizmor, Checkov.
- **terraform**: fmt + validate.
- **image**: build once; Trivy gate; SBOM; run the image the way ECS runs it (read-only FS, no capabilities, non-root, separate migrate container) and test it; OWASP ZAP baseline against it; on `main`, push to ECR tagged with the commit SHA.
- **deploy** (main only): the steps above.

Pull requests run everything except the AWS steps. Other workflows: CodeQL, Infrastructure (Terraform plan/apply/destroy), Ops (one-off commands).

### How are AWS credentials handled?
- **In CI:** AWS Academy doesn't allow creating an OIDC identity provider or IAM roles, so the pipeline uses the lab's temporary session credentials, stored as encrypted GitHub secrets and refreshed each lab session. They expire after a few hours, which limits exposure. In a normal account I'd use GitHub OIDC: the workflow gets a short-lived token, AWS STS exchanges it for a role whose trust policy only accepts this repository and the `main` branch / `production` environment - no stored keys at all.
- **In the app:** no keys. boto3 gets temporary credentials from the ECS task role.
- **Least privilege:** in a normal account `infra/iam.tf` creates an execution role (pull image, write logs, read *one* secret) and a task role (read/write only `media/*` in *one* bucket). In Academy both are `LabRole`, which is broader - I know that and would not ship it that way.

### How are secrets handled?
Terraform generates the Django `SECRET_KEY`, the DB password and an initial admin password and stores them as one JSON secret in Secrets Manager. The task definition references `arn:...:SECRET_KEY::`; the ECS agent fetches the values at task start and sets them as environment variables inside the container only. They're not in the image, the repo, the task definition or the pipeline logs. The admin account is created by a one-off task (`bootstrap_admin`) that reads the password from Secrets Manager itself. Weak point I'd mention: the values are also in the Terraform state, which is why the state bucket is private, encrypted, versioned and TLS-only; the next step would be write-only attributes or managed rotation.

### What happens if a deployment fails?
Depends where:
- **Tests/scans fail** -> nothing is published.
- **Migration task fails** -> the service is never updated; old version keeps serving.
- **New task never becomes healthy** -> ECS deployment circuit breaker stops the rollout and returns to the last good revision; the script detects it and fails the job.
- **Healthy but broken** (smoke test fails: missing header, DB not reachable, static files 404) -> the workflow updates the service back to the previous task definition.
Because images are immutable and tagged by commit, rolling back is just pointing the service at an older revision.

---

## 4. Security

### What security controls did you implement?
Group them in three layers (details: `docs/ARCHITECTURE.md` section 8):
- **Pipeline:** secret scanning, SAST (Bandit + CodeQL), dependency scanning, hash-pinned dependencies, IaC scanning, Dockerfile lint, image scanning with a gate, SBOM, DAST (ZAP), pipeline hardening (SHA-pinned actions, minimal token permissions, zizmor).
- **Application:** brute-force lockout, rate limits, non-spoofable client IP, upload validation, nonce-based CSP, security headers, secure cookies, authorization checks, race-free wallet, audit trail.
- **Infrastructure:** ALB as the only public component, private DB, least-privilege security groups, encryption at rest, TLS-only buckets, secrets manager, non-root read-only containers, immutable images.

### What vulnerabilities did you find?
Good stories to tell, each with a regression test:
1. **Rate-limit and lockout bypass via X-Forwarded-For.** The code keyed rate limits on the raw header and the audit log trusted its first value. A client can send any value, so an attacker could rotate fake IPs to avoid lockout. Fix: `TrustedProxyMiddleware` trusts only the right-most N hops (N = number of proxies I control), because each proxy *appends*. Test: `core/tests.py::TrustedProxyTests`.
2. **Stored XSS through chat uploads.** The chat view wrote `request.FILES['image']` directly to the model, skipping validation, so an `.html` file would be stored and served from the site's origin. Fix: a `ModelForm` (Pillow verification), extension allow-list, size limit, random names; plus uploads are now served from S3. Test: `messaging/tests.py`.
3. **Double spending in the wallet.** Check-then-update without locking. Fix: `select_for_update()` in a transaction + SQL-side decrement.
4. **Points farming.** Like/unlike or lost/found flipping paid out every time. Fix: idempotency key with a unique constraint.
5. **Verification bypass:** a verified student could change their student ID. Fix: field disabled once verified.
6. **DOM XSS sink** in the notification dropdown (`innerHTML` with item titles). Fix: escaping.
7. **Dependency CVEs** found by pip-audit in the pipeline (`sqlparse`, `urllib3`) - pinned to fixed versions.
Also: the app didn't start (merge-conflict markers), uploaded images weren't served in production, and the requirements weren't installable.

### How does container scanning work?
Trivy runs twice on the image built in the job. The gate run fails the build on HIGH or CRITICAL vulnerabilities **that have a fix available** (`ignore-unfixed`), in OS packages and Python libraries, plus secrets baked into layers - failing on unfixable CVEs would just block every build without making anything safer. The second run reports everything as SARIF to GitHub's Security tab. A CycloneDX SBOM is attached to each run. ECR also scans on push. Exceptions would go in `.trivyignore` with a reason and review date; it is empty.

### Why both Bandit and CodeQL?
Bandit is fast and pattern-based ("is `subprocess` called with `shell=True`?") and blocks the pipeline in seconds. CodeQL does data-flow analysis - it follows untrusted input from the request to a dangerous sink - and it also analyses the JavaScript and the workflow files, which Bandit can't.

### Explain the CSP.
`script-src 'self' 'nonce-<random>'`: only scripts from our origin or inline blocks carrying the per-request nonce run, so injected `<script>` or `onclick=` attributes don't execute. To get there I compiled Tailwind at build time (the old CDN script compiled CSS in the browser) and moved every inline handler into `static/js/app.js` with `data-*` attributes. A test asserts no page renders an inline handler, and the E2E browser run checks for CSP violations. `style-src` still allows `'unsafe-inline'` because templates use `style=""` attributes - a known, lower-risk compromise.

---

## 5. Operations

### How does monitoring work?
The app logs one JSON object per line to stdout (`core/logging.py`, Gunicorn access log format in `docker/gunicorn.conf.py`); ECS ships it to CloudWatch Logs. Metric filters turn log events into metrics: failed logins, lockouts, 429s, application errors. Alarms: failed-login spike, application errors, no healthy target, target 5xx, ECS memory, RDS CPU and storage -> SNS. One dashboard shows traffic, latency p50/p95, ECS and RDS, and the security metrics, with a Logs Insights table of recent audit events.

### How do you debug a production problem?
Dashboard first (is it traffic, errors, latency, DB?), then Logs Insights, e.g. `fields @timestamp, status, path, duration_ms | filter event = "access" and status >= 500`. ECS service events explain failed task starts (image pull, secret access, health check). `/readyz/` tells me if the app can reach the DB. For a one-off command there's the Ops workflow.

### How would you scale it?
Horizontally: the task is stateless (sessions and rate-limit counters in PostgreSQL, uploads in S3), so `desired_count` can go up and an ECS target-tracking policy on CPU or ALB requests per target can manage it. Vertically: bigger task sizes, more Gunicorn workers. Then the database: a bigger instance, read replicas, and RDS Proxy if connection counts grow. A CDN in front would offload static files. Two things to change as it grows: Redis for rate limiting/caching (DB increments aren't atomic under load), and WebSockets instead of 3-second chat polling.

### What would you change for production?
In order: OIDC + least-privilege roles instead of Academy credentials; custom domain with ACM and HTTPS to the ALB; WAF; 2+ tasks across AZs with autoscaling; Multi-AZ RDS with deletion protection; private subnets + VPC endpoints; secret rotation; approvals on the production environment; longer log retention and tracing.

### What does it cost?
About $52/month if left running (~$1.7/day): ALB $16, RDS $14, public IPv4s $11, Fargate $9, the rest ~$2. On the $50 Academy budget I create it for demos and destroy it with the Infrastructure workflow.

---

## 6. Likely follow-up probes (short answers)

- **"What is `ignore-unfixed`?"** Don't fail on CVEs that have no patched version yet; they're reported, not gated.
- **"Why `--require-hashes`?"** pip refuses any package whose sha256 doesn't match the lock file: protects against a compromised index/mirror or a re-uploaded package.
- **"Why pin actions to SHAs?"** Tags can be moved (this happened in real supply-chain attacks on popular actions); a commit SHA can't.
- **"Liveness vs readiness?"** `/healthz/` doesn't touch the DB, so a DB outage doesn't make ECS kill every web task (which would turn a DB problem into a full outage). `/readyz/` checks the DB for the smoke test.
- **"Why is ALLOWED_HOSTS a problem behind an ALB?"** The ALB health checker sends the task's private IP as `Host`; the health middleware answers before host validation, so `ALLOWED_HOSTS` stays strict.
- **"Where are sessions stored?"** PostgreSQL (Django's default DB sessions) - that's what makes tasks stateless.
- **"How do you create the first admin?"** Ops workflow -> `bootstrap_admin`; the password is read from Secrets Manager inside the task.
- **"What's the blast radius if the image is compromised?"** Non-root, read-only filesystem, no capabilities, can only reach AWS APIs over 443 and the DB; its role (in a normal account) can only touch `media/*` in one bucket and read one secret.
- **"What would you do differently?"** Check the lab's permission boundaries before designing (CloudFront was my plan A), get a domain for HTTPS, and use a real AWS account with OIDC from day one.
