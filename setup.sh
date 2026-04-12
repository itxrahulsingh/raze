#!/usr/bin/env bash
# =============================================================================
# RAZE Enterprise AI OS — Single-click setup script
# =============================================================================
# Usage: bash setup.sh
# Supports: Ubuntu 20.04+, Debian 11+, macOS 12+
# =============================================================================

set -euo pipefail

# ── Color helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

info()    { printf "${BLUE}[INFO]${NC}  %s\n" "$*"; }
success() { printf "${GREEN}[OK]${NC}    %s\n" "$*"; }
warn()    { printf "${YELLOW}[WARN]${NC}  %s\n" "$*"; }
error()   { printf "${RED}[ERROR]${NC} %s\n" "$*" >&2; }
fatal()   { error "$*"; exit 1; }
step()    { printf "\n${BOLD}${CYAN}══ %s ══${NC}\n" "$*"; }

# ── Script directory ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Banner ────────────────────────────────────────────────────────────────────
printf "\n"
printf "${BOLD}${CYAN}"
printf "  ██████╗  █████╗ ███████╗███████╗\n"
printf "  ██╔══██╗██╔══██╗╚══███╔╝██╔════╝\n"
printf "  ██████╔╝███████║  ███╔╝ █████╗  \n"
printf "  ██╔══██╗██╔══██║ ███╔╝  ██╔══╝  \n"
printf "  ██║  ██║██║  ██║███████╗███████╗\n"
printf "  ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝\n"
printf "${NC}"
printf "${BOLD}  Enterprise AI OS — Setup Script${NC}\n\n"

# ── OS detection ──────────────────────────────────────────────────────────────
step "Detecting operating system"

OS=""
ARCH="$(uname -m)"

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS="linux"
        DISTRO="${ID:-unknown}"
        info "Detected Linux: $PRETTY_NAME (${ARCH})"
    else
        fatal "Unsupported Linux distribution (no /etc/os-release)"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    DISTRO="macos"
    MACOS_VERSION="$(sw_vers -productVersion)"
    info "Detected macOS $MACOS_VERSION (${ARCH})"
else
    fatal "Unsupported OS: $OSTYPE. This script supports Linux and macOS."
fi

# ── Dependency check helpers ──────────────────────────────────────────────────
command_exists() { command -v "$1" &>/dev/null; }

require_root_or_sudo() {
    if [[ "$OS" == "linux" ]] && [[ $EUID -ne 0 ]] && ! command_exists sudo; then
        fatal "This script requires sudo on Linux. Install sudo or run as root."
    fi
}

run_sudo() {
    if [[ $EUID -eq 0 ]]; then
        "$@"
    else
        sudo "$@"
    fi
}

# ── Install Docker ────────────────────────────────────────────────────────────
step "Checking Docker installation"

install_docker_linux() {
    info "Installing Docker Engine..."
    require_root_or_sudo

    # Detect package manager
    if command_exists apt-get; then
        run_sudo apt-get update -qq
        run_sudo apt-get install -y -qq ca-certificates curl gnupg lsb-release

        run_sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/${DISTRO}/gpg | \
            run_sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        run_sudo chmod a+r /etc/apt/keyrings/docker.gpg

        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/${DISTRO} $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
            run_sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

        run_sudo apt-get update -qq
        run_sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io \
            docker-buildx-plugin docker-compose-plugin

    elif command_exists dnf; then
        run_sudo dnf -y install dnf-plugins-core
        run_sudo dnf config-manager --add-repo \
            https://download.docker.com/linux/centos/docker-ce.repo
        run_sudo dnf install -y docker-ce docker-ce-cli containerd.io \
            docker-buildx-plugin docker-compose-plugin

    elif command_exists yum; then
        run_sudo yum install -y yum-utils
        run_sudo yum-config-manager --add-repo \
            https://download.docker.com/linux/centos/docker-ce.repo
        run_sudo yum install -y docker-ce docker-ce-cli containerd.io \
            docker-buildx-plugin docker-compose-plugin

    else
        fatal "Unsupported package manager. Install Docker manually: https://docs.docker.com/engine/install/"
    fi

    run_sudo systemctl enable docker
    run_sudo systemctl start docker

    # Add current user to docker group
    if [[ $EUID -ne 0 ]]; then
        run_sudo usermod -aG docker "$USER"
        warn "Added $USER to docker group. You may need to log out and back in for this to take effect."
        warn "If docker commands fail, run: newgrp docker"
    fi

    success "Docker installed successfully"
}

install_docker_macos() {
    if command_exists brew; then
        info "Installing Docker Desktop via Homebrew..."
        brew install --cask docker
        info "Starting Docker Desktop..."
        open -a Docker
        info "Waiting for Docker daemon to start (up to 60s)..."
        local attempts=0
        until docker info &>/dev/null 2>&1; do
            sleep 3
            attempts=$((attempts + 1))
            if [[ $attempts -ge 20 ]]; then
                fatal "Docker daemon did not start in time. Open Docker Desktop manually and retry."
            fi
            printf "."
        done
        printf "\n"
        success "Docker Desktop is running"
    else
        fatal "Homebrew not found. Install it from https://brew.sh then re-run this script, or install Docker Desktop manually from https://www.docker.com/products/docker-desktop/"
    fi
}

if command_exists docker && docker info &>/dev/null 2>&1; then
    DOCKER_VERSION="$(docker --version | awk '{print $3}' | tr -d ',')"
    success "Docker $DOCKER_VERSION is already installed and running"
else
    warn "Docker not found or daemon not running"
    if [[ "$OS" == "linux" ]]; then
        install_docker_linux
    else
        install_docker_macos
    fi
fi

# ── Check Docker Compose v2 ───────────────────────────────────────────────────
step "Checking Docker Compose v2"

if docker compose version &>/dev/null 2>&1; then
    COMPOSE_VERSION="$(docker compose version --short)"
    success "Docker Compose v2 ($COMPOSE_VERSION) is available"
elif command_exists docker-compose; then
    # Old standalone v1 — install v2 plugin
    warn "Found legacy docker-compose v1. Installing Docker Compose v2 plugin..."

    if [[ "$OS" == "linux" ]]; then
        COMPOSE_V2_URL="https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)"
        COMPOSE_DEST="/usr/local/lib/docker/cli-plugins/docker-compose"
        run_sudo mkdir -p /usr/local/lib/docker/cli-plugins
        run_sudo curl -fsSL "$COMPOSE_V2_URL" -o "$COMPOSE_DEST"
        run_sudo chmod +x "$COMPOSE_DEST"
        success "Docker Compose v2 installed at $COMPOSE_DEST"
    else
        fatal "Please update Docker Desktop to get Compose v2, then re-run this script."
    fi
else
    fatal "Docker Compose not found. Install Docker (which includes Compose v2) and retry."
fi

# ── Verify openssl ────────────────────────────────────────────────────────────
step "Checking required tools"

if ! command_exists openssl; then
    if [[ "$OS" == "linux" ]]; then
        run_sudo apt-get install -y openssl 2>/dev/null || \
        run_sudo yum install -y openssl 2>/dev/null || \
        fatal "openssl not found. Install it with your package manager."
    else
        fatal "openssl not found. Install it with: brew install openssl"
    fi
fi
success "openssl is available"

# ── Create scripts/ dir and init-db.sql ──────────────────────────────────────
step "Creating required directories and files"

mkdir -p scripts nginx backups

if [ ! -f scripts/init-db.sql ]; then
    cat > scripts/init-db.sql <<'SQL'
-- RAZE database initialization
-- This file runs automatically when the postgres container is first created.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
SQL
    success "Created scripts/init-db.sql"
else
    success "scripts/init-db.sql already exists"
fi

# ── Generate secret values ─────────────────────────────────────────────────────
# ── Copy and populate .env ─────────────────────────────────────────────────────
step "Setting up environment file"

# Allow explicit regeneration when needed
FORCE_ENV="${FORCE_ENV:-0}"

if [ -f .env ] && [ "$FORCE_ENV" != "1" ]; then
    warn ".env already exists — keeping it (set FORCE_ENV=1 to regenerate)"
else
    step "Generating secure credentials"

    gen_secret() { openssl rand -hex "$1"; }

    JWT_SECRET="$(gen_secret 32)"
    SECRET_KEY="$(gen_secret 32)"
    CSRF_SECRET="$(gen_secret 32)"
    POSTGRES_PASSWORD="$(gen_secret 16)"
    REDIS_PASSWORD="$(gen_secret 16)"
    MINIO_ROOT_PASSWORD="$(gen_secret 16)"
    QDRANT_API_KEY="$(gen_secret 24)"

    success "Generated JWT secret key"
    success "Generated PostgreSQL password"
    success "Generated Redis password"
    success "Generated MinIO root password"
    success "Generated Qdrant API key"

    if [ -f .env ]; then
        warn ".env already exists — backing up to .env.bak"
        cp .env .env.bak
    fi

    cp .env.example .env

    # Detect server IP (prefer primary non-loopback interface)
    if [[ "$OS" == "linux" ]]; then
        SERVER_IP="$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' | head -1)"
    else
        SERVER_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "127.0.0.1")"
    fi
    SERVER_IP="${SERVER_IP:-127.0.0.1}"
    info "Detected server IP: $SERVER_IP"

    # Helper to replace a value in .env (works on both Linux and macOS sed)
    set_env() {
        local key="$1"
        local value="$2"
        if [[ "$OS" == "macos" ]]; then
            sed -i '' "s|^${key}=.*|${key}=${value}|" .env
        else
            sed -i "s|^${key}=.*|${key}=${value}|" .env
        fi
    }

    set_env "SERVER_IP"             "$SERVER_IP"
    set_env "JWT_SECRET_KEY"        "$JWT_SECRET"
    set_env "SECRET_KEY"            "$SECRET_KEY"
    set_env "CSRF_SECRET"           "$CSRF_SECRET"
    set_env "POSTGRES_PASSWORD"     "$POSTGRES_PASSWORD"
    set_env "REDIS_PASSWORD"        "$REDIS_PASSWORD"
    set_env "MINIO_ROOT_PASSWORD"   "$MINIO_ROOT_PASSWORD"
    set_env "QDRANT_API_KEY"        "$QDRANT_API_KEY"

    # Update composite URLs that embed the generated passwords
    set_env "DATABASE_URL" "postgresql+asyncpg://raze:${POSTGRES_PASSWORD}@postgres:5432/raze"
    set_env "REDIS_URL"    "redis://:${REDIS_PASSWORD}@redis:6379/0"
    set_env "CELERY_BROKER_URL"  "redis://:${REDIS_PASSWORD}@redis:6379/1"
    set_env "CELERY_RESULT_BACKEND" "redis://:${REDIS_PASSWORD}@redis:6379/2"
    set_env "NEXT_PUBLIC_API_URL"  "http://${SERVER_IP}/api"
    set_env "NEXT_PUBLIC_WS_URL"   "ws://${SERVER_IP}/ws"
    set_env "MINIO_EXTERNAL_URL"   "http://${SERVER_IP}:9000"
    set_env "CORS_ORIGINS"         "http://${SERVER_IP},http://${SERVER_IP}:3000,http://localhost,http://localhost:3000"
    set_env "ALLOWED_HOSTS"        "${SERVER_IP},localhost,127.0.0.1"

    success ".env configured with generated credentials and server IP ($SERVER_IP)"
fi

# Load required values from .env without sourcing (handles spaces safely)
get_env() {
    local key="$1"
    if [ -f .env ]; then
        grep -E "^${key}=" .env | head -1 | cut -d= -f2-
    fi
}

POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(get_env POSTGRES_PASSWORD)}"
REDIS_PASSWORD="${REDIS_PASSWORD:-$(get_env REDIS_PASSWORD)}"

# ── Pull images ───────────────────────────────────────────────────────────────
step "Pulling Docker base images"
docker compose pull postgres redis minio qdrant nginx || \
    warn "Some images could not be pulled. Will use cached versions."

# ── Build application images ──────────────────────────────────────────────────
step "Building application images"
if [ -d backend ] && [ -f backend/Dockerfile ]; then
    info "Building backend image..."
    docker compose build backend
    success "Backend image built"
else
    warn "backend/Dockerfile not found — skipping backend build (add it before starting services)"
fi

if [ -d frontend ] && [ -f frontend/Dockerfile ]; then
    info "Building frontend image..."
    docker compose build frontend
    success "Frontend image built"
else
    warn "frontend/Dockerfile not found — skipping frontend build (add it before starting services)"
fi

# ── Start infrastructure services ─────────────────────────────────────────────
step "Starting infrastructure services"

info "Starting postgres, redis, minio, qdrant..."
docker compose up -d postgres redis minio qdrant

# ── Wait for PostgreSQL ───────────────────────────────────────────────────────
step "Waiting for PostgreSQL to be healthy"

MAX_WAIT=120
ELAPSED=0
INTERVAL=5

until docker compose exec -T postgres \
    pg_isready -U raze -d raze -q 2>/dev/null; do
    if [[ $ELAPSED -ge $MAX_WAIT ]]; then
        fatal "PostgreSQL did not become healthy within ${MAX_WAIT}s. Check: docker compose logs postgres"
    fi
    info "Waiting for postgres... (${ELAPSED}s elapsed)"
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

success "PostgreSQL is healthy"

# ── Wait for Redis ────────────────────────────────────────────────────────────
step "Waiting for Redis to be healthy"

ELAPSED=0
until docker compose exec -T redis redis-cli -a "$REDIS_PASSWORD" ping 2>/dev/null | grep -q PONG; do
    if [[ $ELAPSED -ge 60 ]]; then
        fatal "Redis did not become healthy within 60s. Check: docker compose logs redis"
    fi
    info "Waiting for redis... (${ELAPSED}s elapsed)"
    sleep 3
    ELAPSED=$((ELAPSED + 3))
done

success "Redis is healthy"

# ── Run Alembic migrations ─────────────────────────────────────────────────────
step "Running database migrations"

if [ -d backend ] && [ -f backend/Dockerfile ]; then
    # Ensure backend is up for migrations
    docker compose up -d backend

    ELAPSED=0
    until docker compose exec -T backend curl -sf http://localhost:8000/health &>/dev/null; do
        if [[ $ELAPSED -ge 120 ]]; then
            warn "Backend did not become healthy within 120s. Attempting migrations anyway..."
            break
        fi
        info "Waiting for backend to start... (${ELAPSED}s elapsed)"
        sleep 5
        ELAPSED=$((ELAPSED + 5))
    done

    if docker compose exec -T backend alembic upgrade head 2>/dev/null; then
        success "Database migrations applied"
    else
        warn "Alembic migration failed or alembic not configured yet. Run 'make migrate' after setting up alembic."
    fi
else
    warn "Backend not built yet — skipping migrations. Run 'make migrate' after backend is ready."
fi

# ── Start all remaining services ──────────────────────────────────────────────
step "Starting all services"
docker compose up -d --remove-orphans
success "All services started"

# ── Print status ──────────────────────────────────────────────────────────────
step "Service status"
docker compose ps

# ── Success banner ────────────────────────────────────────────────────────────
printf "\n"
printf "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════╗${NC}\n"
printf "${GREEN}${BOLD}║         RAZE Enterprise AI OS is up and running!         ║${NC}\n"
printf "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════╝${NC}\n\n"

printf "${BOLD}  Access URLs:${NC}\n"
printf "  ${CYAN}●${NC} Frontend (Admin UI)  : ${BOLD}http://${SERVER_IP}/${NC}\n"
printf "  ${CYAN}●${NC} Backend API          : ${BOLD}http://${SERVER_IP}/api/${NC}\n"
printf "  ${CYAN}●${NC} API Docs (Swagger)   : ${BOLD}http://${SERVER_IP}/docs${NC}\n"
printf "  ${CYAN}●${NC} MinIO Console        : ${BOLD}http://${SERVER_IP}:9001/${NC}\n"
printf "  ${CYAN}●${NC} Qdrant Dashboard     : ${BOLD}http://${SERVER_IP}:6333/dashboard${NC}\n"

printf "\n${BOLD}  MinIO Credentials:${NC}\n"
printf "  User     : ${BOLD}raze_admin${NC}\n"
printf "  Password : ${BOLD}${MINIO_ROOT_PASSWORD}${NC}\n"

printf "\n${BOLD}  Useful commands:${NC}\n"
printf "  ${CYAN}make logs${NC}           — tail all service logs\n"
printf "  ${CYAN}make shell-backend${NC}  — open backend shell\n"
printf "  ${CYAN}make shell-db${NC}       — open psql shell\n"
printf "  ${CYAN}make backup${NC}         — dump database\n"
printf "  ${CYAN}make down${NC}           — stop all services\n"
printf "\n${YELLOW}  All credentials are saved in .env (keep it secret!)${NC}\n\n"
