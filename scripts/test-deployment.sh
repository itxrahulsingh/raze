#!/bin/bash
# Comprehensive deployment test script

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

PASSED=0
FAILED=0

test_result() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $1"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗${NC} $1"
        FAILED=$((FAILED + 1))
    fi
}

echo -e "\n${BOLD}${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}  RAZE Deployment Test Suite${NC}"
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════${NC}\n"

# Docker
echo -e "${BOLD}Testing Docker & Services:${NC}"
docker info > /dev/null 2>&1
test_result "Docker daemon running"

docker compose ps > /dev/null 2>&1
test_result "Docker Compose available"

# Containers
echo -e "\n${BOLD}Testing Containers:${NC}"
docker compose exec -T postgres pg_isready -U raze -d raze > /dev/null 2>&1
test_result "PostgreSQL healthy"

docker compose exec -T redis redis-cli ping > /dev/null 2>&1
test_result "Redis responsive"

curl -sf http://localhost:6333/health > /dev/null 2>&1
test_result "Qdrant vector database"

# Backend API
echo -e "\n${BOLD}Testing Backend API:${NC}"
curl -sf http://localhost/health > /dev/null 2>&1
test_result "Backend health endpoint"

curl -sf http://localhost/api/v1/health > /dev/null 2>&1
test_result "Backend v1 health endpoint"

curl -sf http://localhost/docs > /dev/null 2>&1
test_result "API documentation (Swagger)"

# Frontend
echo -e "\n${BOLD}Testing Frontend:${NC}"
curl -sf http://localhost:3000 | grep -q "html" > /dev/null 2>&1
test_result "Frontend accessible"

# Nginx
echo -e "\n${BOLD}Testing Reverse Proxy (Nginx):${NC}"
docker compose exec -T nginx nginx -t 2>&1 | grep -q "successful" > /dev/null 2>&1
test_result "Nginx configuration valid"

curl -sI http://localhost/ | grep -q "200\|301\|302" > /dev/null 2>&1
test_result "Nginx routing to frontend"

curl -sI http://localhost/api/v1/health | grep -q "200" > /dev/null 2>&1
test_result "Nginx routing to backend"

# Database
echo -e "\n${BOLD}Testing Database:${NC}"
docker compose exec -T postgres psql -U raze -d raze -c "SELECT COUNT(*) FROM users;" > /dev/null 2>&1
test_result "Users table exists and readable"

docker compose exec -T postgres psql -U raze -d raze -c "SELECT COUNT(*) FROM conversations;" > /dev/null 2>&1
test_result "Conversations table accessible"

# Migrations
echo -e "\n${BOLD}Testing Database Migrations:${NC}"
docker compose exec -T backend alembic current > /dev/null 2>&1
test_result "Alembic migrations current"

# Environment
echo -e "\n${BOLD}Testing Configuration:${NC}"
[ -f .env ] && test_result ".env file exists" || test_result ".env file exists"
grep -q "JWT_SECRET_KEY" .env
test_result "JWT_SECRET_KEY configured"

grep -q "POSTGRES_PASSWORD" .env
test_result "POSTGRES_PASSWORD configured"

grep -q "OPENAI_API_KEY" .env
test_result "OPENAI_API_KEY configured"

# Summary
echo -e "\n${BOLD}${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}Test Summary:${NC}"
echo -e "  ${GREEN}Passed: ${PASSED}${NC}"
echo -e "  ${RED}Failed: ${FAILED}${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}${BOLD}✓ All tests passed! Deployment is ready.${NC}\n"
    exit 0
else
    echo -e "\n${YELLOW}${BOLD}⚠ Some tests failed. Check logs:${NC}"
    echo -e "  docker compose logs\n"
    exit 1
fi
