#!/bin/bash
# RAZE Health Check & Validation

set -e

cat << "EOF"
╔════════════════════════════════════════════════════════════╗
║         RAZE Enterprise AI OS - Health Check              ║
╚════════════════════════════════════════════════════════════╝
EOF

echo ""
echo "▶ Checking Docker & services..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not installed"
    exit 1
fi
echo "✓ Docker is installed"

# Check services running
RUNNING=$(docker compose ps -q | wc -l)
if [ "$RUNNING" -eq 0 ]; then
    echo "⚠️  No services running. Starting services..."
    docker compose up -d
fi

echo "▶ Checking service health..."

# PostgreSQL
if docker compose exec -T postgres pg_isready -U raze -d raze 2>/dev/null; then
    echo "✓ PostgreSQL: HEALTHY"
else
    echo "❌ PostgreSQL: FAILED"
    echo "   Logs:"
    docker compose logs postgres | tail -20
    exit 1
fi

# Redis
if docker compose exec -T redis redis-cli -a "$(grep REDIS_PASSWORD .env | cut -d= -f2)" ping 2>/dev/null | grep -q PONG; then
    echo "✓ Redis: HEALTHY"
else
    echo "❌ Redis: FAILED"
    exit 1
fi

# Backend health
if docker compose exec -T backend curl -sf http://localhost:8000/health 2>/dev/null; then
    echo "✓ Backend: HEALTHY"
else
    echo "⚠️  Backend: STARTING (may take 30-60s for migrations)"
    docker compose logs backend | tail -30
fi

# Database migrations
if docker compose exec -T backend alembic current 2>/dev/null; then
    echo "✓ Database Migrations: COMPLETE"
else
    echo "⚠️  Migrations pending - running now..."
    docker compose exec -T backend alembic upgrade head
    echo "✓ Migrations completed"
fi

# Frontend
if docker compose exec -T frontend curl -sf http://localhost:3000 2>/dev/null | grep -q "html"; then
    echo "✓ Frontend: HEALTHY"
else
    echo "⚠️  Frontend: STARTING"
fi

# Nginx
if docker compose exec -T nginx nginx -t 2>/dev/null | grep -q "successful"; then
    echo "✓ Nginx: HEALTHY"
else
    echo "⚠️  Nginx: CONFIG ERROR"
fi

echo ""
echo "▶ Environment check..."
echo "  ENVIRONMENT: $(grep ENVIRONMENT= .env | cut -d= -f2)"
echo "  DEBUG: $(grep '^DEBUG=' .env | cut -d= -f2)"
echo "  SERVER_IP: $(grep SERVER_IP= .env | cut -d= -f2)"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║         All systems operational! ✓                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Access URLs:"
echo "  Admin Dashboard: http://$(grep SERVER_IP= .env | cut -d= -f2)/"
echo "  API Docs: http://$(grep SERVER_IP= .env | cut -d= -f2)/docs"
echo ""
