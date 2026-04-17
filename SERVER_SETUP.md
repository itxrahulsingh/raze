# RAZE Enterprise AI OS — Raw Server Setup Guide

Tested on Ubuntu 22.04 LTS. Requires a server with at least 4 vCPU, 8 GB RAM, 50 GB SSD.

---

## 1. Provision the Server

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker Engine
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose plugin
sudo apt-get install -y docker-compose-plugin

# Verify
docker version
docker compose version
```

---

## 2. Clone the Repository

```bash
git clone <your-repo-url> /opt/raze
cd /opt/raze
```

---

## 3. Configure Environment

```bash
cp .env.example .env
nano .env
```

Generate all required secrets and fill in your API keys:

```bash
# Generate secrets inline
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)"
echo "POSTGRES_PASSWORD=$(openssl rand -hex 16)"
echo "REDIS_PASSWORD=$(openssl rand -hex 16)"
echo "MINIO_ROOT_PASSWORD=$(openssl rand -hex 16)"
echo "QDRANT_API_KEY=$(openssl rand -hex 24)"
```

**Required values to set in `.env`:**

| Key | Description |
|-----|-------------|
| `JWT_SECRET_KEY` | 64-char random hex |
| `POSTGRES_PASSWORD` | Strong DB password |
| `REDIS_PASSWORD` | Strong Redis password |
| `MINIO_ROOT_USER` | MinIO admin username |
| `MINIO_ROOT_PASSWORD` | MinIO admin password |
| `QDRANT_API_KEY` | Qdrant auth key |
| `OPENAI_API_KEY` | Your OpenAI key |
| `ANTHROPIC_API_KEY` | (Optional) Anthropic key |
| `NEXT_PUBLIC_API_URL` | `http://<SERVER_IP>/api` |
| `ALLOWED_ORIGINS` | `http://<SERVER_IP>,http://<SERVER_IP>:3000` |
| `DATABASE_URL` | Auto-constructed from Postgres vars |
| `REDIS_URL` | Auto-constructed from Redis vars |

---

## 4. Build and Start All Services

```bash
cd /opt/raze

# Build images (first time takes 5-10 min)
docker compose build

# Start everything
docker compose up -d

# Watch logs
docker compose logs -f
```

Services started:
- `postgres` — PostgreSQL 16 with pgvector
- `redis` — Redis 7 with persistence
- `minio` — Object storage (ports 9000/9001)
- `qdrant` — Vector database (port 6333)
- `backend` — FastAPI on port 8000 (internal)
- `frontend` — Next.js on port 3000 (internal)
- `nginx` — Reverse proxy on port 80 (public)

---

## 5. Verify Health

```bash
# All containers running
docker compose ps

# Backend health
curl http://localhost/health

# Detailed health
curl http://localhost/api/v1/health

# Nginx is proxying correctly
curl http://<SERVER_IP>/health
```

---

## 6. Create First Admin User

The database starts empty. Create a superadmin via psql:

```bash
docker compose exec postgres psql -U raze -d raze -c "
INSERT INTO users (id, email, username, hashed_password, full_name, role, is_active, is_verified)
VALUES (
  gen_random_uuid(),
  'admin@yourcompany.com',
  'admin',
  -- bcrypt hash of 'ChangeMe123!' — replace immediately after first login
  '\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQyCi1O7EUmg7BM.s9nOGIEU.',
  'System Administrator',
  'superadmin',
  true,
  true
);
"
```

Then log in via `POST /api/v1/auth/login` and immediately change your password via `POST /api/v1/auth/change-password`.

---

## 7. MinIO Bucket Setup

```bash
# Access MinIO console at http://<SERVER_IP>:9001
# Login with MINIO_ROOT_USER / MINIO_ROOT_PASSWORD
# Create buckets: raze-documents, raze-exports, raze-media
```

Or via CLI:

```bash
docker compose exec minio mc alias set local http://localhost:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD
docker compose exec minio mc mb local/raze-documents local/raze-exports local/raze-media
```

---

## 8. Run Database Migrations

Migrations run automatically on backend container start. To run manually:

```bash
docker compose exec backend alembic upgrade head
```

---

## 9. Configure Firewall

```bash
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 80/tcp     # HTTP (nginx)
sudo ufw allow 443/tcp    # HTTPS (when SSL is added)
# MinIO console — restrict to admin IP only
sudo ufw allow from <ADMIN_IP> to any port 9001
sudo ufw enable
```

---

## 10. Enable HTTPS (Optional — Requires Domain)

```bash
sudo apt-get install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com

# Update nginx.conf to add SSL server block, then reload:
docker compose exec nginx nginx -s reload
```

---

## 11. Service Management

```bash
# Stop all
docker compose down

# Restart a single service
docker compose restart backend

# View logs for one service
docker compose logs -f backend

# Update after code changes
docker compose build backend
docker compose up -d backend

# Full update (all services)
docker compose pull
docker compose build
docker compose up -d
```

---

## 12. Backups

```bash
# PostgreSQL backup
docker compose exec postgres pg_dump -U raze raze | gzip > backup_$(date +%F).sql.gz

# Redis backup (AOF/RDB already enabled via docker-compose)
docker compose exec redis redis-cli -a $REDIS_PASSWORD BGSAVE

# MinIO: sync bucket to local or S3 via mc mirror
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Backend won't start | Check `docker compose logs backend` — often a missing env var or DB connection failure |
| `CORS` errors in browser | Set `ALLOWED_ORIGINS` in `.env` to include your server IP/domain |
| Streaming chat cuts off | Confirm nginx SSE location block is applied (`nginx -t`) |
| 401 on all requests | Ensure `JWT_SECRET_KEY` is set and consistent across restarts |
| MinIO upload fails | Verify bucket names match `MINIO_BUCKET_DOCUMENTS` in `.env` |
| pgvector extension missing | Custom postgres Dockerfile installs it — rebuild with `docker compose build postgres` |
