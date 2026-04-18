#!/bin/bash
# Database backup script

set -euo pipefail

BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_FILE="${BACKUP_DIR}/raze_${TIMESTAMP}.sql.gz"

GREEN='\033[0;32m'
BOLD='\033[1m'
NC='\033[0m'

mkdir -p "$BACKUP_DIR"

echo -e "${BOLD}Creating database backup...${NC}"
echo "  File: $BACKUP_FILE"

# PostgreSQL backup
docker compose exec -T postgres pg_dump -U raze -d raze | gzip > "$BACKUP_FILE"

# Get file size
SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

echo -e "${GREEN}✓ Backup complete${NC}"
echo "  Size: $SIZE"
echo "  Location: $BACKUP_FILE"

# Keep only last 7 backups
echo -e "\n${BOLD}Cleaning up old backups (keeping last 7)...${NC}"
ls -t "$BACKUP_DIR"/raze_*.sql.gz 2>/dev/null | tail -n +8 | while read -r file; do
    rm "$file"
    echo "  Removed: $(basename "$file")"
done

echo -e "\n${GREEN}Done!${NC}"
