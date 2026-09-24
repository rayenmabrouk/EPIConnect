# EPIConnect - Operations Runbook

How to run, deploy, operate and tear down EPIConnect.

## Local development

```bash
docker compose up --build          # PostgreSQL + migrations + app on http://localhost:8000
docker compose run --rm web createsuperuser
docker compose run --rm web seed_perks
docker compose down -v             # stop and delete local data
```

The `web` container runs exactly like on ECS: non-root, read-only root filesystem, all capabilities dropped. Settings for local use are in `.env.example`.

Without Docker (Python 3.13, Node 22):

```bash
python -m venv .venv && . .venv/bin/activate
pip install --require-hashes -r requirements.txt -r requirements-dev.txt
(cd frontend && npm ci && npm run build)     # compiles static/css/app.css
DEBUG=true python manage.py migrate && DEBUG=true python manage.py runserver
DEBUG=true STATIC_MANIFEST=false python manage.py test
```

## First deployment to AWS (AWS Academy)

1. **Start the Learner Lab** and copy the *AWS CLI* credentials into `~/.aws/credentials`.
2. **Put them in GitHub** (they expire with the lab session; repeat each session):
   `powershell -ExecutionPolicy Bypass -File scripts\refresh-github-aws-secrets.ps1`
3. **Create the infrastructure:** GitHub -> Actions -> *Infrastructure* -> Run workflow -> `apply`.
   The job creates the Terraform state bucket if needed, plans, and applies that plan (~10-15 min, mostly RDS and CloudFront). The ECS service is created with 0 tasks.
4. **Deploy the application:** Actions -> *CI/CD* -> Run workflow (or push to `main`). The pipeline builds, scans, pushes the image, runs migrations and scales the service to 1 task. The URL is in the run summary and in the SSM parameter `/epiconnect/deploy/app_url`.
5. **Create the admin account:** Actions -> *Ops* -> `bootstrap_admin`. Username `admin`; the password is the `ADMIN_PASSWORD` key of the Secrets Manager secret `epiconnect/app` (AWS console -> Secrets Manager -> Retrieve secret value). Optionally run `seed_perks`.
6. Log in at `/admin/`, verify student accounts (Student profiles -> select -> "Verify selected students").

## Routine deployment

Merge to `main`. Nothing else: the pipeline does build -> gates -> ECR -> migration task -> rolling update -> smoke test.

## Rollback

- Automatic: circuit breaker (new task unhealthy) or smoke-test failure (workflow rolls back to the previous task definition).
- Manual, to any earlier version:
  ```bash
  aws ecs list-task-definitions --family-prefix epiconnect --sort DESC --max-items 5
  aws ecs update-service --cluster epiconnect --service epiconnect-web --task-definition epiconnect:<revision>
  aws ecs wait services-stable --cluster epiconnect --services epiconnect-web
  ```
  Migrations are not rolled back automatically; write them backward-compatible.

## Observability

- Dashboard: CloudWatch -> Dashboards -> `epiconnect` (URL is a Terraform output).
- Logs: log group `/ecs/epiconnect`. Useful Logs Insights queries:
  ```
  fields @timestamp, status, method, path, duration_ms
  | filter event = "access" and status >= 500 | sort @timestamp desc

  fields @timestamp, action, client_ip, details
  | filter event = "audit" | sort @timestamp desc | limit 50

  fields @timestamp, logger, message, exception
  | filter level = "ERROR" | sort @timestamp desc
  ```
- Alarm e-mails: set `alarm_email` (Terraform variable) and confirm the SNS subscription e-mail.
- Service events (why a task did not start): ECS -> Clusters -> epiconnect -> Services -> epiconnect-web -> Events.

## Cost control

~$1.7/day while running. After a demo:

- **Destroy everything:** Actions -> *Infrastructure* -> `destroy` (database and uploads are deleted). Recreate later with steps 3-5 above.
- **Pause cheaply for a few days:** scale the service to 0 and stop the database (the ALB still costs ~$0.55/day; RDS restarts itself after 7 days):
  ```bash
  aws ecs update-service --cluster epiconnect --service epiconnect-web --desired-count 0
  aws rds stop-db-instance --db-instance-identifier epiconnect-db
  ```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Pipeline fails at "AWS credentials" | Lab session expired | Restart the lab, refresh `~/.aws/credentials`, rerun `refresh-github-aws-secrets.ps1`, re-run the job |
| "AWS infrastructure not found ... deploy skipped" | Infrastructure not applied (or destroyed) | Run *Infrastructure* -> `apply`, then re-run *CI/CD* |
| Migration task fails | Bad migration or DB unreachable | Read the task's log stream `web/web/<task-id>`; service was not changed |
| Task stops with `ResourceInitializationError` | Cannot pull image / read the secret | Check the task has a public IP, outbound 443 allowed, secret exists |
| Tasks start then get replaced | ALB health check failing | Check `/healthz/` in the task logs; container must listen on 8000 |
| Site shows 403 "Forbidden" (plain text) | Request reached the ALB without CloudFront's secret header | Use the CloudFront URL, not the ALB DNS name |
| Redirect loop | `SECURE_PROXY_SSL_HEADER` not set to `HTTP_CLOUDFRONT_FORWARDED_PROTO` | Task definition env (Terraform `ecs.tf`) |
| 400 Bad Request | Host not in `ALLOWED_HOSTS` | Must be the CloudFront domain (set by Terraform) |
| CSRF failure on forms | Origin not in `CSRF_TRUSTED_ORIGINS` or cookie not sent over HTTP | Use `https://<cloudfront domain>` |
| Uploaded image 403 from CloudFront | Object outside `media/` or bucket policy missing | Check `aws_s3_bucket_policy.media` |
| 429 Too Many Requests | Rate limit or axes lockout | Wait (lockout 1 h) or reset in admin -> Axes |
