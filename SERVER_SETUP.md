# RAZE Enterprise AI OS — Production Deployment Guide

**Version:** 1.0.0  
**Last Updated:** April 2026  
**Tested On:** Ubuntu 22.04 LTS, Ubuntu 24.04 LTS, macOS 13+

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Quick Start (5 minutes)](#quick-start-5-minutes)
4. [Manual Deployment](#manual-deployment)
5. [Admin Panel Setup](#admin-panel-setup)
6. [Chat SDK Integration](#chat-sdk-integration)
7. [Testing & Verification](#testing--verification)
8. [Production Configuration](#production-configuration)
9. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum
- **CPU:** 4 vCPU (8+ recommended for production)
- **RAM:** 8 GB (16 GB recommended)
- **Storage:** 50 GB SSD (100+ GB for production)
- **Network:** 100 Mbps stable connection

### Software
- **Docker:** 20.10+ with Compose plugin v2+
- **OS:** Ubuntu 20.04+, Debian 11+, or macOS 12+
- **Git:** For cloning the repository

### API Keys Required
- **OpenAI:** (for GPT-4, GPT-4 Turbo)
- **Anthropic:** Optional (for Claude models)
- **Gemini:** Optional (for Gemini models)
- **Grok/X API:** Optional
- **MinIO:** Built-in, auto-configured

---

## Pre-Deployment Checklist

- [ ] Server has 4+ vCPU, 8+ GB RAM
- [ ] Docker and Docker Compose v2 installed
- [ ] OpenAI API key obtained
- [ ] Domain/IP address ready for deployment
- [ ] Network ports 80, 443 accessible
- [ ] Git cloned repository to `/opt/raze`
- [ ] Generated strong passwords ready (.env file)

---

## Quick Start (5 minutes)

### 1. Clone Repository

```bash
git clone <your-repo-url> /opt/raze
cd /opt/raze
chmod +x setup.sh
```

### 2. Run Automated Setup

```bash
bash setup.sh
```

This script automatically:
- ✅ Checks/installs Docker
- ✅ Generates secure credentials
- ✅ Creates `.env` from template
- ✅ Builds Docker images
- ✅ Starts all services
- ✅ Runs database migrations
- ✅ Creates default admin user

### 3. Access the System

Once setup completes, you'll see:

```
╔══════════════════════════════════════════════════════════════╗
║         RAZE Enterprise AI OS is up and running!            ║
╚══════════════════════════════════════════════════════════════╝

Access URLs:
  ● Admin Dashboard:   http://<SERVER_IP>/
  ● API Documentation: http://<SERVER_IP>/docs
  ● MinIO Console:     http://<SERVER_IP>:9001/
  ● Qdrant Dashboard:  http://<SERVER_IP>:6333/dashboard

MinIO Credentials:
  User     : raze_admin
  Password : [shown in output]
```

**Login to Admin Dashboard:**
- **Email:** admin@yourcompany.com
- **Password:** ChangeMe123! (change immediately!)

---

## Manual Deployment

If automated setup fails or you prefer manual control:

### Step 1: System Preparation

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

### Step 2: Clone & Configure

```bash
git clone <your-repo-url> /opt/raze
cd /opt/raze

# Copy template
cp .env.example .env

# Edit with your values
nano .env  # or use your preferred editor
```

**Essential `.env` variables:**

```bash
# Server Configuration
SERVER_IP=192.168.1.100  # Your server's public IP
ENVIRONMENT=production
DEBUG=false

# Database
POSTGRES_PASSWORD=<generate-strong-password>
DATABASE_URL=postgresql+asyncpg://raze:${POSTGRES_PASSWORD}@postgres:5432/raze

# Redis
REDIS_PASSWORD=<generate-strong-password>
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# JWT & Security
JWT_SECRET_KEY=<generate-64-char-hex>

# MinIO / S3
STORAGE_BACKEND=local  # or "minio"
MINIO_ROOT_USER=raze_admin
MINIO_ROOT_PASSWORD=<generate-strong-password>
MINIO_BUCKET_DOCUMENTS=raze-documents

# Vector Database
QDRANT_API_KEY=<generate-24-char-hex>

# LLM Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo
ANTHROPIC_API_KEY=sk-ant-...  # Optional
ANTHROPIC_MODEL=claude-3-opus-20240229

# Frontend
NEXT_PUBLIC_API_URL=http://${SERVER_IP}/api
NEXT_PUBLIC_WS_URL=ws://${SERVER_IP}/ws
ALLOWED_ORIGINS=http://${SERVER_IP},http://${SERVER_IP}:3000
```

### Step 3: Generate Secrets

```bash
# Run this to generate secure values
bash scripts/generate-secrets.sh

# Or manually:
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)"
echo "POSTGRES_PASSWORD=$(openssl rand -hex 16)"
echo "REDIS_PASSWORD=$(openssl rand -hex 16)"
echo "MINIO_ROOT_PASSWORD=$(openssl rand -hex 16)"
echo "QDRANT_API_KEY=$(openssl rand -hex 24)"
```

### Step 4: Start Services

```bash
# Build images
docker compose build

# Start all services
docker compose up -d

# Watch logs
docker compose logs -f
```

### Step 5: Run Migrations

```bash
# Wait for backend to be healthy (30-60s)
docker compose exec backend alembic upgrade head

# Verify
docker compose ps
```

### Step 6: Create Admin User

```bash
docker compose exec postgres psql -U raze -d raze <<'SQL'
INSERT INTO public.users (
  id, email, username, hashed_password, full_name, role, is_active, is_verified, user_metadata
) VALUES (
  gen_random_uuid(),
  'admin@yourcompany.com',
  'admin',
  -- bcrypt hash of 'ChangeMe123!'
  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQyCi1O7EUmg7BM.s9nOGIEU.',
  'System Administrator',
  'superadmin',
  true,
  true,
  '{}'::jsonb
);
SQL
```

---

## Admin Panel Setup

### First Login

1. Open **http://your-server-ip/**
2. Login with email: `admin@yourcompany.com`, password: `ChangeMe123!`
3. **IMMEDIATELY change your password** via Account Settings

### Admin Features

The Admin Dashboard provides:

#### 🔧 AI Configuration
- Configure default LLM models (OpenAI, Anthropic, Gemini)
- Set routing strategy (cost-optimized, latency-optimized, quality-optimized)
- Token limits per request type
- Rate limiting per user/operation

#### 📚 Knowledge Management
- Upload documents (PDF, DOCX, TXT, CSV, JSON, HTML)
- Approve/reject knowledge sources
- View chunk metadata and embeddings
- Version history and rollback
- Tag and organize knowledge

#### 💾 Memory System
- View user memory (short-term, long-term, context)
- Set retention policies
- Configure importance decay
- Monitor memory usage

#### 📊 Analytics & Monitoring
- 30-day cost tracking
- Token usage by model
- Error rates and latency
- Active conversations
- Audit logs

#### 👥 User Management
- Create additional admin users
- Set user roles (superadmin, admin, viewer)
- View user sessions and activity

---

## Chat SDK Integration

### Modern Chat Widget

The RAZE Chat SDK provides enterprise-grade chat capabilities with:
- ✅ Streaming responses (real-time token streaming)
- ✅ Tool integration (execute functions)
- ✅ Memory persistence (context across sessions)
- ✅ Rate limiting & quota management
- ✅ Custom theming & styling
- ✅ Mobile responsive
- ✅ Accessibility (WCAG 2.1)

### Quick Integration

#### Option 1: Embed HTML (Simplest)

```html
<!-- Add to your website -->
<div id="raze-chat"></div>

<script>
  window.RazeConfig = {
    apiUrl: 'https://your-server.com/api',
    apiKey: 'your-sdk-api-key',
    theme: {
      primaryColor: '#7C3AED',
      accentColor: '#06B6D4'
    }
  };
</script>
<script src="https://your-server.com/raze-widget.js"></script>
```

#### Option 2: JavaScript SDK

```javascript
import { RazeChat } from '@raze/chat-sdk';

const chat = new RazeChat({
  apiKey: 'your-api-key',
  apiUrl: 'https://your-server.com/api',
  sessionId: 'user-session-123'
});

// Send message
const response = await chat.sendMessage('Hello!');

// Stream message
await chat.streamMessage('Tell me about AI', (chunk) => {
  console.log('Chunk:', chunk);
});
```

#### Option 3: React Component

```jsx
import { RazeChatComponent } from '@raze/react-chat';

export default function MyApp() {
  return (
    <RazeChatComponent
      apiKey={process.env.REACT_APP_RAZE_API_KEY}
      theme={{ primaryColor: '#7C3AED' }}
      onMessage={(msg) => console.log('New message:', msg)}
    />
  );
}
```

### Getting SDK API Key

1. Login to Admin Dashboard
2. Go to **Integrations** → **SDK Keys**
3. Create new key (gives API key for embedding)
4. Configure rate limits, scopes

### SDK Features

**Message Types:**
- Text messages
- Code blocks with syntax highlighting
- Tables and formatted data
- Cards (like ChatGPT)
- Images and media
- Action buttons

**Advanced Capabilities:**
- Knowledge base search
- Tool/function calling
- Memory persistence
- User context injection
- Custom system prompts

---

## Testing & Verification

### Health Checks

```bash
# Backend health
curl http://localhost/api/v1/health

# Frontend
curl http://localhost/ | grep -q "html" && echo "OK"

# Database
docker compose exec postgres pg_isready -U raze -d raze

# Redis
docker compose exec redis redis-cli ping

# Qdrant
curl http://localhost:6333/health | jq .
```

### Quick Test Script

```bash
bash scripts/test-deployment.sh
```

This runs:
- ✅ Container health checks
- ✅ Database connectivity
- ✅ LLM endpoint validation
- ✅ Knowledge base search
- ✅ Chat endpoint test
- ✅ Admin API endpoints

### Manual API Testing

**Create a test user:**
```bash
curl -X POST http://localhost/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!",
    "full_name": "Test User"
  }'
```

**Login:**
```bash
curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!"
  }' | jq -r '.access_token'
```

**Send a chat message:**
```bash
TOKEN="<access-token-from-login>"

curl -X POST http://localhost/api/v1/chat/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! Tell me about yourself.",
    "use_knowledge": true,
    "use_memory": true,
    "tools_enabled": true
  }' | jq .
```

**Stream chat (Server-Sent Events):**
```bash
curl -X POST http://localhost/api/v1/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain quantum computing in detail"
  }'
```

---

## Production Configuration

### 1. HTTPS/SSL Setup

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Request certificate
sudo certbot certonly --standalone -d your-domain.com

# Update docker-compose.yml nginx config with SSL paths
```

### 2. Custom Domain

Update `.env`:
```bash
NEXT_PUBLIC_API_URL=https://your-domain.com/api
ALLOWED_ORIGINS=https://your-domain.com
```

### 3. Database Backups

```bash
# Automated daily backup
docker compose exec postgres pg_dump -U raze raze | \
  gzip > backups/raze_$(date +%Y-%m-%d).sql.gz

# Or use: make backup
```

### 4. Monitor Services

```bash
# View all logs
docker compose logs -f

# Filter by service
docker compose logs -f backend
docker compose logs -f postgres

# Export logs
docker compose logs > logs-$(date +%Y-%m-%d).txt
```

### 5. Performance Tuning

**PostgreSQL:**
```bash
docker compose exec postgres psql -U raze -d raze <<'SQL'
ANALYZE;  -- Update statistics
REINDEX;  -- Rebuild indexes
VACUUM;   -- Clean up space
SQL
```

**Redis:**
```bash
# Monitor memory usage
docker compose exec redis redis-cli INFO memory

# Clear old sessions if needed
docker compose exec redis redis-cli FLUSHDB
```

---

## Service Management

### Start/Stop

```bash
# Start all services
docker compose up -d

# Stop all
docker compose down

# Restart specific service
docker compose restart backend

# View status
docker compose ps
```

### Update Code

```bash
# Pull latest changes
git pull origin main

# Rebuild affected images
docker compose build backend frontend

# Restart services
docker compose up -d

# Run migrations if needed
docker compose exec backend alembic upgrade head
```

### View Logs

```bash
# All services (last 100 lines)
docker compose logs --tail=100

# Specific service, follow mode
docker compose logs -f backend

# With timestamps
docker compose logs --timestamps backend
```

---

## Troubleshooting

### Backend Won't Start

**Problem:** `docker compose logs backend` shows connection errors

**Solution:**
```bash
# Wait for postgres
sleep 30
docker compose restart backend

# Or check database manually
docker compose exec postgres psql -U raze -d raze -c "SELECT version();"
```

### CORS Errors in Frontend

**Problem:** Browser console shows "Access to XMLHttpRequest blocked by CORS"

**Solution:**
```bash
# Verify .env
grep ALLOWED_ORIGINS .env

# Restart nginx
docker compose restart nginx
```

### Chat Streaming Cuts Off

**Problem:** SSE stream stops before completion

**Solution:**
```bash
# Check nginx SSE config
docker compose exec nginx nginx -t

# Increase timeout
# Edit docker-compose.yml nginx section, add:
# environment:
#   - NGINX_TIMEOUT=300
```

### Database Migrations Fail

**Problem:** `alembic upgrade head` fails

**Solution:**
```bash
# Check migration status
docker compose exec backend alembic current

# View failed migration
docker compose logs backend | grep -A 10 "alembic"

# Reset (WARNING: loses data)
docker compose down
docker volume rm raze_postgres_data
docker compose up -d
docker compose exec backend alembic upgrade head
```

### Out of Memory

**Problem:** Container crashes with OOM

**Solution:**
```bash
# Increase Docker memory
# Edit docker-compose.yml, add to services:
# deploy:
#   resources:
#     limits:
#       memory: 4G

# Or clean up
docker system prune --volumes
```

### Knowledge Search Returns Empty

**Problem:** Uploaded documents aren't being found

**Solution:**
1. Verify documents are approved in Admin → Knowledge
2. Check Qdrant has embeddings: `curl http://localhost:6333/collections`
3. Trigger reprocessing: Admin → Knowledge → Source → Reprocess

---

## Useful Make Commands

```bash
make logs              # Tail all logs
make logs-backend      # Tail backend logs
make shell-backend     # SSH into backend container
make shell-db          # psql shell
make backup            # Create database backup
make clean             # Remove containers
make reset             # Full reset (deletes data!)
make health            # Quick health check
make migrate           # Run migrations
make test              # Run test suite
```

---

## Support & Resources

- **Documentation:** https://raze-docs.example.com
- **API Swagger:** http://your-server/docs
- **GitHub Issues:** https://github.com/your-org/raze
- **Email Support:** support@raze.example.com

---

**Last Updated:** April 18, 2026  
**Version:** RAZE 1.0.0 Enterprise Edition
