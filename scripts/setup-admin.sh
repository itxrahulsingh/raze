#!/bin/bash
# Setup initial admin user and configuration

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[1;34m'
BOLD='\033[1m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "\n${BOLD}${CYAN}RAZE Admin Setup${NC}\n"

# Check if postgres is running
if ! docker compose ps | grep -q "postgres.*Up"; then
    echo "❌ PostgreSQL not running. Start services first: docker compose up -d postgres"
    exit 1
fi

# Bcrypt hash of 'ChangeMe123!'
HASH='$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQyCi1O7EUmg7BM.s9nOGIEU.'

echo -e "${BOLD}Creating default superadmin user...${NC}\n"

docker compose exec -T postgres psql -U raze -d raze <<SQL
INSERT INTO public.users (
  id, email, username, hashed_password, full_name, role, is_active, is_verified, user_metadata
) VALUES (
  gen_random_uuid(),
  'admin@yourcompany.com',
  'admin',
  '$HASH',
  'System Administrator',
  'superadmin',
  true,
  true,
  '{}'::jsonb
)
ON CONFLICT (email) DO UPDATE SET
  username = EXCLUDED.username,
  hashed_password = EXCLUDED.hashed_password,
  role = EXCLUDED.role,
  is_active = EXCLUDED.is_active,
  is_verified = EXCLUDED.is_verified;
SQL

echo -e "${GREEN}✓ Admin user created${NC}\n"

# Create default AI config
echo -e "${BOLD}Setting up default AI configuration...${NC}\n"

docker compose exec -T postgres psql -U raze -d raze <<SQL
INSERT INTO public.ai_configs (
  id, name, description, model, provider, is_default, max_tokens, temperature, is_active
) VALUES (
  gen_random_uuid(),
  'Default GPT-4 Config',
  'Production-grade GPT-4 configuration',
  'gpt-4-turbo',
  'openai',
  true,
  2000,
  0.7,
  true
)
ON CONFLICT DO NOTHING;

INSERT INTO public.ai_configs (
  id, name, description, model, provider, is_default, max_tokens, temperature, is_active
) VALUES (
  gen_random_uuid(),
  'Budget OpenAI Config',
  'Cost-optimized GPT-3.5 Turbo',
  'gpt-3.5-turbo',
  'openai',
  false,
  1000,
  0.7,
  true
)
ON CONFLICT DO NOTHING;
SQL

echo -e "${GREEN}✓ AI configurations created${NC}\n"

# Display credentials
echo -e "${BOLD}${CYAN}═════════════════════════════════════════════════${NC}"
echo -e "${BOLD}Admin Access Credentials:${NC}\n"
echo -e "  ${CYAN}Email:${NC}    admin@yourcompany.com"
echo -e "  ${CYAN}Password:${NC}  ChangeMe123!"
echo -e "\n${BOLD}${CYAN}═════════════════════════════════════════════════${NC}\n"

echo -e "📝  ${BOLD}Next steps:${NC}\n"
echo "  1. Access admin dashboard: http://<SERVER_IP>/admin"
echo "  2. Login with credentials above"
echo "  3. Change password immediately (Account Settings)"
echo "  4. Configure your OpenAI/Anthropic API keys"
echo "  5. Upload knowledge documents"
echo -e "\n${GREEN}Setup complete!${NC}\n"
