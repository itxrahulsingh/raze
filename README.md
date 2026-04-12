# RAZE Enterprise AI OS

**An Enterprise-Grade AI Operating System for Controlled, Persistent, and Scalable Artificial Intelligence**

![RAZE Architecture](docs/assets/raze-banner.png)

## 🎯 Overview

RAZE is a next-generation **single-tenant enterprise AI platform** that enables organizations to deploy domain-restricted, fully controllable, intelligent AI assistants. It combines:

- **Controlled Intelligence**: Full governance over AI behavior and knowledge
- **Persistent Knowledge**: File-independent knowledge storage with human approval
- **Advanced Memory**: Multi-layer memory system with importance scoring and decay
- **Real-time AI**: Fast streaming responses (<2s for most queries)
- **Tool Execution**: Dynamic API calls and workflow automation
- **Full Observability**: Complete AI decision tracing and metrics
- **Enterprise Security**: JWT auth, role-based access, SSL/TLS ready
- **Scalable Architecture**: From single server to Kubernetes clusters

## 📋 Features

### Core AI Capabilities
- ✅ Multi-LLM Support (OpenAI, Anthropic Claude, Google Gemini, Grok, Ollama)
- ✅ AI Orchestration Engine with intent detection and dynamic decision-making
- ✅ Advanced Memory System (context, user, operational, knowledge)
- ✅ Semantic Knowledge Search (<200ms latency)
- ✅ Tool/Action Engine for API execution and automation
- ✅ Response Streaming with Server-Sent Events
- ✅ Tool Call Planning and Execution

### Knowledge Management
- ✅ Multi-format Ingestion (PDF, DOCX, TXT, Web URLs)
- ✅ Intelligent Text Chunking
- ✅ Admin Approval Workflow
- ✅ Persistent Knowledge Mode (file-independent)
- ✅ Deduplication and Versioning
- ✅ Source Traceability and Audit Logs

### Administration & Observability
- ✅ Admin Control Panel (Next.js dashboard)
- ✅ AI Decision Logging and Replay
- ✅ Real-time Analytics and Usage Metrics
- ✅ User Session Tracking
- ✅ System Health Monitoring
- ✅ Cost Tracking (per-token, per-model)

### SDK & Embedding
- ✅ Embeddable Chat Widget (one script tag)
- ✅ Session-based or API Key Auth
- ✅ Streaming Responses
- ✅ Customizable Theme
- ✅ ~15KB gzipped bundle

### Security & Compliance
- ✅ JWT-based Authentication
- ✅ Role-Based Access Control (superadmin, admin, viewer)
- ✅ API Key Management
- ✅ Rate Limiting
- ✅ Encryption-ready (AES-256, TLS)
- ✅ Audit Logging
- ✅ CORS Configuration

## 🏗️ Architecture

### High-Level Components

```
Internet/Users
    ↓
Nginx Gateway (Port 80)
    ↓
├─ Backend API (FastAPI, Port 8000)
│  ├─ AI Orchestration Engine
│  ├─ Multi-LLM Router
│  ├─ Memory Engine
│  ├─ Knowledge Engine
│  ├─ Tool Engine
│  ├─ Vector Search
│  └─ API Routes (auth, chat, knowledge, tools, admin, analytics)
│
├─ Frontend (Next.js, Port 3000)
│  ├─ Admin Dashboard
│  ├─ Knowledge Management
│  ├─ Conversation Monitoring
│  └─ Analytics & Settings
│
└─ Data Layer
   ├─ PostgreSQL 16 (+ pgvector for embeddings)
   ├─ Qdrant (Vector Database)
   ├─ Redis 7 (Cache + Sessions)
   └─ MinIO (S3-compatible Storage)
```

### Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0 async |
| **Frontend** | Next.js 14, React 18, TypeScript, Tailwind CSS |
| **Chat SDK** | TypeScript, Vanilla JS (no dependencies) |
| **Database** | PostgreSQL 16 + pgvector extension |
| **Vector DB** | Qdrant or pgvector (built-in fallback) |
| **Cache** | Redis 7 |
| **Storage** | MinIO (S3-compatible) |
| **Gateway** | Nginx 1.25+ |
| **Orchestration** | Docker Compose v2 |
| **LLM Support** | OpenAI, Anthropic, Google Gemini, Ollama |

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose v2
- 4 CPU cores, 8GB RAM, 100GB storage (minimum)
- openssl, curl installed

### Single-Click Setup (Recommended)

```bash
cd /Users/rahul/Development/raze
bash setup.sh
```

The script will:
1. Detect your OS and install Docker if needed
2. Generate security credentials (JWT secret, database passwords, API keys)
3. Start all services (backend, frontend, database, cache, vector DB, storage)
4. Run database migrations
5. Create default admin user
6. Print access URLs and credentials

### Manual Setup

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your settings (API keys, database passwords, etc.)

# 2. Start services
docker compose up -d

# 3. Wait for services to be healthy
sleep 30

# 4. Run migrations
docker compose exec backend alembic upgrade head

# 5. Create admin user (optional)
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

asyncio.run(create_admin())
"

# 6. Access the system
# Admin Dashboard: http://localhost/dashboard
# API Docs: http://localhost/docs
# Default login: admin@raze.local / change-me-in-production
```

## 📊 Accessing RAZE

After successful deployment:

| Component | URL | Purpose |
|-----------|-----|---------|
| Admin Dashboard | `http://<SERVER_IP>/dashboard` | System administration |
| API Documentation | `http://<SERVER_IP>/docs` | Swagger UI interactive docs |
| API Base | `http://<SERVER_IP>/api/v1` | REST API endpoints |
| Chat Widget SDK | `http://<SERVER_IP>/chat-sdk.js` | Embeddable widget |

**Default Admin Credentials**:
- Email: `admin@raze.local`
- Password: `change-me-in-production`

⚠️ **Change immediately after first login!**

## 📖 Documentation

- **[DEPLOYMENT.md](./docs/DEPLOYMENT.md)** - Complete deployment guide, scaling, SSL setup
- **[API.md](./docs/API.md)** - Full REST API reference with examples
- **[ARCHITECTURE.md](./docs/ARCHITECTURE.md)** - Detailed system architecture and data flows
- **[Chat SDK Example](./chat-sdk/example/index.html)** - SDK usage guide

## 💬 Using the Chat Widget

### In Your Website
```html
<script src="http://your-raze-server/chat-sdk.js"></script>
<script>
  RazeChat.init({
    apiUrl: 'http://your-raze-server',
    theme: {
      primaryColor: '#7C3AED',
    },
    botName: 'My AI Assistant',
    position: 'bottom-right'
  });
</script>
```

### API Reference
See [SDK Endpoints in API.md](./docs/API.md#sdk-endpoints)

## 🛠️ Configuration

### Environment Variables

Create a `.env` file (copy from `.env.example`):

```bash
# Core
DEBUG=false
SECRET_KEY=<generate-with: openssl rand -hex 32>

# Database
DATABASE_URL=postgresql://raze:password@postgres:5432/raze
REDIS_URL=redis://:password@redis:6379/0

# LLMs (get keys from their platforms)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Storage
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Vector DB
QDRANT_URL=http://qdrant:6333

# Application
CORS_ORIGINS=http://localhost:3000,http://localhost
MAX_UPLOAD_SIZE_MB=100

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60
```

## 📝 Project Structure

```
raze/
├── backend/                    # FastAPI backend application
│   ├── app/
│   │   ├── main.py            # FastAPI app entry
│   │   ├── config.py          # Configuration
│   │   ├── database.py        # SQLAlchemy + PostgreSQL
│   │   ├── models/            # 14 database models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── api/v1/            # REST API routes (8 modules)
│   │   └── core/              # AI engines (8 modules)
│   ├── alembic/               # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                   # Next.js 14 admin dashboard
│   ├── src/
│   │   ├── app/               # App Router pages
│   │   ├── components/        # React components
│   │   └── lib/               # Utilities
│   ├── Dockerfile
│   └── package.json
│
├── chat-sdk/                   # Embeddable chat widget
│   ├── src/
│   │   └── index.ts           # Main SDK file
│   ├── example/
│   │   └── index.html         # Usage example
│   ├── vite.config.ts
│   └── package.json
│
├── nginx/                      # Nginx reverse proxy config
│   └── nginx.conf
│
├── docs/                       # Documentation
│   ├── API.md                 # REST API docs
│   ├── DEPLOYMENT.md          # Deployment guide
│   └── ARCHITECTURE.md        # Architecture docs
│
├── docker-compose.yml         # Single-server orchestration
├── .env.example               # Environment template
├── setup.sh                   # Single-click setup
├── Makefile                   # Development commands
└── README.md                  # This file
```

## 🚀 Development Commands

### Using Makefile

```bash
# Setup and start
make setup
make up

# View logs
make logs
make logs-backend

# Database
make migrate
make shell-db

# Stop
make down

# Clean up
make clean
```

### Or use Docker Compose directly

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f backend

# Run migrations
docker compose exec backend alembic upgrade head

# Shell into backend
docker compose exec backend bash
docker compose exec backend python

# Shell into database
docker compose exec postgres psql -U raze
```

## 📊 Monitoring & Observability

### Health Checks

```bash
# Quick liveness
curl http://localhost/health

# Detailed health
curl http://localhost/api/v1/health

# Prometheus metrics
curl http://localhost/metrics
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f postgres
docker compose logs -f redis
```

### Admin Dashboard
Visit `http://localhost/dashboard` to view:
- System health
- Usage metrics
- AI decision logs
- Conversation analytics
- Model performance

## 🔐 Security

### Important
- ⚠️ Change default admin password immediately
- ⚠️ Generate new JWT secret for production (`openssl rand -hex 32`)
- ⚠️ Use strong database passwords
- ⚠️ Enable HTTPS (see DEPLOYMENT.md for SSL setup)
- ⚠️ Restrict CORS origins to your domains
- ⚠️ Never commit .env file to version control

### Best Practices
- Rotate API keys regularly
- Monitor rate limits and adjust as needed
- Enable audit logging
- Use managed databases for production
- Set up automated backups
- Use environment variables for all secrets

## 📈 Performance

### Expected Metrics
- Chat Response Time: <2 seconds
- Knowledge Search: <200ms
- API Response: <500ms  
- Concurrent Users: 100+ (single server), 1000+ (scaled)
- Storage Efficiency: 10-50 MB per 10K knowledge chunks

### Scaling Path
1. **Single Server** (current): 50-100 concurrent users
2. **Multi-Server**: 100-1000 concurrent users
3. **Kubernetes**: 1000+ concurrent users

See [DEPLOYMENT.md](./docs/DEPLOYMENT.md#scaling-from-single-server-to-multi-server) for scaling guide.

## 🤝 API Usage Examples

### Authentication
```bash
curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@raze.local","password":"password"}'
```

### Chat Message
```bash
curl -X POST http://localhost/api/v1/chat/message \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"sess-123","message":"Hello RAZE"}'
```

### Upload Knowledge
```bash
curl -X POST http://localhost/api/v1/knowledge/sources \
  -H "Authorization: Bearer <token>" \
  -F "file=@document.pdf"
```

### Stream Chat Response (SSE)
```bash
curl -N -X POST http://localhost/api/v1/chat/stream \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"sess-123","message":"Explain AI"}'
```

Full API documentation: [docs/API.md](./docs/API.md)

## 🐛 Troubleshooting

### Services won't start
```bash
# Check for port conflicts
lsof -i :80
lsof -i :5432
lsof -i :6379

# Check Docker daemon
systemctl restart docker

# View detailed logs
docker compose logs backend
```

### Database connection errors
```bash
docker compose exec postgres pg_isready
docker compose exec backend ping postgres
```

### Out of memory
```bash
docker compose stats
# Increase Docker memory in /etc/docker/daemon.json
```

See [DEPLOYMENT.md#troubleshooting](./docs/DEPLOYMENT.md#troubleshooting) for more.

## 📞 Support

- 📖 **Documentation**: See `/docs` folder
- 📧 **API Docs**: `http://<SERVER_IP>/docs` (interactive Swagger UI)
- 🐛 **Issues**: Check logs with `docker compose logs -f`
- 💡 **Best Practices**: See [DEPLOYMENT.md](./docs/DEPLOYMENT.md)

## 📄 License

Proprietary - RAZE Enterprise AI OS

## 🎯 Next Steps

1. **Deploy**: Run `bash setup.sh` to get started
2. **Configure**: Update `.env` with your API keys
3. **Add Knowledge**: Upload documents via admin dashboard
4. **Create Tools**: Define APIs for AI to execute
5. **Embed Widget**: Add chat widget to your website
6. **Monitor**: Track metrics in analytics dashboard
7. **Scale**: Move to multi-server when ready

---

Built with ❤️ for enterprises that need intelligent, controlled, and observable AI.

**RAZE - Enterprise AI Operating System**
