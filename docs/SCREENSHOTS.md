# Screenshot checklist

The original screenshots were lost, so this is the list to retake. Save each file in `docs/screenshots/` with the **exact file name** below so the docs and report can reference them. Use a 1920×1080 window, dark mode, and crop out browser bars unless the URL or padlock matters.

✅ = retaken · ⬜ = to do

## A. Azure (portal.azure.com)

| ☐ | File | What to capture |
|---|---|---|
| ⬜ | `azure-01-resource-group.png` | Resource group `epiconnect-rg`: list of all resources (VM, NIC, NSG, IP, disk, VNet) |
| ⬜ | `azure-02-vm-overview.png` | VM `epiconnect-vm` Overview: status Running, size B2ts_v2, Sweden Central, public IP, DNS name |
| ⬜ | `azure-03-region-policy-error.png` | *(optional, to reproduce)* the `RequestDisallowedByAzure` error on another region |
| ⬜ | `azure-04-nsg-rules.png` | NSG → Inbound security rules after `terraform apply` (443/80 Internet, 22/3000/8080/9090 admin IP) |
| ⬜ | `azure-05-defender-secure-score.png` | Defender for Cloud → Secure Score / recommendations |
| ⬜ | `azure-06-backup.png` | VM → Backup: policy and last successful backup |
| ⬜ | `azure-07-blob-backups.png` | Storage account → container `backups` with `db-*.dump` / `media-*.tar.gz` |

## B. Terraform (terminal)

| ☐ | File | What to capture |
|---|---|---|
| ⬜ | `tf-01-plan.png` | `terraform plan` output (resources to add or import) |
| ⬜ | `tf-02-apply.png` | `terraform apply`: *Apply complete!* and outputs |

## C. Server (SSH terminal)

| ☐ | File | Command |
|---|---|---|
| ⬜ | `vm-01-ssh.png` | `ssh rayen9@4.223.163.106` welcome banner |
| ⬜ | `vm-02-services.png` | `systemctl status gunicorn nginx postgresql --no-pager` (all *active (running)*) |
| ⬜ | `vm-03-nginx-test.png` | `sudo nginx -t` |
| ⬜ | `vm-04-healthz.png` | `curl -s -H "Host: localhost" http://127.0.0.1:8000/healthz/` |
| ⬜ | `vm-05-certbot.png` | `sudo certbot certificates` |
| ⬜ | `vm-06-listening-ports.png` | `sudo ss -tlnp` (Gunicorn on 127.0.0.1:8000, Postgres on 127.0.0.1:5432) |

## D. Jenkins (http://4.223.163.106:8080)

| ☐ | File | What to capture |
|---|---|---|
| ⬜ | `jenkins-01-stage-view.png` | Pipeline **Stage View**, all 7 stages green |
| ⬜ | `jenkins-02-console-security.png` | Console output of stage 3: Bandit *No issues identified* + pip-audit *No known vulnerabilities* |
| ⬜ | `jenkins-03-console-tests.png` | Console output of stage 4: `Ran 50 tests ... OK` |
| ⬜ | `jenkins-04-console-verify.png` | Stage 7: `/healthz/ -> HTTP 200 ... Deployment verified.` |
| ⬜ | `jenkins-05-artifacts.png` | Build page with archived `reports/` artifacts |
| ⬜ | `jenkins-06-failed-build.png` | *(optional)* a red build blocked by a failing test or scan: shows the gate works |
| ⬜ | `github-01-webhook.png` | GitHub → Settings → Webhooks: green ✓ on the last delivery |

## E. Monitoring

| ☐ | File | What to capture |
|---|---|---|
| ⬜ | `prom-01-targets.png` | Prometheus `/targets`: `prometheus`, `node`, `django` all **UP** |
| ⬜ | `grafana-01-node-1860.png` | Dashboard #1860 Node Exporter Full (CPU, RAM, disk, network) |
| ⬜ | `grafana-02-django-17658.png` | Dashboard #17658 Django (requests/s, latency, responses by status, DB queries) |

## F. Security

| ☐ | File | What to capture |
|---|---|---|
| ⬜ | `sec-01-securityheaders-A.png` | https://securityheaders.com/?q=epiconnect.swedencentral.cloudapp.azure.com grade **A** |
| ⬜ | `sec-02-ssl-padlock.png` | Browser padlock → certificate details (Let's Encrypt) |
| ⬜ | `sec-03-axes-lockout.png` | Lockout page after 5 wrong passwords |
| ⬜ | `sec-04-security-dashboard.png` | `/security/dashboard/` with stats and the audit log |
| ⬜ | `sec-05-admin-auditlog.png` | `/admin/auditlog/auditlog/` list |
| ⬜ | `sec-06-admin-axes.png` | `/admin/axes/accessattempt/` |
| ⬜ | `sec-07-metrics-403.png` | `https://…/metrics` → 403 |
| ⬜ | `sec-08-ratelimit-403.png` | *(optional)* 6th registration in a minute → 403 |

## G. Application (browser, https://epiconnect.swedencentral.cloudapp.azure.com)

Seed some realistic data first: 3–4 users, a few items, listings, posts, likes and messages.

| ☐ | File | Page |
|---|---|---|
| ⬜ | `app-01-home.png` | Home page with stats and recent activity |
| ⬜ | `app-02-register.png` | Registration form (student ID field) |
| ⬜ | `app-03-login.png` | Login |
| ⬜ | `app-04-verification-required.png` | Unverified user trying to post |
| ⬜ | `app-05-admin-verify.png` | Admin → Student profiles → *Verify selected students* |
| ⬜ | `app-06-lostfound-list.png` | Lost & Found list with filters |
| ⬜ | `app-07-lostfound-detail.png` | Item detail with the history timeline |
| ⬜ | `app-08-lostfound-form.png` | Report form ("I lost / I found") |
| ⬜ | `app-09-marketplace-list.png` | Marketplace grid with category and sort |
| ⬜ | `app-10-marketplace-detail.png` | Listing detail with "Message seller" |
| ⬜ | `app-11-helpwall-feed.png` | Help Wall feed including an **Anonymous** post |
| ⬜ | `app-12-helpwall-post.png` | Post with comments and like button |
| ⬜ | `app-13-messaging-inbox.png` | Inbox with unread badges |
| ⬜ | `app-14-messaging-chat.png` | Chat with a text and an image message |
| ⬜ | `app-15-notifications.png` | Notification dropdown open |
| ⬜ | `app-16-wallet.png` | Wallet: balance, transactions, how to earn |
| ⬜ | `app-17-perks.png` | Perks shop |
| ⬜ | `app-18-leaderboard.png` | Monthly leaderboard with badges |
| ⬜ | `app-19-profile.png` | Public profile with badges |
| ⬜ | `app-20-dashboard.png` | User dashboard |
| ⬜ | `app-21-mobile.png` | Any page in mobile view (DevTools → iPhone 14) |

## H. Code quality

| ☐ | File | What to capture |
|---|---|---|
| ⬜ | `code-01-tests.png` | `python manage.py test`: 50 tests OK |
| ⬜ | `code-02-bandit.png` | `bandit -r . -x ./venv,./staticfiles,./media`: 0 issues |
| ⬜ | `code-03-pip-audit.png` | `pip-audit -r requirements.txt`: no known vulnerabilities |
| ⬜ | `code-04-check-deploy.png` | `python manage.py check --deploy`: no issues |
