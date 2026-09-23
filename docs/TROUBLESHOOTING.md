# Troubleshooting: problems hit during the project

These are real issues from building and deploying EPIConnect, with the root cause and the fix for each.

## 1. Azure region blocked by policy

**Symptom:** VM creation fails with

```
"code": "RequestDisallowedByAzure",
"message": "Resource 'epiconnect-vm' was disallowed by Azure: This policy maintains a set of best available regions where your subscription can deploy resources..."
```

The same error appeared for the NSG, VNet and public IP.

**Cause:** Azure for Students subscriptions have an Azure Policy that restricts the allowed regions. France Central, West Europe, East US and East US 2 were all refused.

**Fix:** Deploy everything in **Sweden Central**. To list the allowed regions instead of guessing:

```powershell
az policy assignment list --query "[].{name:displayName, params:parameters}" -o json
```

## 2. VM size not available / quota

**Symptom:** `B1s` / `B2s` greyed out or a quota error.

**Fix:** Use `Standard_B2ts_v2` (2 vCPU, 1 GiB, ≈ $8.76/month), which is available in Sweden Central within the student quota. Leave **Azure Spot** unchecked, because a Spot VM can be evicted in the middle of a demo.

## 3. Port 8000 unreachable while testing

**Symptom:** `python manage.py runserver 0.0.0.0:8000` works on the VM, but the browser times out.

**Cause:** The NSG only had 22 and 80.

**Fix (temporary, for testing):** Networking → Add inbound rule, destination port `8000`, source port `*`, TCP, name `allow-8000`. **Remove it afterwards.** In the final setup Gunicorn listens on 127.0.0.1 and Terraform manages the NSG without 8000.

## 4. CSRF verification failed / 500 behind Nginx

**Symptom:** Login and forms fail with "CSRF verification failed" (or a 500 with DEBUG off) once the site is behind Nginx with HTTPS.

**Cause:** Nginx talks to Gunicorn over plain HTTP, so Django thought every request was `http://`. Django's CSRF origin check compares the browser's `Origin: https://…` with what it believes is `http://…`, and rejects it. The early workaround was `CSRF_COOKIE_SECURE=False`, which weakens cookie security.

**Proper fix (v1.1):**

```python
# settings.py
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS = ['https://epiconnect.swedencentral.cloudapp.azure.com']
```

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
```

Secure cookies are back on (`HTTPS=True` in `.env`).

## 5. Jenkins "Permission denied" / file ownership conflicts

**Symptom:** Stage *Update Code* fails with `cp: cannot create regular file ... Permission denied`, or Gunicorn can't read files Jenkins copied.

**Cause:** Files in `/var/www/EPIConnect` belonged to `rayen9` (manual deploy). Jenkins runs as `jenkins`, and `cp -r` also tried to copy `.git` and preserve modes.

**Fix:** A shared group with setgid on the directory, and `rsync --no-owner --no-group` with a group-writable `--chmod` (see [CICD.md → Permissions](CICD.md#permissions-the-fix-for-the-file-ownership-conflicts)). Gunicorn runs with `UMask=0002` so uploaded media also stays group-writable.

## 6. Jenkins "Verify Deployment" returned 400

**Symptom:** `curl http://localhost` in the pipeline returned **400 Bad Request**.

**Cause:** `Host: localhost` wasn't in `ALLOWED_HOSTS`.

**Fix:** Send the real host header: `curl -H "Host: epiconnect.swedencentral.cloudapp.azure.com"`. In v1.1 the stage polls `/healthz/` on Gunicorn directly and retries up to 10 times.

## 7. Grafana datasource not saved

**Symptom:** The Prometheus datasource added through the UI or API kept disappearing or failing, and dashboards showed *"Datasource not found"*.

**Original workaround:** A Python script that pushed the datasource through Grafana's HTTP API.

**Fix (v1.1):** Declarative provisioning, `deploy/monitoring/grafana/datasource.yml` → `/etc/grafana/provisioning/datasources/`. Grafana loads it at every start, with a fixed `uid: prometheus` that the imported dashboards can reference.

## 8. Everyone locked out after a few bad passwords

**Symptom:** After 5 failed logins (from any user), nobody could log in for an hour.

**Cause:** django-axes locks by IP, and behind Nginx every request arrived from `127.0.0.1`.

**Fix (v1.1):** `AXES_CLIENT_IP_CALLABLE = 'core.utils.get_client_ip'`, which reads `X-Real-IP` set by Nginx. To unlock someone immediately:

```bash
venv/bin/python manage.py axes_reset                      # everyone
venv/bin/python manage.py axes_reset_username <username>
```

## 9. `pip install -r requirements.txt` fails on a fresh machine

**Symptom:** `ResolutionImpossible ... django-prometheus 2.4.1 depends on Django<6.0`.

**Fix (v1.1):** `django-prometheus==2.5.0`, which supports Django 6.0.

## 10. `SyntaxError` in `users/views.py`

**Symptom:** Django won't start and points at `<<<<<<< Updated upstream`.

**Cause:** A `git stash pop` conflict was committed without being resolved.

**Fix (v1.1):** Resolved. Stage 4 (`manage.py check` plus tests) now catches this before anything restarts.

## 11. Site down after a VM stop/start

**Cause:** A dynamic public IP changed.

**Fix:** Set the public IP to **Static** and use the DNS name `epiconnect.swedencentral.cloudapp.azure.com` everywhere.

## Quick diagnostics

```bash
sudo systemctl status gunicorn nginx postgresql jenkins prometheus grafana-server --no-pager
sudo journalctl -u gunicorn -n 100 --no-pager
sudo nginx -t
curl -s -H "Host: localhost" http://127.0.0.1:8000/healthz/
free -h && df -h /
```
