# 🚀 RAZE Deployment Guide — Complete & Unified

**Deploy your branded RAZE platform in 3 simple phases: Prepare → Deploy → Verify**

> **This is the ONLY guide you need.** It consolidates setup.sh, SERVER_SETUP.md, QUICK_START.md, and DEPLOYMENT_CHECKLIST.md into one clear path.

---

## ⏱️ Time Required

- **Phase 1 (Prepare):** 15 minutes
- **Phase 2 (Deploy):** 15 minutes (mostly waiting for Docker)
- **Phase 3 (Verify):** 10 minutes
- **Total:** ~40 minutes to fully functional platform

---

## 📋 Pre-Deployment Checklist

Before starting, make sure you have:

- [ ] Server access (Ubuntu 20.04+, Debian 11+, or macOS)
- [ ] 4+ CPU cores, 8+ GB RAM, 50+ GB disk
- [ ] Internet connection (30+ Mbps)
- [ ] OpenAI API key (from https://platform.openai.com)
- [ ] Your company name & brand colors (optional, but recommended)
- [ ] Domain name (optional, for production)

**Don't have these yet?**
```bash
# Generate OpenAI key: https://platform.openai.com/account/api-keys
# Generate secure passwords: bash scripts/generate-secrets.sh
# Choose colors: See BRANDING.md
```

---

# 🟢 PHASE 1: PREPARE

## Step 1.1: SSH Into Your Server

```bash
ssh root@your-server-ip
# or: ssh ubuntu@your-server-ip
```

## Step 1.2: Create RAZE Directory

```bash
mkdir -p /opt/raze
cd /opt/raze
```

## Step 1.3: Clone Repository

```bash
git clone https://github.com/your-org/raze.git .
chmod +x setup.sh scripts/*.sh
```

**Expected output:**
```
Cloning into '.'...
remote: Enumerating objects...
Receiving objects: 100% (...)
```

## Step 1.4: Customize Branding (Optional)

If you want custom branding (recommended):

```bash
nano .env.example
```

Look for these lines and customize:

```bash
# From BRANDING.md - healthcare example
BRAND_NAME=YourCompanyName
CHATBOT_NAME=YourAI Assistant
THEME_PRIMARY_COLOR=#7C3AED
THEME_ACCENT_COLOR=#06B6D4
COMPANY_NAME=Your Company Inc.
COMPANY_WEBSITE=https://yourcompany.com
INDUSTRY_TYPE=healthcare  # or: legal, finance, education, saas, ecommerce, creative
```

**Not sure about colors?** See industry presets in [BRANDING.md](BRANDING.md)

---

# 🟡 PHASE 2: DEPLOY (Automated)

## Step 2.1: Run One Command

```bash
bash setup.sh
```

This single command will:

✅ Check/install Docker  
✅ Generate secure credentials  
✅ Create `.env` file  
✅ Build all Docker images  
✅ Start all services  
✅ Run database migrations  
✅ Create admin user  

**What happens:**
```
═══════════════════════════════════════════════════════════
  RAZE Enterprise AI OS — Setup Script
═══════════════════════════════════════════════════════════

[INFO] Detecting operating system
[OK] Linux: Ubuntu 22.04 LTS (x86_64)

[INFO] Checking Docker installation
[OK] Docker 25.0.0 is already installed and running

[INFO] Checking Docker Compose v2
[OK] Docker Compose v2 (v2.x.x) is available

[INFO] Creating required directories and files
[OK] Created scripts/init-db.sql

[INFO] Setting up environment file
[INFO] Generating secure credentials
[OK] Generated JWT secret key
[OK] Generated PostgreSQL password
[OK] Generated Redis password
[OK] Generated MinIO root password
[OK] Generated Qdrant API key
[OK] .env configured with generated credentials

[INFO] Pulling Docker base images
[OK] (pulls postgres, redis, minio, qdrant, nginx)

[INFO] Building application images
[INFO] Building backend image...
[OK] Backend image built
[INFO] Building frontend image...
[OK] Frontend image built

[INFO] Starting infrastructure services
[INFO] postgres, redis, minio, qdrant...

[INFO] Waiting for PostgreSQL to be healthy
[INFO] Waiting for postgres... (5s elapsed)
[OK] PostgreSQL is healthy

[INFO] Waiting for Redis to be healthy
[OK] Redis is healthy

[INFO] Running database migrations
[OK] Database migrations applied

[INFO] Starting all services
[OK] All services started

[INFO] Service status
NAME       IMAGE          STATUS
postgres   postgres:16    Up 2 minutes
redis      redis:7        Up 2 minutes
minio      minio:latest   Up 2 minutes
qdrant     qdrant:latest  Up 2 minutes
backend    raze:backend   Up 1 minute
frontend   raze:frontend  Up 1 minute
nginx      nginx:latest   Up 1 minute

════════════════════════════════════════════════════════════
         RAZE Enterprise AI OS is up and running!
════════════════════════════════════════════════════════════

Access URLs:
  ● Frontend (Admin UI)  : http://192.168.1.100/
  ● Backend API          : http://192.168.1.100/api/
  ● API Docs (Swagger)   : http://192.168.1.100/docs
  ● MinIO Console        : http://192.168.1.100:9001/
  ● Qdrant Dashboard     : http://192.168.1.100:6333/dashboard

MinIO Credentials:
  User     : raze_admin
  Password : xxxxxxxxxxxxxxxx

Useful commands:
  make logs           — tail all service logs
  make shell-backend  — open backend shell
  make shell-db       — open psql shell
  make backup         — dump database
  make down           — stop all services

All credentials are saved in .env (keep it secret!)
```

## Step 2.2: Wait for Everything to Start (5-10 minutes)

The setup script runs automatically. **Just wait.** Services need time to:
- Build Docker images
- Start PostgreSQL
- Initialize database
- Run migrations
- Create admin user

## Step 2.3: Verify Services Started

```bash
docker compose ps
```

**Expected output:** All services show "Up"

```
NAME       IMAGE          STATUS
postgres   postgres:16    Up 3 minutes
redis      redis:7        Up 3 minutes
minio      minio:latest   Up 3 minutes
qdrant     qdrant:latest  Up 3 minutes
backend    raze:backend   Up 2 minutes
frontend   raze:frontend  Up 2 minutes
nginx      nginx:latest   Up 2 minutes
```

**If any show "Exited":**
```bash
docker compose logs backend  # Check backend for errors
docker compose restart backend
```

---

# 🟢 PHASE 3: VERIFY & ACCESS

## Step 3.1: Quick Health Check

```bash
make health
```

**Expected output:**
```
✓ Docker daemon running
✓ PostgreSQL healthy
✓ Redis responsive
✓ Qdrant vector database
✓ Backend API responding
✓ Frontend accessible
✓ Nginx routing working
✓ Database migrations current
✓ Configuration files valid

═══════════════════════════════════════════════════════════
All systems operational! ✓
═══════════════════════════════════════════════════════════
```

## Step 3.2: Run Comprehensive Tests

```bash
make test
```

This verifies:
- All containers healthy
- Database connectivity
- API endpoints responding
- Nginx routing
- Migrations current

**Expected:** All tests PASS ✓

## Step 3.3: Access Your Platform

Open your browser to:

| Service | URL |
|---------|-----|
| **Admin Dashboard** | `http://<YOUR_SERVER_IP>/` |
| **API Documentation** | `http://<YOUR_SERVER_IP>/docs` |
| **MinIO Console** | `http://<YOUR_SERVER_IP>:9001/` |

## Step 3.4: Login to Admin Dashboard

1. Open `http://<YOUR_SERVER_IP>/`
2. **Email:** `admin@yourcompany.com`
3. **Password:** `ChangeMe123!`

**⚠️ IMPORTANT:** Change this password immediately!

```
Click Account Settings → Change Password
Save new password in password manager
```

## Step 3.5: Configure AI Keys

1. Go to **Settings** → **AI Configuration**
2. Click **"Add AI Configuration"**
3. Select model: **GPT-4-Turbo** (recommended)
4. Paste your **OpenAI API key**
5. Click **"Save & Test"**
6. If green checkmark appears ✅, you're ready!

## Step 3.6: Test Chat

1. Go to **Chat** (or chat icon)
2. Type: "Hello! What can you do?"
3. Press Send

**Expected:** AI responds with its capabilities

---

# 📚 NEXT STEPS: Configure Your Platform

## Upload Knowledge Documents

1. **Admin Dashboard** → **Knowledge** → **Upload Source**
2. Choose PDF, DOCX, TXT, CSV, JSON, or HTML
3. Wait 30-60 seconds for processing
4. Status shows **"Approved"**

## Test Knowledge Search

1. Go to **Knowledge** → **Search**
2. Type a question about your document
3. See results appear

## Invite Team Members

1. **Admin** → **Users** → **Add User**
2. Enter email & choose role
3. They receive invitation link
4. They can login and chat

## Monitor Analytics

1. **Admin** → **Analytics** → **Dashboard**
2. See 30-day cost, token usage, error rates
3. Track conversations & memory usage

---

# 🎨 OPTIONAL: Custom Branding

Want to customize for your company/industry?

1. See [BRANDING.md](BRANDING.md)
2. Choose industry preset (healthcare, legal, finance, etc.)
3. Update `.env` with colors & company name
4. Rebuild: `docker compose build frontend`
5. Restart: `docker compose up -d`

Takes 5 minutes, fully transforms the look!

---

# 🔒 PRODUCTION DEPLOYMENT (For HTTPS/Domain)

If you have a domain and want HTTPS:

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot certonly --standalone -d your-domain.com

# Update .env with your domain
NEXT_PUBLIC_API_URL=https://your-domain.com/api
ALLOWED_ORIGINS=https://your-domain.com

# Restart
docker compose restart nginx
```

Or follow detailed steps in [SERVER_SETUP.md](SERVER_SETUP.md#production-configuration)

---

# 🛠️ Useful Commands (Bookmark These!)

## View Logs

```bash
make logs              # All services
make logs-backend      # Backend only
make logs-postgres     # Database only
```

## Database Management

```bash
make shell-db          # Open psql shell
make backup            # Create backup
make restore FILE=backups/raze_YYYYMMDD_HHMMSS.pgdump
```

## Service Management

```bash
make up                # Start all
make down              # Stop all
make restart           # Restart all
make restart-backend   # Restart backend only
```

## Testing & Verification

```bash
make health            # Quick health check
make test              # Run all tests
make setup-admin       # Create additional admin users
```

## API Testing

```bash
# Get auth token
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email":"admin@yourcompany.com",
    "password":"YOUR_PASSWORD"
  }' | jq -r '.access_token')

# Send test message
curl -X POST http://localhost/api/v1/chat/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message":"Hello! Tell me about yourself.",
    "use_knowledge":true
  }' | jq .
```

---

# ❌ Troubleshooting

## Services won't start?

```bash
# Check logs
docker compose logs

# Check specific service
docker compose logs backend

# Restart
docker compose down
docker compose up -d
```

## Backend crashes?

```bash
# View full logs
docker compose logs backend --tail=100

# Most common issues:
# 1. Database not ready - wait 30s and restart
# 2. Missing .env variables - check .env exists
# 3. Port conflict - check ports 8000, 3000, 5432 are free
```

## Database errors?

```bash
# Check database is running
docker compose exec postgres pg_isready -U raze -d raze

# View database logs
docker compose logs postgres

# Reset database (⚠️ LOSES DATA)
docker compose down
docker volume rm raze_postgres_data
docker compose up -d
```

## Chat API not responding?

```bash
# Check backend health
curl http://localhost/health

# Check API docs
curl http://localhost/docs

# Verify OpenAI key is set
grep OPENAI_API_KEY .env
```

## Forgot admin password?

```bash
# Reset to default
docker compose exec postgres psql -U raze -d raze <<'SQL'
UPDATE public.users 
SET hashed_password = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQyCi1O7EUmg7BM.s9nOGIEU.'
WHERE email = 'admin@yourcompany.com';
SQL

# Login with: admin@yourcompany.com / ChangeMe123!
# Then change password in Settings
```

---

# 📞 Support & Resources

| Resource | Link |
|----------|------|
| **Full Setup Guide** | [SERVER_SETUP.md](SERVER_SETUP.md) |
| **Branding & Theming** | [BRANDING.md](BRANDING.md) |
| **Deployment Checklist** | [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) |
| **Quick Start** | [QUICK_START.md](QUICK_START.md) |
| **API Documentation** | `http://<your-server>/docs` |
| **Repository Issues** | https://github.com/your-org/raze |

---

# ✅ Final Checklist

- [ ] Phase 1: Prepare (clone, customize .env, branding)
- [ ] Phase 2: Deploy (run `setup.sh`, wait for completion)
- [ ] Phase 3: Verify (run `make health`, run `make test`)
- [ ] Access dashboard at `http://<SERVER_IP>/`
- [ ] Login with credentials provided by setup.sh
- [ ] Change admin password
- [ ] Add OpenAI API key
- [ ] Upload sample document
- [ ] Test chat
- [ ] Everything works! 🎉

---

# 🎉 You're Done!

Your RAZE platform is now **fully deployed and ready to use.**

## What You Can Do Now:

✅ Chat with AI (streaming responses)  
✅ Search knowledge base  
✅ Upload documents  
✅ Manage users & permissions  
✅ Monitor usage & costs  
✅ Configure AI models  
✅ Persist user memory  
✅ View audit logs  

## Next:

- Invite your team members
- Upload your company documents to knowledge base
- Customize admin settings
- Monitor usage in analytics
- Scale if needed

---

## Questions?

- **Setup issues?** Check [SERVER_SETUP.md](SERVER_SETUP.md#troubleshooting)
- **Branding help?** See [BRANDING.md](BRANDING.md)
- **Deployment help?** See [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
- **API help?** Visit `http://<your-server>/docs`

**Happy deploying! 🚀**
