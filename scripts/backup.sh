#!/bin/bash
# =============================================================
# ClientFinder — Backup Script
# =============================================================
# Creates encrypted database + files backup
# Usage: ./scripts/backup.sh
# Cron:  0 2 * * * /path/to/backup.sh >> /var/log/cf-backup.log 2>&1
# =============================================================

set -euo pipefail

# Load env
if [ -f .env ]; then
    # shellcheck disable=SC1091
    set -a; source .env; set +a
fi

# Config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
DATE="$(date +%Y%m%d_%H%M%S)"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
PASSPHRASE="${BACKUP_PASSPHRASE:-}"

mkdir -p "$BACKUP_DIR"

# ----- Database backup -----
echo "[$(date)] Backing up database..."
DB_DUMP_FILE="$BACKUP_DIR/db_$DATE.sql.gz"
docker compose exec -T postgres pg_dump \
    -U "${POSTGRES_USER:-clientfinder}" \
    -d "${POSTGRES_DB:-clientfinder}" \
    --no-owner --no-acl \
    | gzip > "$DB_DUMP_FILE"

# Encrypt
if [ -n "$PASSPHRASE" ]; then
    gpg --batch --yes --symmetric \
        --passphrase "$PASSPHRASE" \
        --cipher-algo AES256 \
        -o "$DB_DUMP_FILE.gpg" \
        "$DB_DUMP_FILE"
    rm -f "$DB_DUMP_FILE"
    DB_FINAL="$DB_DUMP_FILE.gpg"
else
    DB_FINAL="$DB_DUMP_FILE"
fi

echo "[$(date)] ✓ Database backup: $DB_FINAL ($(du -h "$DB_FINAL" | cut -f1))"

# ----- MinIO backup (only if enabled) -----
if [ "${BACKUP_MINIO:-false}" = "true" ]; then
    echo "[$(date)] Backing up MinIO buckets..."
    MINIO_DUMP_DIR="$BACKUP_DIR/files_$DATE"
    mkdir -p "$MINIO_DUMP_DIR"
    # Requires mc configured; see ops/minio/setup-mc.sh
    docker run --rm -v "$MINIO_DUMP_DIR:/backup" \
        --network cf-net \
        minio/mc:latest \
        mirror minio/clientfinder /backup || echo "MinIO backup failed (check mc config)"
    echo "[$(date)] ✓ Files backup: $MINIO_DUMP_DIR"
fi

# ----- Retention cleanup -----
echo "[$(date)] Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -type f -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -type d -empty -delete

# ----- Remote sync (optional) -----
if [ -n "${BACKUP_REMOTE_TARGET:-}" ]; then
    echo "[$(date)] Syncing to remote: $BACKUP_REMOTE_TARGET"
    rclone sync "$BACKUP_DIR" "$BACKUP_REMOTE_TARGET" || echo "rclone sync failed"
fi

echo "[$(date)] ✓ Backup complete"
