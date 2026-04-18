# RAZE Quick Start Guide

**Get RAZE running in under 10 minutes.**

---

## 1️⃣ Prerequisites

```bash
# Check Docker is installed
docker --version
docker compose version

# If not, install from: https://docs.docker.com/engine/install/
```

---

## 2️⃣ Clone & Setup (2 minutes)

```bash
# Clone repository
git clone <your-repo-url> /opt/raze
cd /opt/raze

# Run automated setup
bash setup.sh
```

The script will:
- ✅ Generate secure credentials automatically
- ✅ Build all Docker images
- ✅ Start all services
- ✅ Run database migrations
- ✅ Create admin user

---

## 3️⃣ Access the System

Once setup completes (5-10 minutes), you'll see URLs:

| Service | URL | Notes |
|---------|-----|-------|
| **Admin Dashboard** | `http://<SERVER_IP>/` | Main interface |
| **API Docs** | `http://<SERVER_IP>/docs` | Interactive Swagger |
| **MinIO Console** | `http://<SERVER_IP>:9001/` | File storage |

**Default Login:**
- **Email:** `admin@yourcompany.com`
- **Password:** `ChangeMe123!`
- ⚠️ **Change immediately after first login**

---

## 4️⃣ Verify Everything Works

```bash
# Check all services are running
make health

# Run comprehensive tests
make test

# View logs
make logs
```

---

## 5️⃣ Start Using

### Admin Dashboard
1. Open `http://<SERVER_IP>/`
2. Login with credentials above
3. Go to **Settings** → **AI Configuration**
4. Add your OpenAI API key
5. Upload documents to **Knowledge** → **Upload Source**

### Test Chat API

```bash
# Get auth token
TOKEN=$(curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yourcompany.com","password":"ChangeMe123!"}' \
  | jq -r '.access_token')

# Send a message
curl -X POST http://localhost/api/v1/chat/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello! What can you do?"}' \
  | jq .
```

### Embed Chat in Website

```html
<!-- Add to your website -->
<script>
  window.RazeConfig = {
    apiKey: 'your-sdk-key',
    apiUrl: 'http://your-server/api'
  };
</script>
<script src="http://your-server/raze-widget.js"></script>
```

---

## 📚 Next Steps

- **Full Deployment Guide:** See [SERVER_SETUP.md](SERVER_SETUP.md)
- **Admin Documentation:** Visit `/docs` on your instance
- **Chat SDK Guide:** [Integration examples and API reference](SERVER_SETUP.md#chat-sdk-integration)
- **Troubleshooting:** See [SERVER_SETUP.md#troubleshooting](SERVER_SETUP.md#troubleshooting)

---

## 🛠️ Common Commands

```bash
# Manage services
make up          # Start all
make down        # Stop all
make restart     # Restart all

# Logs & debugging
make logs        # View all logs
make logs-backend  # Backend only
make health      # Quick health check

# Database
make shell-db    # Open database shell
make backup      # Create backup
make test        # Run deployment tests

# Admin setup
make setup-admin    # Create admin user
make generate-secrets # Generate new credentials
```

---

## ⚠️ Important Notes

- **First run takes 5-10 minutes** while Docker builds images
- **Keep `.env` file secret** — contains all credentials
- **Change admin password immediately** after first login
- **Use strong OpenAI/Anthropic API keys** in production

---

## 📞 Troubleshooting

**Services won't start?**
```bash
docker compose logs
```

**Backend crashes?**
```bash
docker compose logs backend
```

**Database errors?**
```bash
docker compose restart postgres
```

**Reset everything** (⚠️ loses data):
```bash
docker compose down
docker volume rm raze_postgres_data
bash setup.sh
```

---

Ready to dive deeper? Check out [SERVER_SETUP.md](SERVER_SETUP.md) for production deployment.

**Happy chatting! 🚀**
