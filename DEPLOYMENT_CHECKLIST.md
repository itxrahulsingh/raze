# RAZE Production Deployment Checklist

**Use this checklist to ensure your RAZE deployment is production-ready.**

---

## Pre-Deployment (24 hours before)

### Infrastructure
- [ ] Server provisioned (4+ vCPU, 8+ GB RAM, 50+ GB SSD)
- [ ] Ubuntu 20.04+ or Debian 11+ installed
- [ ] SSH access configured
- [ ] Network ports 80, 443 accessible
- [ ] Domain name registered & DNS configured
- [ ] SSL certificate obtained (Let's Encrypt or custom)

### Credentials & Keys
- [ ] OpenAI API key obtained and validated
- [ ] Anthropic API key (optional) obtained
- [ ] Strong PostgreSQL password generated
- [ ] Strong Redis password generated
- [ ] Strong MinIO password generated
- [ ] JWT secret key generated (64 hex characters)
- [ ] Stored in secure location (password manager)

---

## Deployment Day (Step-by-step)

### Step 1: Prepare Server (15 minutes)
```bash
# SSH into server
ssh root@your-server-ip

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Create RAZE directory
sudo mkdir -p /opt/raze
sudo chown $(id -u):$(id -g) /opt/raze
```

- [ ] System updated
- [ ] RAZE directory created

### Step 2: Clone Repository (5 minutes)
```bash
cd /opt/raze
git clone <your-repo-url> .
chmod +x setup.sh
```

- [ ] Repository cloned
- [ ] Scripts executable

### Step 3: Configure Environment (10 minutes)
```bash
# Review template
nano .env.example

# Copy and customize
cp .env.example .env
nano .env
```

**Critical variables to verify:**
- [ ] `SERVER_IP` — Set to your server's public IP
- [ ] `ENVIRONMENT=production`
- [ ] `DEBUG=false`
- [ ] `POSTGRES_PASSWORD` — Strong, 16+ characters
- [ ] `REDIS_PASSWORD` — Strong, 16+ characters
- [ ] `JWT_SECRET_KEY` — 64 hex characters
- [ ] `OPENAI_API_KEY` — Your OpenAI key
- [ ] `NEXT_PUBLIC_API_URL` — Points to your domain
- [ ] `ALLOWED_ORIGINS` — Includes your domain

Use this command to generate secrets:
```bash
bash scripts/generate-secrets.sh
```

- [ ] All environment variables configured
- [ ] Secrets verified as strong
- [ ] API keys validated

### Step 4: Run Automated Setup (10-15 minutes)
```bash
bash setup.sh
```

This script:
- Installs Docker (if needed)
- Generates missing credentials
- Builds all images
- Starts all services
- Runs migrations
- Creates default admin user

Wait for completion...

- [ ] Setup script completed successfully
- [ ] All services started
- [ ] Database migrations applied

### Step 5: Verify Deployment (10 minutes)
```bash
# Check all services
make health

# Run comprehensive tests
make test

# View logs if needed
make logs
```

**All tests should PASS:**
- [ ] Docker daemon running
- [ ] PostgreSQL healthy
- [ ] Redis responsive
- [ ] Qdrant vector DB accessible
- [ ] Backend API responding
- [ ] Frontend accessible
- [ ] Nginx routing working
- [ ] Database migrations current
- [ ] Configuration files valid

### Step 6: Create Admin User
```bash
make setup-admin
```

This creates:
- Default admin user (admin@yourcompany.com / ChangeMe123!)
- Default AI configurations (GPT-4, GPT-3.5)
- Initial system settings

- [ ] Admin user created
- [ ] AI configurations initialized
- [ ] Can login to admin dashboard

### Step 7: Secure Admin Access
```bash
# Test login
curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@yourcompany.com",
    "password": "ChangeMe123!"
  }'
```

Then via browser:
1. Open `http://your-domain/`
2. Login with email/password above
3. **IMMEDIATELY** go to Account Settings
4. Change password to something strong
5. **SAVE NEW PASSWORD IN PASSWORD MANAGER**

- [ ] Can login to admin dashboard
- [ ] Can access all admin sections
- [ ] Password changed from default

### Step 8: Configure LLM Keys
In Admin Dashboard → Settings → AI Configuration:

1. Click "Add AI Configuration"
2. Select model (GPT-4, Claude 3, etc.)
3. Enter API key
4. Set as default if desired
5. Test with sample prompt

- [ ] OpenAI API key configured
- [ ] Can send test messages
- [ ] Response is generated and streamed

### Step 9: Test Knowledge Base
In Admin Dashboard → Knowledge → Upload Source:

1. Upload a sample PDF or text file
2. Wait for processing (may take 30-60s)
3. Verify status shows "Approved"
4. Go to Knowledge → Search
5. Try searching for content from uploaded file

- [ ] Can upload documents
- [ ] Documents processed successfully
- [ ] Knowledge search returns results

### Step 10: Test Chat API
```bash
# Get token
TOKEN=$(curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yourcompany.com","password":"YOUR_NEW_PASSWORD"}' \
  | jq -r '.access_token')

# Send message
curl -X POST http://localhost/api/v1/chat/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello! Tell me about yourself.","use_knowledge":true}' \
  | jq .
```

Expected: Response with message content, model used, tokens consumed

- [ ] Can send messages via API
- [ ] Gets sensible responses
- [ ] Streaming works (if testing /stream endpoint)

### Step 11: Setup HTTPS/SSL (15 minutes)
```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone -d your-domain.com

# Update docker-compose.yml to use SSL certificates
# Copy nginx.conf to use SSL paths
# Restart nginx
```

Or use Let's Encrypt + auto-renewal:
```bash
sudo certbot renew --dry-run  # Test
```

- [ ] SSL certificate obtained
- [ ] Nginx configured for HTTPS
- [ ] Can access https://your-domain.com
- [ ] All HTTP requests redirect to HTTPS

### Step 12: Enable Firewall
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow MinIO console from admin IPs only (optional)
sudo ufw allow from <YOUR_IP> to any port 9001

sudo ufw enable
```

- [ ] Firewall rules configured
- [ ] Can still SSH into server
- [ ] Can access RAZE via HTTP/HTTPS
- [ ] Unnecessary ports blocked

---

## Post-Deployment (1-2 hours after)

### Monitor Services
```bash
# Watch logs for 30 minutes to catch any errors
make logs

# Check service health periodically
watch make health
```

- [ ] No error messages in logs
- [ ] Services remain healthy over time
- [ ] No memory/CPU spikes

### Verify All Components
- [ ] Admin Dashboard loads
- [ ] API documentation accessible
- [ ] Database queries responsive
- [ ] Chat responses generate correctly
- [ ] Knowledge search works
- [ ] Memory persistence working

### Setup Automated Backups
```bash
# Test backup
make backup

# Setup cron job
sudo crontab -e

# Add this line to backup daily at 2 AM:
# 0 2 * * * cd /opt/raze && make backup
```

- [ ] Backup created successfully
- [ ] Cron job scheduled
- [ ] Backup file verified in backups/ folder

### Configure Log Rotation
```bash
# Create log rotation config
sudo cat > /etc/logrotate.d/raze <<'EOF'
/opt/raze/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 raze raze
}
EOF
```

- [ ] Log rotation configured
- [ ] Old logs will be automatically cleaned

---

## Security Hardening Checklist

### Secrets Management
- [ ] `.env` file is NOT in git (check .gitignore)
- [ ] `.env` backed up securely (password manager)
- [ ] All passwords are 16+ characters
- [ ] API keys rotated if leaked
- [ ] No secrets in logs

### Access Control
- [ ] Only admins can access admin dashboard
- [ ] SSH key authentication configured (no password SSH)
- [ ] Regular users don't have server access
- [ ] Database passwords different from app secrets
- [ ] API keys have appropriate scopes

### Network Security
- [ ] Firewall enabled and configured
- [ ] Only necessary ports open
- [ ] HTTPS enforced (HTTP → HTTPS redirect)
- [ ] SSL certificate auto-renewal configured
- [ ] Rate limiting enabled (configured in app)

### Data Protection
- [ ] Regular backups scheduled
- [ ] Backup storage is separate from server
- [ ] Database encryption at rest (if available)
- [ ] User passwords hashed with bcrypt
- [ ] Sensitive data not logged

---

## Performance Verification Checklist

### Response Times
- [ ] Admin dashboard loads < 2 seconds
- [ ] Chat API responds < 5 seconds
- [ ] Knowledge search < 3 seconds
- [ ] Streaming latency acceptable

### Resource Usage
- [ ] CPU usage < 70% at baseline
- [ ] RAM usage < 75% at baseline
- [ ] Disk usage < 80% (50+ GB available)
- [ ] Network bandwidth sufficient

### Database Health
```bash
# Check database size
docker compose exec postgres psql -U raze -d raze \
  -c "SELECT pg_size_pretty(pg_database_size('raze'));"

# Check indexes
docker compose exec postgres psql -U raze -d raze \
  -c "SELECT schemaname, tablename, indexname FROM pg_indexes LIMIT 10;"

# Analyze for query optimization
docker compose exec postgres psql -U raze -d raze -c "ANALYZE;"
```

- [ ] Database size reasonable
- [ ] Indexes created
- [ ] Query performance acceptable

---

## Documentation & Runbooks

### Create Server Documentation
- [ ] Document server IP and access method
- [ ] Document admin credentials (in password manager)
- [ ] Document API keys and endpoints
- [ ] Document backup procedure
- [ ] Document upgrade procedure

### Create Runbooks
- [ ] Restart all services
- [ ] Restart single service
- [ ] View logs
- [ ] Create database backup
- [ ] Restore from backup
- [ ] Troubleshoot common issues

---

## Final Verification

Run this complete test:
```bash
#!/bin/bash
set -e

echo "🔍 Running final verification..."

# Health checks
make health

# Run tests
make test

# Check logs for errors
echo ""
echo "Checking for errors in logs..."
docker compose logs --since 5m | grep -i error || echo "✅ No errors found"

# Test chat API
echo ""
echo "Testing chat API..."
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yourcompany.com","password":"YOURPASSWORD"}' \
  | jq -r '.access_token')

curl -s -X POST http://localhost/api/v1/chat/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Test message"}' | jq '.message' || echo "❌ Chat API failed"

echo ""
echo "✅ Verification complete!"
```

- [ ] All health checks pass
- [ ] All tests pass
- [ ] No errors in logs
- [ ] Chat API responds correctly
- [ ] Admin can send messages
- [ ] Knowledge search works

---

## Go-Live Sign-off

- [ ] All checklist items completed
- [ ] All tests passing
- [ ] Security verified
- [ ] Performance acceptable
- [ ] Backups tested
- [ ] Team trained on operations
- [ ] Documentation complete
- [ ] Support contacts listed
- [ ] Monitoring configured

**Deployment Date:** _________________

**Deployed By:** _________________

**Approved By:** _________________

---

## Ongoing Maintenance

Schedule these tasks:

**Daily:**
- [ ] Monitor logs for errors
- [ ] Check disk space (20%+ should be free)
- [ ] Verify services are running: `make health`

**Weekly:**
- [ ] Review access logs for suspicious activity
- [ ] Verify backups were created
- [ ] Check for system updates

**Monthly:**
- [ ] Analyze performance trends
- [ ] Update dependencies (if applicable)
- [ ] Review and rotate API keys if needed
- [ ] Full backup verification

**Quarterly:**
- [ ] Security audit
- [ ] Load testing
- [ ] Disaster recovery drill
- [ ] Documentation review

---

**Deployment Complete! 🎉**

Your RAZE Enterprise AI OS is now running in production.

For support: See [SERVER_SETUP.md](SERVER_SETUP.md) and [QUICK_START.md](QUICK_START.md)
