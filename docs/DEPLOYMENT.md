# Deployment guide: Azure VM

This takes a fresh Azure for Students subscription to EPIConnect running at `https://epiconnect.swedencentral.cloudapp.azure.com`.

> Commands are run on your PC (PowerShell) or on the VM (`rayen9@epiconnect-vm$`), as indicated.

---

## Part 1: Create the VM (Azure portal)

1. **Resource group** → Create → name `epiconnect-rg`, region **Sweden Central**.
2. **Virtual machines** → Create → Azure virtual machine:

| Field | Value |
|---|---|
| Resource group | `epiconnect-rg` |
| VM name | `epiconnect-vm` |
| Region | **Sweden Central** (other regions are blocked by the student policy) |
| Availability options | No infrastructure redundancy required |
| Image | Ubuntu Server 24.04 LTS – x64 Gen2 |
| Size | `Standard_B2ts_v2` (2 vCPU, 1 GiB, ≈ $8.76/month) |
| Azure Spot discount | **Unchecked** (Spot VMs can be evicted during a demo) |
| Authentication | Password, username `rayen9` |
| Inbound ports | SSH (22), HTTP (80) |

3. **Review + create**. Once deployed, note the public IP (`4.223.163.106`).
4. VM → **Overview → DNS name → Configure** → label `epiconnect` → the site becomes `epiconnect.swedencentral.cloudapp.azure.com`.
5. Set the public IP to **Static** so it survives a VM stop/start.

## Part 2: Connect and update

```powershell
ssh rayen9@4.223.163.106
```

```bash
sudo apt update && sudo apt upgrade -y
sudo reboot
```

## Part 3: Install packages

```bash
sudo apt install -y python3 python3-venv python3-pip python3-dev git nginx \
    postgresql postgresql-contrib libpq-dev rsync curl
python3 --version     # must be ≥ 3.12 (Ubuntu 24.04 ships 3.12)
```

### PostgreSQL

```bash
sudo -u postgres psql <<'SQL'
CREATE DATABASE epiconnect_db;
CREATE USER epiconnect_user WITH PASSWORD 'CHANGE-ME';
ALTER ROLE epiconnect_user SET client_encoding TO 'utf8';
ALTER ROLE epiconnect_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE epiconnect_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE epiconnect_db TO epiconnect_user;
\c epiconnect_db
GRANT ALL ON SCHEMA public TO epiconnect_user;
SQL
```

## Part 4: Deploy the application

```bash
# Shared directory: owned by rayen9, group www-data (Nginx + Jenkins)
sudo mkdir -p /var/www/EPIConnect
sudo chown rayen9:www-data /var/www/EPIConnect
sudo chmod 2775 /var/www/EPIConnect            # setgid: new files keep group www-data

git clone https://github.com/rayenmabrouk/EPIConnect.git /var/www/EPIConnect
cd /var/www/EPIConnect
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements-dev.txt

cp .env.example .env
nano .env        # SECRET_KEY, DATABASE_URL password, HTTPS=False until Part 6
chmod 640 .env

venv/bin/python manage.py migrate
venv/bin/python manage.py collectstatic --noinput
venv/bin/python manage.py seed_perks
venv/bin/python manage.py createsuperuser
venv/bin/python manage.py check --deploy
```

Generate the secret key with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

## Part 5: Gunicorn (systemd) and Nginx

```bash
# Gunicorn
sudo cp deploy/systemd/gunicorn.service /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn
curl -s -H "Host: localhost" http://127.0.0.1:8000/healthz/     # {"status": "ok"}

# Nginx
sudo cp deploy/nginx/epiconnect.conf /etc/nginx/sites-available/epiconnect
sudo ln -sf /etc/nginx/sites-available/epiconnect /etc/nginx/sites-enabled/epiconnect
sudo rm -f /etc/nginx/sites-enabled/default
```

`epiconnect.conf` references the Let's Encrypt certificate. **Before the certificate exists**, comment out the `listen 443` server block and the `return 301` line, then:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## Part 6: HTTPS with Let's Encrypt

The NSG must allow 80 and 443 (see Part 7).

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d epiconnect.swedencentral.cloudapp.azure.com \
     --agree-tos -m rayenmabrouk9@gmail.com --redirect
sudo systemctl status certbot.timer         # auto-renewal twice a day
```

Restore the full `deploy/nginx/epiconnect.conf`, set `HTTPS=True` in `.env`, then:

```bash
sudo nginx -t && sudo systemctl reload nginx
sudo systemctl restart gunicorn
```

Check: https://securityheaders.com/?q=epiconnect.swedencentral.cloudapp.azure.com should give **grade A**.

## Part 7: Lock down the network (Terraform)

From your PC (with the Azure CLI and Terraform installed):

```powershell
az login
cd infra\terraform
copy terraform.tfvars.example terraform.tfvars   # set subscription_id and admin_ip (curl ifconfig.me)/32
# In import.tf, replace <SUBSCRIPTION_ID>
terraform init
terraform plan
terraform apply
```

Result: 80 and 443 are public; 22, 3000, 8080 and 9090 are reachable only from your IP (8080 also from GitHub's webhook ranges); 8000 is closed. In the portal, delete any leftover rules created by the wizard (`default-allow-ssh`, `allow-8000`).

> Your home IP changes? Update `admin_ip` and run `terraform apply` again. It takes seconds.

## Part 8: CI/CD and monitoring

- Jenkins: [CICD.md](CICD.md)
- Prometheus, node_exporter, Grafana: [MONITORING.md](MONITORING.md)

## Part 9: Backups

- **Azure Backup**: VM → Backup → enable the daily policy (whole-VM snapshots).
- **App-level backup** to Blob Storage: [`deploy/scripts/backup_db.sh`](../deploy/scripts/backup_db.sh) dumps PostgreSQL (`pg_dump -Fc`) and archives `media/`, then uploads both with `az storage blob upload`. Run it nightly from cron:

```bash
crontab -e
0 2 * * * STORAGE_ACCOUNT=<account> /var/www/EPIConnect/deploy/scripts/backup_db.sh >> /home/rayen9/backup.log 2>&1
```

## Part 10: Final verification

| Check | Expected |
|---|---|
| `https://epiconnect.swedencentral.cloudapp.azure.com` | Home page, padlock |
| `http://4.223.163.106` | 301 redirect to HTTPS |
| `/admin/` login | Works (no CSRF error) |
| Upload a profile picture | Visible (media served by Nginx) |
| `https://…/metrics` | 403 |
| `https://…/healthz/` | `{"status": "ok"}` |
| `systemctl status gunicorn nginx postgresql` | active (running) |
| securityheaders.com | A |
| `nmap -Pn 4.223.163.106` from outside | only 80, 443 |

## Useful commands

```bash
sudo journalctl -u gunicorn -f              # application logs
sudo tail -f /var/log/nginx/error.log       # proxy errors
sudo systemctl restart gunicorn             # after changing .env
cd /var/www/EPIConnect && venv/bin/python manage.py shell
sudo -u postgres psql epiconnect_db
```
