# Backup & Restore

## Manual Backup

```bash
make backup
```

Atau langsung:
```bash
./scripts/backup.sh
```

Backup file: `./backups/db_YYYYMMDD_HHMMSS.sql.gz.gpg`

## Restore

```bash
make restore file=backups/db_20240101_020000.sql.gz.gpg
```

## Automatic Backup (Production)

Tambahkan ke crontab:
```bash
0 2 * * * /home/kumaha-sia/clientfinder/scripts/backup.sh >> /var/log/cf-backup.log 2>&1
```

## Offsite Sync (Optional)

Edit `BACKUP_REMOTE_TARGET` di `.env`:
- rclone ke Google Drive
- rclone ke S3
- rclone ke B2

## Retention

Default 30 hari. Edit `BACKUP_RETENTION_DAYS` di `.env`.
