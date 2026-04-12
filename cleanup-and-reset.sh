#!/bin/bash
# =============================================================================
# RAZE - Complete Cleanup & Reset Script
# WARNING: This DELETES everything - containers, volumes, images, networks
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
BOLD='\033[1m'
NC='\033[0m'

info()    { printf "${BLUE}[INFO]${NC}  %s\n" "$*"; }
success() { printf "${GREEN}[OK]${NC}    %s\n" "$*"; }
warn()    { printf "${YELLOW}[WARN]${NC}  %s\n" "$*"; }
error()   { printf "${RED}[ERROR]${NC} %s\n" "$*" >&2; }
step()    { printf "\n${BOLD}${BLUE}══ %s ══${NC}\n" "$*"; }

# Banner
printf "\n${RED}${BOLD}"
printf "╔══════════════════════════════════════════════════════════════╗\n"
printf "║   RAZE Complete Cleanup - WARNING: DESTRUCTIVE OPERATION    ║\n"
printf "║                                                              ║\n"
printf "║   This will DELETE:                                         ║\n"
printf "║   ✗ All Docker containers (postgres, redis, backend, etc)   ║\n"
printf "║   ✗ All volumes (databases, caches, file storage)          ║\n"
printf "║   ✗ All images built for RAZE                              ║\n"
printf "║   ✗ All networks                                            ║\n"
printf "║   ✗ .env file (will be regenerated)                        ║\n"
printf "║   ✗ Previous .env.bak backup                               ║\n"
printf "╚══════════════════════════════════════════════════════════════╝${NC}\n\n"

# Confirmation
warn "THIS OPERATION CANNOT BE UNDONE!"
printf "${BOLD}Type 'DELETE EVERYTHING' to confirm: ${NC}"
read -r CONFIRMATION

if [ "$CONFIRMATION" != "DELETE EVERYTHING" ]; then
    echo "❌ Cancelled. No changes made."
    exit 0
fi

printf "\n${YELLOW}You have 10 seconds to cancel (Ctrl+C)...${NC}\n"
sleep 10

# ─── Start Cleanup ───────────────────────────────────────────────────────────

step "Stopping all containers"

if docker ps -q | grep -q .; then
    docker compose down 2>/dev/null || true
    docker stop $(docker ps -aq) 2>/dev/null || true
    sleep 5
    success "Containers stopped"
else
    info "No containers running"
fi

# ─── Remove RAZE volumes ─────────────────────────────────────────────────────

step "Removing RAZE volumes"

VOLUMES=$(docker volume ls -q | grep -E "raze_|^postgres_data|^redis_data|^minio_data|^qdrant_data|^backend_cache|^nginx_logs" || true)

if [ -n "$VOLUMES" ]; then
    echo "$VOLUMES" | while read -r vol; do
        docker volume rm "$vol" 2>/dev/null && info "Removed volume: $vol" || warn "Failed to remove: $vol"
    done
    success "All RAZE volumes removed"
else
    info "No RAZE volumes found"
fi

# ─── Remove RAZE images ──────────────────────────────────────────────────────

step "Removing RAZE images"

IMAGES=$(docker images | grep -E "raze_|postgres|redis|minio|qdrant" | awk '{print $3}' || true)

if [ -n "$IMAGES" ]; then
    echo "$IMAGES" | sort -u | while read -r img; do
        if [ -n "$img" ] && [ "$img" != "IMAGE" ]; then
            docker rmi -f "$img" 2>/dev/null && info "Removed image: $img" || warn "Failed to remove image: $img"
        fi
    done
    success "RAZE images removed"
else
    info "No RAZE images found"
fi

# ─── Remove RAZE network ─────────────────────────────────────────────────────

step "Removing RAZE network"

if docker network ls -q | grep -q "raze_internal"; then
    docker network rm raze_internal 2>/dev/null && success "Network removed" || warn "Failed to remove network"
else
    info "Network already removed"
fi

# ─── Backup and remove .env ──────────────────────────────────────────────────

step "Backing up current .env"

if [ -f .env ]; then
    TIMESTAMP=$(date +%s)
    cp .env ".env.backup-${TIMESTAMP}"
    info "Backed up to .env.backup-${TIMESTAMP}"
    rm -f .env .env.bak
    success ".env files removed"
else
    info "No .env file to remove"
fi

# ─── Clean up Docker system ──────────────────────────────────────────────────

step "Cleaning up unused Docker resources"

docker system prune -f --volumes 2>/dev/null || true

success "System prune complete"

# ─── Verify cleanup ──────────────────────────────────────────────────────────

step "Verifying cleanup"

REMAINING_CONTAINERS=$(docker ps -aq | wc -l)
REMAINING_VOLUMES=$(docker volume ls -q | grep -c raze || echo 0)
REMAINING_NETWORKS=$(docker network ls | grep -c raze_internal || echo 0)

if [ "$REMAINING_CONTAINERS" -eq 0 ] && [ "$REMAINING_VOLUMES" -eq 0 ] && [ "$REMAINING_NETWORKS" -eq 0 ]; then
    success "All RAZE resources cleaned up"
else
    warn "Some resources may still exist - continuing anyway..."
fi

# ─── Summary ──────────────────────────────────────────────────────────────────

printf "\n${GREEN}${BOLD}"
printf "╔══════════════════════════════════════════════════════════════╗\n"
printf "║              ✓ COMPLETE CLEANUP FINISHED                    ║\n"
printf "╚══════════════════════════════════════════════════════════════╝${NC}\n\n"

printf "${BOLD}Next steps - Fresh start:${NC}\n\n"
printf "  ${BLUE}1.${NC} Run fresh setup:\n"
printf "     ${BOLD}bash setup.sh${NC}\n\n"
printf "  ${BLUE}2.${NC} Wait for all services to start (5-10 minutes)\n\n"
printf "  ${BLUE}3.${NC} Verify deployment:\n"
printf "     ${BOLD}docker compose ps${NC}\n\n"
printf "  ${BLUE}4.${NC} Check health:\n"
printf "     ${BOLD}curl http://localhost/health${NC}\n\n"

printf "${YELLOW}⚠️  All data is gone - this is a fresh database${NC}\n\n"
