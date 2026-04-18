# RAZE Enterprise AI OS - Fresh Server Deployment Guide

## ✅ Fully Automated Setup (Everything Works Out of the Box)

This guide covers deploying RAZE on a fresh server with **zero manual configuration**.

---

## **What Gets Auto-Installed:**

✅ **PostgreSQL** - Database  
✅ **Redis** - Caching & session management  
✅ **Qdrant** - Vector search engine  
✅ **MinIO** - File storage  
✅ **Ollama** - Local AI engine  
✅ **Mistral Model** - Default LLM (auto-downloaded)  
✅ **FastAPI Backend** - AI orchestration  
✅ **Next.js Frontend** - Admin dashboard  
✅ **Nginx** - Reverse proxy  

**Total setup time: ~10-15 minutes** (mostly Mistral download)

---

## **Prerequisites:**

### **System Requirements:**
- **OS**: Linux (Ubuntu 20.04+, Debian, CentOS, etc.)
- **CPU**: 2+ cores
- **RAM**: 4GB minimum (8GB recommended for Mistral)
- **Storage**: 50GB+ (includes Mistral model)
- **Docker**: 20.10+
- **Docker Compose**: 2.0+

### **Install Docker & Docker Compose:**

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

---

## **Deployment Steps:**

### **Step 1: Clone or Extract RAZE**

```bash
# Option A: From repository
git clone https://github.com/your-org/raze.git
cd raze

# Option B: From archive
unzip raze.zip
cd raze
```

### **Step 2: Create Environment File**

```bash
cat > .env << 'EOF'
# Database
POSTGRES_DB=raze
POSTGRES_USER=raze
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Redis
REDIS_PASSWORD=$(openssl rand -base64 32)

# MinIO (File Storage)
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=$(openssl rand -base64 32)

# Qdrant (Vector Search)
QDRANT_API_KEY=$(openssl rand -base64 32)

# JWT Secrets
JWT_SECRET_KEY=$(openssl rand -base64 32)

# Default Settings
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_DEFAULT_MODEL=mistral

DEBUG=false
EOF

# Secure the file
chmod 600 .env
```

### **Step 3: Start All Services**

```bash
# Pull latest images
docker compose pull

# Start all containers
docker compose up -d

# Watch initialization (5-15 minutes)
docker compose logs -f ollama
```

You should see:
```
🤖 Ollama Model Initialization
=============================="
Waiting for Ollama to be ready...
✅ Ollama is ready
📥 No models found - pulling default models...
📦 Pulling mistral (this may take 5-10 minutes)...
✅ Mistral downloaded successfully
🎉 Ollama initialization complete!
```

### **Step 4: Verify All Services Are Healthy**

```bash
docker compose ps

# Expected output (all HEALTHY):
raze_postgres    ✓ healthy
raze_redis       ✓ healthy  
raze_qdrant      ✓ healthy
raze_minio       ✓ healthy
raze_ollama      ✓ healthy
raze_backend     ✓ healthy
raze_frontend    ✓ healthy
raze_nginx       ✓ healthy
```

### **Step 5: Access the Application**

Open browser to:
```
http://your-server-ip:80
```

Or if deployed on localhost:
```
http://localhost
```

---

## **First Login:**

When you access the dashboard for the first time:

**Email:** `admin@yourcompany.com`  
**Password:** `admin123`

---

## **Verify Everything Works:**

### **1. Check Ollama & Mistral:**
```bash
curl http://localhost:11434/api/tags
# Should return: {"models":[{"name":"mistral:latest",...}]}
```

### **2. Test Chat Endpoint:**
```bash
# Get JWT token
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yourcompany.com","password":"admin123"}' | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

# Test chat
curl -X POST http://localhost/api/v1/chat/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"hello","use_knowledge":false}'

# Should return JSON with AI response
```

### **3. Test Admin Dashboard:**
- Go to Settings → Provider Setup
- Verify Ollama is listed
- Go to Test Chat → Type a message → Should get response from Mistral

---

## **Post-Deployment Configuration:**

### **Optional: Add Additional LLM Providers**

Go to Settings → Provider Setup and add:
- **OpenAI**: Your API key
- **Anthropic**: Your Claude API key
- **Google Gemini**: Your API key
- **Grok**: Your API key (via Twitter)

### **Optional: Customize White Label**

Go to Settings → White Label and configure:
- Brand name
- Primary color
- Logo URL

### **Optional: Download Additional Ollama Models**

```bash
# List available models at https://ollama.ai/library

# Download another model (e.g., Neural Chat)
docker exec raze_ollama ollama pull neural-chat

# List installed models
curl http://localhost:11434/api/tags
```

---

## **Persistent Data Locations:**

All data is stored in Docker volumes:

```bash
# View all volumes
docker volume ls | grep raze

# Backup data
docker run --rm -v raze_postgres_data:/backup \
  -v $(pwd):/output alpine tar czf /output/raze-backup.tar.gz /backup
```

---

## **Updating RAZE:**

```bash
# Pull latest code
git pull origin main

# Rebuild containers
docker compose down
docker compose build
docker compose up -d

# Data is preserved automatically
```

---

## **Troubleshooting:**

### **Mistral Download Stuck?**

```bash
# Check Ollama logs
docker logs raze_ollama

# Check available disk space
df -h

# If needed, manually pull model
docker exec raze_ollama ollama pull mistral
```

### **Backend Not Starting?**

```bash
# Check backend logs
docker logs raze_backend

# Rebuild backend
docker compose build --no-cache raze_backend
docker compose up -d raze_backend
```

### **Cannot Login?**

```bash
# Reset admin password
docker exec -i raze_postgres psql -U raze -d raze << 'SQL'
UPDATE users 
SET hashed_password = '$2b$12$aaUtVXqutkvP0ivJ9PyAZur0e84MWFaPY2B4gYEPe2GDRfS6dFXgy' 
WHERE email = 'admin@yourcompany.com';
SQL

# Password is now: admin123
```

### **Out of Disk Space?**

```bash
# Clean up Docker
docker system prune -a

# Or remove old Ollama models
docker exec raze_ollama ollama rm old-model-name
```

---

## **Production Recommendations:**

### **SSL/HTTPS:**
Use Let's Encrypt with Nginx:
```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone -d your-domain.com

# Update nginx config to use SSL
```

### **Reverse Proxy:**
Change Nginx to listen on your domain instead of localhost:80

### **Backup Strategy:**
```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR=/backups/raze
mkdir -p $BACKUP_DIR
docker exec raze_postgres pg_dump -U raze raze > $BACKUP_DIR/db-$(date +%Y%m%d).sql
docker volume inspect raze_ollama_data > $BACKUP_DIR/ollama-$(date +%Y%m%d).json
```

### **Monitor Services:**
```bash
# Check container status
docker compose ps

# View resource usage
docker stats raze_*

# Monitor logs
docker compose logs --tail 100 -f
```

---

## **What's Included by Default:**

✅ **Admin Chat** - Full-featured AI chat agent  
✅ **Knowledge Management** - Upload & search documents  
✅ **Settings Dashboard** - Configure AI, white label, providers  
✅ **Analytics** - Track usage & performance  
✅ **Memory Management** - Session & long-term memory  
✅ **Tool Integration** - Extend AI with custom tools  
✅ **Chat SDK** - Embed chat widget on websites  

---

## **Support:**

For issues or questions:
1. Check logs: `docker compose logs -f`
2. Review this guide's troubleshooting section
3. Visit https://github.com/your-org/raze/issues

---

## **Key Files for Fresh Setup:**

```
raze/
├── docker-compose.yml          # Complete stack definition
├── docker/
│   ├── ollama-init.sh          # Auto-pulls Mistral on startup
│   ├── postgres/Dockerfile     # Database setup
│   └── ...
├── .env                        # Your environment variables (CREATE THIS)
└── FRESH_DEPLOYMENT_GUIDE.md   # This file
```

---

**🎉 Your RAZE instance is now fully operational with Mistral AI ready to go!**

Mistral will automatically download on first startup and be available for use immediately.
