#!/bin/bash
# Generate secure secrets for .env configuration

set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "\n${BOLD}${CYAN}RAZE Secret Generator${NC}\n"

gen_secret() {
    openssl rand -hex "$1" 2>/dev/null || openssl rand "$1" | base64 | head -c "$1"
}

echo -e "${BOLD}Generated Secrets (copy to .env):${NC}\n"

echo "JWT_SECRET_KEY=$(gen_secret 32)"
echo "SECRET_KEY=$(gen_secret 32)"
echo "CSRF_SECRET=$(gen_secret 32)"
echo "POSTGRES_PASSWORD=$(gen_secret 16)"
echo "REDIS_PASSWORD=$(gen_secret 16)"
echo "MINIO_ROOT_PASSWORD=$(gen_secret 16)"
echo "QDRANT_API_KEY=$(gen_secret 24)"

echo -e "\n${GREEN}✓ Secrets generated${NC}\n"
