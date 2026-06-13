#!/bin/bash
# =============================================================
# ClientFinder — Restore Script
# =============================================================
# Usage: ./scripts/restore.sh <backup-file>
# =============================================================

set -euo pipefail

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <backup-file>"
    echo "Example: $0 backups/db_20240101_020000.sql.gz.gpg"
    exit 1
fi

BACKUP_FILE="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Load env
if [ -f .env ]; then
    set -a; source .env; set +a
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "✗ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "⚠  This will OVERWRITE the current database."
echo "   Press Ctrl-C within 5 seconds to abort..."
sleep 5

# Decrypt if needed
if [[ "$BACKUP_FILE" == *.gpg ]]; then
    PASSPHRASE="${BACKUP_PASSPHRASE:-}"
    if [ -z "$PASSPHRASE" ]; then
        echo -n "Enter backup passphrase: "
        read -rs PASSPHRASE
    fi
    DECRYPTED_FILE="${BACKUP_FILE%.gpg}"
    gpg --batch --yes --passphrase "$PASSPHRASE" \
        --decrypt -o "$DECRYPTED_FILE" "$BACKUP_FILE"
    TARGET_FILE="$DECRYPTED_FILE"
else
    TARGET_FILE="$BACKUP_FILE"
fi

# Decompress
if [[ "$TARGET_FILE" == *.gz ]]; then
    DECOMPRESSED_FILE="${TARGET_FILE%.gz}"
    gunzip -c "$TARGET_FILE" > "$DECOMPRESSED_FILE"
    SQL_FILE="$DECOMPRESSED_FILE"
else
    SQL_FILE="$TARGET_FILE"
fi

# Restore
echo "Restoring database from $BACKUP_FILE..."
gunzip -c "$SQL_FILE" | docker compose exec -T postgres psql \
    -U "${POSTGRES_USER:-clientfinder}" \
    -d "${POSTGRES_DB:-clientfinder}"

# Cleanup
rm -f "$DECRYPTED_FILE" "$DECOMPRESSED_FILE" 2>/dev/null || true

echo "✓ Restore complete"
