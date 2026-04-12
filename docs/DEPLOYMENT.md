# RAZE Enterprise AI OS - Deployment Guide

## Overview

RAZE is an enterprise-grade AI Operating System designed for deployment on single servers with IP-based access, scaling to multi-server and Kubernetes deployments later. This guide covers complete setup from bare metal to production.

## Prerequisites

### Minimum Hardware
- **CPU**: 4 cores (Intel/AMD)
- **RAM**: 8 GB minimum (16 GB recommended)
- **Storage**: 100 GB SSD minimum (500 GB for production)
- **Network**: Stable internet connection, publicly accessible IP (optional)

### Operating System
- Ubuntu 22.04 LTS or Debian 12
- macOS 12+ (for development/testing)
- Windows with WSL2 (for development)

### Software (Auto-installed by setup.sh)
- Docker 20.10+
- Docker Compose v2
- openssl
- curl

## Quick Start (Single-Click Setup)

### Option 1: Automated Setup (Recommended)

```bash
cd /path/to/raze
bash setup.sh
```

The script will:
1. Detect your OS (Linux/macOS)
2. Install Docker and Docker Compose if missing
3. Generate security credentials (JWT secrets, database passwords, API keys)
4. Pull/build service images
5. Start all services
6. Run database migrations
7. Print access URLs and credentials
8. Create default admin user

### Option 2: Manual Setup

#### Step 1: Clone and Install Docker

```bash
# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose v2
sudo apt-get install docker-compose-plugin

# Add current user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

#### Step 2: Configure Environment

```bash
cd /Users/rahul/Development/raze

# Copy example env and generate secrets
cp .env.example .env

# Generate JWT secret
JWT_SECRET=$(openssl rand -hex 32)
sed -i "s/your-secret-key-here/$JWT_SECRET/" .env

# Generate database password
DB_PASS=$(openssl rand -hex 16)
sed -i "s/postgres-password/$DB_PASS/" .env

# Generate Redis password
REDIS_PASS=$(openssl rand -hex 16)
sed -i "s/redis-password/$REDIS_PASS/" .env

# Generate MinIO credentials
MINIO_USER=$(openssl rand -hex 8)
MINIO_PASS=$(openssl rand -hex 16)
sed -i "s/minio-user/$MINIO_USER/" .env
sed -i "s/minio-password/$MINIO_PASS/" .env

# Set your server IP
export SERVER_IP=$(hostname -I | awk '{print $1}')
echo "SERVER_IP=$SERVER_IP" >> .env
```

#### Step 3: Start Services

```bash
docker compose up -d

# Wait for services to be ready
sleep 30

# Run database migrations
docker compose exec backend alembic upgrade head

# Verify all services are running
docker compose ps

# Check logs
docker compose logs -f backend
```

#### Step 4: Create Admin User

```bash
docker compose exec backend python -c "
import asyncio
from app.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash

async def create_admin():
    async with AsyncSessionLocal() as db:
        admin = User(
            id='admin-001',
            email='admin@raze.local',
            username='admin',
            hashed_password=get_password_hash('change-me-in-production'),
            role='superadmin',
            is_active=True
        )
        db.add(admin)
        await db.commit()
        print('Admin created: admin@raze.local / change-me-in-production')

asyncio.run(create_admin())
"
```

## Environment Configuration

Edit `.env` to configure:

### Core Services
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `QDRANT_URL` - Qdrant vector DB URL
- `MINIO_ENDPOINT` - MinIO S3-compatible storage

### AI/LLM Configuration
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic (Claude) API key
- `GOOGLE_API_KEY` - Google Gemini API key
- `OLLAMA_BASE_URL` - Local Ollama instance URL (optional)

### Security
- `SECRET_KEY` - JWT signing key (generate with: `openssl rand -hex 32`)
- `ALGORITHM` - JWT algorithm (HS256, RS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Default: 30
- `REFRESH_TOKEN_EXPIRE_DAYS` - Default: 7

### Application
- `DEBUG` - Set to false in production
- `CORS_ORIGINS` - Allowed origins (default: http://localhost:3000)
- `API_PREFIX` - Default: /api/v1
- `MAX_UPLOAD_SIZE_MB` - Default: 100

## Accessing the System

After deployment, access at:

- **Admin Dashboard**: `http://<SERVER_IP>` (redirects to /dashboard)
- **API Docs**: `http://<SERVER_IP>/docs` (Swagger UI)
- **Chat Widget**: Include in your site: `<script src="http://<SERVER_IP>/chat-sdk.js"></script>`

Default credentials (change immediately):
- Email: `admin@raze.local`
- Password: `change-me-in-production`

## Managing Services

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f postgres
docker compose logs -f redis
docker compose logs -f qdrant
```

### Restart Services

```bash
# Single service
docker compose restart backend

# All services
docker compose restart

# Hard restart (stop and start)
docker compose down
docker compose up -d
```

### View Service Status

```bash
docker compose ps
```

### Scale Services

```bash
# Scale backend to 2 instances (behind nginx load balancer)
docker compose up -d --scale backend=2
```

## Database Migrations

### Create Migration

```bash
docker compose exec backend alembic revision --autogenerate -m "Description of change"
```

### Run Migrations

```bash
# Up
docker compose exec backend alembic upgrade head

# Down (caution!)
docker compose exec backend alembic downgrade -1

# View history
docker compose exec backend alembic history
```

## Backup and Restore

### Backup Database

```bash
docker compose exec -T postgres pg_dump -U raze raze > backup-$(date +%Y%m%d-%H%M%S).sql
```

### Backup MinIO Data

```bash
docker compose exec -T minio mc mirror minio/raze ./raze-backup/
```

### Restore Database

```bash
cat backup.sql | docker compose exec -T postgres psql -U raze raze
```

### Full Backup Strategy

```bash
#!/bin/bash
BACKUP_DIR=${BACKUP_DIR:-./backups}
DATE=$(date +%Y%m%d-%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
docker compose exec -T postgres pg_dump -U raze raze | gzip > $BACKUP_DIR/db-$DATE.sql.gz

# Backup volumes
tar -czf $BACKUP_DIR/volumes-$DATE.tar.gz \
  /var/lib/docker/volumes/raze_postgres_data \
  /var/lib/docker/volumes/raze_redis_data

# Archive to S3
aws s3 cp $BACKUP_DIR/ s3://your-backup-bucket/raze/$DATE/ --recursive

# Cleanup old backups (keep last 30)
find $BACKUP_DIR -maxdepth 1 -type f -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/db-$DATE.sql.gz"
```

## Adding a Domain (HTTPS with SSL)

### Prerequisites
- Domain name pointing to your server IP
- Certbot and nginx already configured

### Setup SSL

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com

# Update nginx config in docker-compose.yml or nginx.conf
# Add SSL certificate paths
# Point cert to: /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# Point key to: /etc/letsencrypt/live/yourdomain.com/privkey.pem

# Restart nginx
docker compose restart nginx
```

### Sample nginx SSL Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://frontend:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
    }

    location /api/ {
        proxy_pass http://backend:8000;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

## Monitoring and Health Checks

### Health Endpoints

```bash
# Quick check
curl http://localhost/health

# Detailed check
curl http://localhost/api/v1/health
```

### Monitoring with Prometheus (Optional)

```bash
# Metrics endpoint
curl http://localhost/metrics
```

### Set Up Automated Backups

```bash
# Add to crontab
0 2 * * * /path/to/backup.sh

# Edit crontab
crontab -e
```

## Troubleshooting

### Services Won't Start

```bash
# Check for port conflicts
sudo lsof -i :80
sudo lsof -i :5432
sudo lsof -i :6379

# Check Docker daemon
sudo systemctl restart docker

# Review logs
docker compose logs backend
```

### Database Connection Errors

```bash
# Verify database is running and healthy
docker compose exec postgres pg_isready

# Check network
docker compose exec backend ping postgres
```

### Out of Memory

```bash
# Check resource usage
docker compose stats

# Increase Docker memory limit in /etc/docker/daemon.json
{
  "memory": "8g"
}

# Restart Docker
sudo systemctl restart docker
```

### High Disk Usage

```bash
# Check volume sizes
docker volume ls
docker volume inspect raze_postgres_data

# Cleanup unused data
docker system prune -a --volumes
docker image prune -a
```

## Scaling from Single Server to Multi-Server

### Architecture for Multi-Server Deployment

1. **Load Balancer** (HAProxy or Nginx)
   - Distributes requests to multiple backend servers
   - Handles SSL termination

2. **Backend Servers** (multiple instances)
   - Stateless API servers
   - Scales horizontally
   - Each connects to shared database

3. **Database** (separate server or RDS)
   - Single source of truth
   - Replication for HA

4. **Vector DB** (Qdrant cluster)
   - Distributed vector search

5. **Redis Cluster**
   - Session state and caching
   - Replication for HA

6. **MinIO** (object storage)
   - S3-compatible
   - Can be S3 or MinIO distributed

### Kubernetes Deployment

```bash
# Helm chart for RAZE (future)
helm install raze ./helm/raze

# Or kubectl manifests
kubectl apply -f ./k8s/
```

## Performance Tuning

### Database Connection Pool

```python
# In config.py
pool_size=20
max_overflow=0
pool_pre_ping=True
```

### Redis Caching

- Most requests now cached for 1 hour
- Vector search results cached 24 hours
- Memory-backed session cache

### Vector Search Performance

- IVFFlat indexing on pgvector
- Qdrant distributed indexing
- Reranking for relevance

## Security Hardening

### Firewall Rules

```bash
# Allow only SSH, HTTP, HTTPS
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Secrets Management

- Never commit .env file
- Use environment variables in prod
- Rotate keys regularly
- Use external secrets manager (Vault, AWS Secrets Manager)

### Database Security

- Enable password auth
- Restrict network access
- Enable SSL for remote connections

### API Security

- Rate limiting enabled
- CORS configured properly
- SQL injection protection (SQLAlchemy)
- XSS protection (sanitize inputs)

## Support and Updates

### Get Logs for Debugging

```bash
# Collect all logs
docker compose logs > raze-logs-$(date +%Y%m%d).log

# Upload for analysis
```

### Update RAZE

```bash
# Pull latest code
git pull origin main

# Rebuild images
docker compose build --no-cache

# Restart services
docker compose restart
```

## Rollback Procedure

```bash
# Stop current version
docker compose down

# Go to previous version
git checkout <previous-commit>

# Restart with previous images
docker compose up -d
```

## References

- [Docker Documentation](https://docs.docker.com/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [RAZE API Documentation](./API.md)
- [RAZE Architecture](./ARCHITECTURE.md)
