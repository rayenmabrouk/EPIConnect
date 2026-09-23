#!/bin/bash
# Nightly PostgreSQL + media backup to Azure Blob Storage.
# Cron (as rayen9):  0 2 * * * /var/www/EPIConnect/deploy/scripts/backup_db.sh >> /var/log/epiconnect-backup.log 2>&1
#
# Requires: Azure CLI (az) logged in with a managed identity or `az login`,
#           and a storage account + container, set below or in the environment.
set -euo pipefail

STORAGE_ACCOUNT="${STORAGE_ACCOUNT:?set STORAGE_ACCOUNT}"
CONTAINER="${CONTAINER:-backups}"
DB_NAME="${DB_NAME:-epiconnect_db}"
APP_DIR="${APP_DIR:-/var/www/EPIConnect}"
STAMP="$(date +%Y%m%d-%H%M%S)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "[$STAMP] Dumping $DB_NAME..."
sudo -u postgres pg_dump -Fc "$DB_NAME" > "$TMP/db-$STAMP.dump"

echo "[$STAMP] Archiving media..."
tar -czf "$TMP/media-$STAMP.tar.gz" -C "$APP_DIR" media

for f in "$TMP"/*; do
    az storage blob upload --auth-mode login --only-show-errors \
        --account-name "$STORAGE_ACCOUNT" --container-name "$CONTAINER" \
        --file "$f" --name "$(basename "$f")"
done
echo "[$STAMP] Backup uploaded to $STORAGE_ACCOUNT/$CONTAINER"
