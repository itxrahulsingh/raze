# RAZE Enterprise AI OS — Production Installation Guide

**Complete setup, configuration, and deployment in one guide.**

---

## Prerequisites

- **Server:** Ubuntu 20.04+, Debian 11+, or macOS 12+
- **Hardware:** 4+ vCPU, 8+ GB RAM, 50+ GB SSD
- **Software:** Docker 20.10+, Docker Compose v2+
- **AI Models:** Ollama (included in docker-compose, free) or OpenAI/Anthropic API keys (optional)
- **Network:** Port 80, 443 accessible (for HTTP/HTTPS)

---

## LLM Models & Configuration

RAZE supports **self-hosted and cloud AI models**. Choose your deployment style:

### Models Overview at a Glance

**You have 3 deployment options:**

1. **FREE ONLY** (Ollama) – Zero cost, complete privacy, no API keys needed
2. **HYBRID** (Ollama + Cloud) – Free by default, cloud for premium tasks
3. **CLOUD ONLY** – Maximum quality, pay per use

**Quick Decision:**
- **Budget / Private** → Use Mistral (Ollama)
- **Quality Priority** → Use GPT-4o or Claude-Opus
- **Balanced** → Use Mistral + GPT-4o-mini fallback (recommended)

---

### Option 1: Ollama (Self-Hosted – PRIMARY) ⭐ RECOMMENDED

**Free, private, on-premise AI. No external API costs or data leaving your server.**

#### Available Ollama Models – Detailed Comparison

**All models are FREE, run locally, and keep your data private.**

##### 1. **Mistral 7B** ⭐ RECOMMENDED
- **Download Size:** 4.1 GB
- **Memory Required:** 6-8 GB RAM
- **Context Window:** 32,000 tokens
- **Inference Speed:** ~15-20 tokens/sec
- **Quality:** ★★★★☆ (Excellent for general tasks)
- **Training Date:** April 2023
- **Best For:** General-purpose chat, Q&A, summarization, code assistance
- **Strengths:** Fast, accurate, balanced performance
- **Weaknesses:** Not specialized for any particular task
- **Use Cases:** Chatbots, customer support, general knowledge questions
- **Cost:** FREE

**Example Query Times:**
- Simple question: 2-3 seconds
- Medium response: 5-8 seconds
- Long detailed answer: 15-20 seconds

---

##### 2. **Llama 3.2** (3.8B)
- **Download Size:** 2.0 GB
- **Memory Required:** 4-6 GB RAM
- **Context Window:** 8,192 tokens
- **Inference Speed:** ~25-30 tokens/sec (Fastest)
- **Quality:** ★★★☆☆ (Good for simple tasks)
- **Training Date:** April 2024
- **Best For:** Edge devices, low-resource servers, high-throughput scenarios
- **Strengths:** Smallest model, fastest inference, excellent mobile/edge deployment
- **Weaknesses:** Limited context window, lower quality than 7B models
- **Use Cases:** Real-time chat, IoT devices, high-volume simple queries
- **Cost:** FREE

**When to Use:** When speed matters more than accuracy, or on resource-constrained hardware

---

##### 3. **Llama 2** (7B)
- **Download Size:** 3.8 GB
- **Memory Required:** 6-8 GB RAM
- **Context Window:** 4,096 tokens
- **Inference Speed:** ~15-20 tokens/sec
- **Quality:** ★★★★☆ (Excellent, most mature)
- **Training Date:** July 2023
- **Best For:** Production-stable deployments, long-term reliability
- **Strengths:** Well-tested in production, good quality-speed tradeoff
- **Weaknesses:** Smaller context window, older training data
- **Use Cases:** Enterprise deployments, customer service, documentation Q&A
- **Cost:** FREE

**Why Choose:** If you need maximum stability and community support

---

##### 4. **Neural-Chat 7B**
- **Download Size:** 3.8 GB
- **Memory Required:** 6-8 GB RAM
- **Context Window:** 8,192 tokens
- **Inference Speed:** ~15-18 tokens/sec
- **Quality:** ★★★★☆ (Excellent for conversation)
- **Training Date:** 2024
- **Best For:** Conversational AI, chat applications, user engagement
- **Strengths:** Fine-tuned for dialogue, natural responses, engaging tone
- **Weaknesses:** Not optimized for technical/code tasks
- **Use Cases:** Customer support chatbots, virtual assistants, conversational interfaces
- **Cost:** FREE

**Example Strength:** Produces more human-like conversational responses

---

##### 5. **OpenChat 7B**
- **Download Size:** 3.8 GB
- **Memory Required:** 6-8 GB RAM
- **Context Window:** 8,192 tokens
- **Inference Speed:** ~15-20 tokens/sec
- **Quality:** ★★★★☆ (High-quality open-source)
- **Training Date:** 2024
- **Best For:** Balance of quality and efficiency, no proprietary concerns
- **Strengths:** Excellent reasoning, good instruction-following, fully open-source
- **Weaknesses:** Slightly slower than Mistral
- **Use Cases:** Complex reasoning, instruction-following, detailed analysis
- **Cost:** FREE

**Open-Source Advantage:** Complete transparency, no vendor lock-in, full control

---

##### 6. **Phi 3** (3.8B)
- **Download Size:** 2.3 GB
- **Memory Required:** 4-6 GB RAM
- **Context Window:** 4,096 tokens
- **Inference Speed:** ~25-30 tokens/sec (Very fast)
- **Quality:** ★★★☆☆ (Good for lightweight tasks)
- **Training Date:** April 2024
- **Best For:** Lightweight edge deployment, mobile, IoT
- **Strengths:** Extremely small, very fast, Microsoft-backed quality
- **Weaknesses:** Small context window, limited capability
- **Use Cases:** Mobile apps, edge devices, real-time responses
- **Cost:** FREE

**When to Use:** On Raspberry Pi, mobile, or when response time is critical

---

##### 7. **Orca Mini** (3.8B)
- **Download Size:** 1.8 GB
- **Memory Required:** 3-4 GB RAM
- **Context Window:** 4,096 tokens
- **Inference Speed:** ~25-30 tokens/sec
- **Quality:** ★★☆☆☆ (Acceptable for simple tasks)
- **Training Date:** 2023
- **Best For:** Extremely resource-constrained environments
- **Strengths:** Tiniest model, minimal dependencies
- **Weaknesses:** Lower quality, outdated training
- **Use Cases:** Embedded systems, extreme edge cases
- **Cost:** FREE

**When to Use:** Only if other models won't fit on your hardware

---

#### Quick Model Selection Guide

```
Choosing the right Ollama model:

"I want the best balance" 
  → Use: MISTRAL ⭐
  → Quality: Excellent | Speed: Fast | Memory: 6-8GB

"I need maximum quality & don't mind waiting"
  → Use: OPENCHAT or NEURAL-CHAT
  → Quality: Excellent+ | Speed: Normal | Memory: 6-8GB

"My server has 4GB RAM or less"
  → Use: LLAMA3.2 or PHI3
  → Quality: Good | Speed: Very Fast | Memory: 4-6GB

"I need responses in <1 second"
  → Use: LLAMA3.2 or PHI3
  → Quality: Good | Speed: Very Fast | Memory: 4-6GB

"I need production stability"
  → Use: LLAMA2
  → Quality: Excellent | Speed: Fast | Memory: 6-8GB

"I need to serve 100+ concurrent users"
  → Use: LLAMA3.2 (fast inference = more throughput)
  → Quality: Good | Speed: Very Fast | Memory: 4-6GB
```

#### Quick Ollama Setup

```bash
# Option A: Direct installation
# macOS: brew install ollama
# Linux: curl https://ollama.ai/install.sh | sh
# Windows: https://ollama.ai/download

# Option B: Docker (recommended for servers)
docker run -d --name ollama -v ollama:/root/.ollama -p 11434:11434 ollama/ollama

# Pull a model (mistral recommended)
docker exec ollama ollama pull mistral

# Verify it's working
curl http://localhost:11434/api/generate -d '{"model":"mistral","prompt":"Hello"}'
```

#### Configure in .env

```bash
# Enable Ollama (primary LLM)
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_DEFAULT_MODEL=mistral

# Routing strategy: cost | performance | balanced (default)
LLM_ROUTING_STRATEGY=balanced

# Default provider when none specified
DEFAULT_LLM_PROVIDER=ollama
```

### Option 2: Cloud AI Models (Optional – Use as Fallback/Premium)

For specialized tasks, higher accuracy, or when you need maximum capability, add cloud providers. RAZE automatically routes to them when needed.

#### **OpenAI (ChatGPT – Most Capable)**

```bash
# Get key from https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-key-here
OPENAI_DEFAULT_MODEL=gpt-4o-mini
```

##### Available OpenAI Models

| Model | Quality | Speed | Context | Cost/1K Tokens | Best For |
|-------|---------|-------|---------|---|----------|
| **gpt-4o** | ★★★★★ (Best) | ⚡ | 128K | $0.005 in / $0.015 out | Mission-critical, reasoning |
| **gpt-4o-mini** | ★★★★☆ | ⚡⚡ | 128K | $0.00015 in / $0.0006 out | Balanced, most popular |
| **gpt-4-turbo** | ★★★★★ | ⚡ | 128K | $0.01 in / $0.03 out | Complex tasks, long context |
| **gpt-3.5-turbo** | ★★★☆☆ | ⚡⚡⚡ | 4K | $0.0005 in / $0.0015 out | Budget-conscious |
| **o1** | ★★★★★ | ⚡ | 128K | $0.015 in / $0.060 out | Deep reasoning, research |
| **o1-mini** | ★★★★☆ | ⚡⚡ | 128K | $0.003 in / $0.012 out | Fast reasoning |

**Recommendation:** Use gpt-4o-mini as fallback when Ollama unavailable

---

#### **Anthropic Claude (Best Reasoning & Long Context)**

```bash
# Get key from https://console.anthropic.com
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_DEFAULT_MODEL=claude-3-5-sonnet-20241022
```

##### Available Claude Models

| Model | Quality | Speed | Context | Cost/1M Tokens | Best For |
|-------|---------|-------|---------|---|----------|
| **claude-opus-4-5** | ★★★★★ (Best reasoning) | ⚡ | 200K | $15 in / $75 out | Complex reasoning, research |
| **claude-sonnet-4-5** | ★★★★☆ | ⚡⚡ | 200K | $3 in / $15 out | General-purpose, balanced ✓ |
| **claude-haiku-3-5** | ★★★☆☆ | ⚡⚡⚡ | 200K | $0.25 in / $1.25 out | Fast, budget-friendly |

**Claude Strengths:**
- Best at long-form content generation
- Excellent at reasoning and analysis
- Lowest error rates on complex tasks
- Best 200K context window among all models

**Recommendation:** Use claude-sonnet-4-5 for balanced fallback

---

#### **Google Gemini (Multimodal – Image Support)**

```bash
# Get key from https://ai.google.dev
GOOGLE_API_KEY=your-gemini-key
```

##### Available Gemini Models

| Model | Quality | Speed | Context | Cost/1M Tokens | Best For |
|-------|---------|-------|---------|---|----------|
| **gemini-2.0-flash** | ★★★★★ | ⚡⚡⚡ | 1M | $0.075 in / $0.30 out | Latest, images, documents |
| **gemini-1.5-pro** | ★★★★★ | ⚡⚡ | 2M | $1.25 in / $5 out | Ultra-long context, files |
| **gemini-1.5-flash** | ★★★★☆ | ⚡⚡⚡ | 1M | $0.075 in / $0.30 out | Fast, images, cheap |

**Gemini Strengths:**
- **Multimodal:** Can analyze images, PDFs, documents, videos
- **Ultra-long context:** 1M-2M tokens = entire books at once
- **Very fast:** Exceptional streaming performance
- **Cost-effective:** Lowest cost at massive scale

**Best For:** Document analysis, image understanding, multi-page processing

**Recommendation:** Use gemini-2.0-flash for fast multimodal tasks

---

#### **Grok (X.AI – Cutting Edge)**

```bash
# Get key from X.AI platform (https://x.ai)
GROK_API_KEY=your-grok-key
```

##### Grok Model Details

| Aspect | Details |
|--------|---------|
| **Quality** | ★★★★☆ (Very good, newer) |
| **Speed** | ⚡⚡ (Fast) |
| **Context** | 128K tokens |
| **Cost** | $0.003 in / $0.015 out per 1K tokens |
| **Latest** | Trained on real-time data |
| **Best For** | Current events, real-time information, latest knowledge |

**Grok Strengths:**
- Real-time knowledge cutoff (not trained on old data)
- Can answer questions about current events
- Good for news analysis, recent developments

**Best For:** When you need the latest information and Ollama/GPT models are too outdated

---

### Complete Model Comparison Matrix

```
┌─────────────────────────────────────────────────────────────────┐
│                    MODEL SELECTION MATRIX                       │
├─────────────────────────────────────────────────────────────────┤
│ FREE/LOCAL (Ollama)                                             │
│ ─────────────────────────────────────────────────────────────── │
│ ✓ Mistral 7B        → Best all-around FREE option              │
│ ✓ Llama 3.2         → Fastest, least RAM needed                │
│ ✓ Neural-Chat       → Best for conversations                   │
│ ✓ OpenChat          → Best reasoning quality FREE              │
│                                                                 │
│ CLOUD (As Fallback/Premium)                                    │
│ ─────────────────────────────────────────────────────────────── │
│ $ GPT-4o-mini       → Best cost/quality for fallback           │
│ $ Claude Sonnet     → Best reasoning, long context             │
│ $ Gemini 2.0 Flash  → Best for images/documents               │
│ $$$ GPT-4o          → Maximum capability                       │
│ $$$ Claude Opus     → Best reasoning tasks                     │
│ $$$$ Gemini 1.5 Pro → 2M token context, documents             │
│                                                                 │
│ STRATEGY RECOMMENDATIONS                                        │
│ ─────────────────────────────────────────────────────────────── │
│ Cost-First:    Use Mistral (FREE) → GPT-3.5 ($) → Haiku       │
│ Quality-First: Use GPT-4o → Claude-Opus → Gemini-Pro           │
│ Balanced:      Use Mistral (FREE) → GPT-4o-mini ($) ← DEFAULT │
│ Real-time:     Use Grok for current events, fallback Mistral   │
│ Images/Docs:   Use Gemini-2.0-Flash, fallback Mistral          │
└─────────────────────────────────────────────────────────────────┘
```

### How to Choose Your Primary Model

**Question 1: Is cost a concern?**
- YES → Use Mistral (FREE, excellent quality)
- NO → Use GPT-4o or Claude-Opus

**Question 2: Do you need images/documents?**
- YES → Use Gemini (multimodal), fallback Mistral
- NO → Use Mistral or GPT-4o-mini

**Question 3: How much RAM available?**
- < 6GB → Use Llama3.2 or Phi3
- 6-8GB → Use Mistral, Llama2, or Neural-Chat
- > 8GB → Use any Ollama model or cloud

**Question 4: Need latest information (real-time)?**
- YES → Use Grok, fallback Mistral
- NO → Use Mistral or Claude-Sonnet

**Question 5: Reasoning/analysis tasks?**
- YES → Use Claude-Opus or OpenChat, fallback Mistral
- NO → Use Mistral or GPT-4o-mini

---

### Model Recommendation by Use Case

| Use Case | Recommended | Why |
|----------|---|---|
| **Customer Support Chat** | Mistral + Neural-Chat | Fast, conversational, FREE |
| **Document Q&A** | Gemini 2.0 Flash | Multimodal, document processing |
| **Code Generation** | GPT-4o or Mistral | Best code understanding |
| **Long Documents** | Claude Sonnet (200K) | Huge context window |
| **Real-time News** | Grok | Real-time knowledge cutoff |
| **Budget Startup** | Mistral | Zero cost, excellent quality |
| **Enterprise/Mission-Critical** | GPT-4o + Claude-Opus | Maximum reliability |
| **On-Premise/Private** | Mistral + Neural-Chat | Complete data privacy |
| **Mobile/Edge Devices** | Llama3.2 or Phi3 | Tiny, fast, minimal RAM |
| **High Throughput (100+/sec)** | Llama3.2 | Fastest inference |

### LLM Routing Logic

RAZE automatically selects the best model based on your strategy:

```
User Query arrives
    ↓
LLMRouter calculates:
  • Context size needed
  • Budget constraints
  • Provider availability
    ↓
Selects best match:
  • Cost strategy → ollama/mistral ✓ (free)
  • Performance → gpt-4o or claude-opus
  • Balanced → neural-chat or gpt-4o-mini
    ↓
Sends to provider adapter
    ↓
Streams response token-by-token
```

**Routing Strategies:**

| Strategy | Behavior | Best For |
|----------|----------|----------|
| **cost** | Cheapest model that fits | Budget-conscious, high-volume |
| **performance** | Highest quality model | Mission-critical accuracy |
| **balanced** | Optimal quality/cost ratio | Most deployments (recommended) |

### Frequently Asked Questions about Models

**Q: Will Mistral work as well as ChatGPT?**
A: For most tasks (70-80%), yes. Mistral handles general Q&A, summarization, chat excellently. For specialized tasks (code, reasoning, analysis), GPT-4o is 10-20% better. RAZE lets you use both.

**Q: How much internet bandwidth does Mistral use?**
A: Zero. Models run 100% locally. No data leaves your server. Perfect for privacy-sensitive applications.

**Q: Can I switch models without restarting?**
A: Yes. Edit `.env`, change `OLLAMA_DEFAULT_MODEL=llama3.2`, run `docker compose restart backend`. Takes 5 seconds.

**Q: What if Ollama crashes? Will the system fail?**
A: No. If Ollama is down and you've configured OpenAI/Claude, RAZE automatically fails over to cloud models with zero code changes.

**Q: Do I need to buy all these models?**
A: No. Start free with Mistral. Add cloud models only if you need them. RAZE keeps them optional.

**Q: Which model should I use for customer support?**
A: **Mistral or Neural-Chat.** Both free, fast, good at conversational tone. Can handle 10K+ customers without API costs.

**Q: Can I use Mistral for code generation?**
A: Yes, it's decent (80% accuracy). But GPT-4o is better (95% accuracy). Use Mistral for simple code, GPT-4o for complex.

**Q: How long does it take to pull a model?**
A: 2-10 minutes depending on model size and internet speed:
  - Llama3.2 (2.0GB) → 2-3 minutes
  - Mistral (4.1GB) → 4-5 minutes  
  - Neural-Chat (3.8GB) → 4-5 minutes

**Q: Can I run Mistral on a Raspberry Pi?**
A: Not Mistral (needs 6-8GB RAM). Use Llama3.2 or Phi3 on Pi (needs 4GB minimum).

**Q: What's the difference between gpt-4o and gpt-4o-mini?**
A: 
- **gpt-4o:** Best quality, ~$0.015 per 1K output tokens
- **gpt-4o-mini:** 85% quality, ~$0.0006 per 1K output tokens (25x cheaper)
Use mini for fallback unless you need maximum accuracy.

**Q: Should I use Claude-Opus or GPT-4o?**
A: **For most tasks: GPT-4o** (better at code, faster, cheaper)  
**For reasoning/analysis: Claude-Opus** (better long-form writing, reasoning)
RAZE supports both, use both if budget allows.

**Q: How do I know which model RAZE is using?**
A: Check logs: `docker compose logs backend | grep "llm_routing"` shows routing decisions in real-time.

**Q: Can I configure different models for different tasks?**
A: Yes, via the routing strategy. Set `LLM_ROUTING_STRATEGY=balanced` and RAZE automatically:
- Uses Mistral for simple questions (free)
- Falls back to GPT-4o-mini for complex queries (when needed)

**Q: What if I run out of Ollama disk space?**
A: Models are stored in `ollama_data/` volume. If full, delete unused models:
```bash
docker compose exec ollama ollama rm llama3.2
```

**Q: Can I use multiple Ollama models simultaneously?**
A: Yes, load all via `ollama pull model_name`. But only one runs at a time. Switch in `.env` or via admin dashboard.

**Q: Is Gemini good for images?**
A: **Yes, best for images.** Can analyze PDFs, screenshots, charts, documents. Mistral can't do images.

**Q: What's the learning curve for switching models?**
A: ~5 minutes. Change one line in `.env`, restart backend. That's it.

**Q: Do I need to fine-tune models?**
A: No. RAZE provides "prompt engineering" features where you can inject custom instructions without model fine-tuning.

**Q: Can I use a different vector DB instead of Qdrant?**
A: Currently RAZE ships with Qdrant. Vector DB is separate from LLM choice, so you can:
- Use any LLM (Ollama, OpenAI, etc.) with Qdrant
- We plan to support Pinecone, Weaviate in future releases

**Q: What's the max context I can send?**
A: Depends on model:
- Mistral: 32K tokens (~12,000 words)
- Claude: 200K tokens (~60,000 words)
- Gemini Pro: 2M tokens (~600,000 words)
RAZE automatically splits larger documents.

---

## One-Command Installation

```bash
# 1. Clone repo
git clone <your-repo-url> /opt/raze
cd /opt/raze

# 2. Generate credentials
bash scripts/generate-secrets.sh > .env.secrets

# 3. Create .env (edit with your settings)
cp .env.example .env
# Secrets are already filled. Add SERVER_IP and any API keys

# 4. Deploy everything
docker compose up -d
sleep 30

# 5. Pull Ollama models (first time only, 2-5 minutes)
docker compose exec ollama ollama pull mistral

# 6. Initialize database
docker compose exec backend alembic upgrade head
bash scripts/setup-admin.sh

# 7. Verify
bash scripts/test-deployment.sh

# Access: http://your-server-ip/
# Admin: admin@yourcompany.com / ChangeMe123!
```

**That's it. 20-25 minutes and you're live with free, private AI.**

---

## Step-by-Step Installation

### 1. Prepare Server

```bash
# SSH into server
ssh root@your-server-ip

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker (if needed)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

### 2. Clone Repository

```bash
# Create RAZE directory
mkdir -p /opt/raze
cd /opt/raze

# Clone repo
git clone <your-repo-url> .

# Make scripts executable
chmod +x scripts/*.sh

# Verify setup
ls -la
# Expected: docker-compose.yml, scripts/, backend/, frontend/
```

### 3. Configure Environment

```bash
# Copy template
cp .env.example .env

# Generate secure credentials
bash scripts/generate-secrets.sh

# Edit .env with your settings
nano .env
```

**Critical values in .env:**

```bash
# Server Configuration
SERVER_IP=192.168.1.100          # Your server IP
ENVIRONMENT=production
DEBUG=false

# Database
POSTGRES_PASSWORD=<from-generate-secrets>
DATABASE_URL=postgresql+asyncpg://raze:${POSTGRES_PASSWORD}@postgres:5432/raze

# Redis
REDIS_PASSWORD=<from-generate-secrets>
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# JWT & Security
JWT_SECRET_KEY=<from-generate-secrets>

# LLM Configuration (Ollama is primary, others optional)
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_DEFAULT_MODEL=mistral
DEFAULT_LLM_PROVIDER=ollama
LLM_ROUTING_STRATEGY=balanced

# Optional: Add cloud providers for higher quality/fallback
# OPENAI_API_KEY=sk-...              # Optional for GPT models
# ANTHROPIC_API_KEY=sk-ant-...       # Optional for Claude

# MinIO / File Storage
STORAGE_BACKEND=local              # or "minio"
MINIO_ROOT_PASSWORD=<from-generate-secrets>
MINIO_BUCKET_DOCUMENTS=raze-documents

# Vector Database
QDRANT_API_KEY=<from-generate-secrets>

# Frontend
NEXT_PUBLIC_API_URL=http://${SERVER_IP}/api
NEXT_PUBLIC_WS_URL=ws://${SERVER_IP}/ws

# CORS / Allowed Origins
ALLOWED_ORIGINS=http://${SERVER_IP},http://${SERVER_IP}:3000,http://localhost
```

### 4. Start All Services

```bash
# Build and start everything
docker compose up -d

# Watch logs (Ctrl+C to stop)
docker compose logs -f

# Expected: All services start within 30-60 seconds
```

**Important: Pull Ollama Models (happens once, takes 2-5 minutes)**

```bash
# Wait 30 seconds for Ollama to be healthy
sleep 30

# Pull default model (mistral - 4.1GB)
docker compose exec ollama ollama pull mistral

# Optional: Pull additional models for switching
docker compose exec ollama ollama pull llama3.2
docker compose exec ollama ollama pull neural-chat

# Verify models are installed
docker compose exec ollama ollama list
```

Models are downloaded once and persist in `ollama_data/` volume. Subsequent restarts are instant.

### 5. Initialize Database

```bash
# Wait for backend to be healthy (30-60 seconds)
# Then run migrations
docker compose exec backend alembic upgrade head

# Verify
docker compose exec postgres psql -U raze -d raze -c "SELECT version();"
```

### 6. Create Admin User

```bash
bash scripts/setup-admin.sh

# Output will show:
# Admin user created
# Email: admin@yourcompany.com
# Password: ChangeMe123!
```

### 7. Verify Installation

```bash
bash scripts/test-deployment.sh

# Expected output: All tests PASS ✓
# If any fail, check: docker compose logs service-name
```

---

## Access Your Platform

After successful installation:

| Service | URL | Purpose |
|---------|-----|---------|
| **Admin Dashboard** | `http://<SERVER_IP>/` | Manage AI, knowledge, users |
| **Chat API** | `http://<SERVER_IP>/api/v1/chat` | Chat endpoint (streaming/non-streaming) |
| **API Docs** | `http://<SERVER_IP>/docs` | Interactive Swagger documentation |
| **MinIO Console** | `http://<SERVER_IP>:9001/` | File storage management |

**Login Credentials:**
- Email: `admin@yourcompany.com`
- Password: `ChangeMe123!` (change immediately!)

---

## Configuration Guide

### A. Configure AI Models

RAZE comes pre-configured with **Ollama (mistral)** as primary LLM. Here's how to manage and switch models:

#### Step 1: Verify Ollama is Running

```bash
# Check Ollama service
docker compose ps ollama

# List available models
docker compose exec ollama ollama list

# Or via HTTP
curl http://localhost:11434/api/tags
```

#### Step 2: Install Additional Ollama Models

```bash
# Pull additional models (run inside the container)
docker compose exec ollama ollama pull llama3.2
docker compose exec ollama ollama pull neural-chat
docker compose exec ollama ollama pull openchat

# Models are downloaded once and persisted in volume
# Check size: du -sh ollama_data/
```

#### Step 3: Switch Active Model

Edit `.env` and set:

```bash
OLLAMA_DEFAULT_MODEL=mistral          # or: llama3.2, neural-chat, openchat, etc.
DEFAULT_LLM_PROVIDER=ollama
LLM_ROUTING_STRATEGY=balanced          # or: cost, performance
```

Then restart backend:

```bash
docker compose restart backend
```

#### Step 4: Add Cloud Models as Fallback (Optional)

If you need higher quality for specific tasks, add OpenAI/Anthropic:

```bash
# In .env, add one or more:
OPENAI_API_KEY=sk-your-key-here
OPENAI_DEFAULT_MODEL=gpt-4o-mini

# OR
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_DEFAULT_MODEL=claude-3-5-sonnet-20241022

# OR
GOOGLE_API_KEY=your-gemini-key
```

Then update routing strategy:

```bash
# RAZE will automatically use:
# - Ollama for cost-sensitive queries
# - Cloud models when needed for better quality
LLM_ROUTING_STRATEGY=balanced
```

#### Step 5: Monitor Model Performance

```bash
# Check Ollama logs
docker compose logs ollama

# Check backend routing decisions
docker compose logs backend | grep "llm_routing"

# Test API
curl -X POST http://localhost/api/v1/chat/message \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello, what model are you?"}'
```

#### Complete Models Quick Reference

**FREE/LOCAL (Ollama)**

| Model | Size | Memory | Context | Speed | Quality | Download |
|-------|------|--------|---------|-------|---------|----------|
| **mistral** ⭐ | 7B | 6-8GB | 32K | ⚡⚡ Fast | ★★★★☆ | 4.1 GB |
| **llama3.2** | 3.8B | 4-6GB | 8K | ⚡⚡⚡ Fastest | ★★★☆☆ | 2.0 GB |
| **neural-chat** | 7B | 6-8GB | 8K | ⚡⚡ Fast | ★★★★☆ | 3.8 GB |
| **openchat** | 7B | 6-8GB | 8K | ⚡⚡ Fast | ★★★★☆ | 3.8 GB |
| **llama2** | 7B | 6-8GB | 4K | ⚡⚡ Fast | ★★★★☆ | 3.8 GB |
| **phi3** | 3.8B | 4-6GB | 4K | ⚡⚡⚡ Fastest | ★★★☆☆ | 2.3 GB |
| **orca-mini** | 3.8B | 3-4GB | 4K | ⚡⚡⚡ Fastest | ★★☆☆☆ | 1.8 GB |

**PAID/CLOUD (Optional Fallback)**

| Provider | Model | Speed | Quality | Context | Cost/1K | Best For |
|----------|-------|-------|---------|---------|---------|----------|
| **OpenAI** | gpt-4o | ⚡ | ★★★★★ | 128K | $0.005/$0.015 | Best overall |
| **OpenAI** | gpt-4o-mini | ⚡⚡ | ★★★★☆ | 128K | $0.00015/$0.0006 | Balanced fallback |
| **OpenAI** | gpt-4-turbo | ⚡ | ★★★★★ | 128K | $0.01/$0.03 | Long context |
| **OpenAI** | o1 | ⚡ | ★★★★★ | 128K | $0.015/$0.060 | Deep reasoning |
| **Anthropic** | claude-opus-4-5 | ⚡ | ★★★★★ | 200K | $15/$75/M | Best reasoning |
| **Anthropic** | claude-sonnet-4-5 | ⚡⚡ | ★★★★☆ | 200K | $3/$15/M | Balanced quality |
| **Anthropic** | claude-haiku-3-5 | ⚡⚡⚡ | ★★★☆☆ | 200K | $0.25/$1.25/M | Fast, cheap |
| **Gemini** | gemini-2.0-flash | ⚡⚡⚡ | ★★★★★ | 1M | $0.075/$0.30/M | Latest, images |
| **Gemini** | gemini-1.5-pro | ⚡⚡ | ★★★★★ | 2M | $1.25/$5/M | Ultra context |
| **Gemini** | gemini-1.5-flash | ⚡⚡⚡ | ★★★★☆ | 1M | $0.075/$0.30/M | Fast, cheap |
| **Grok** | grok-3 | ⚡⚡ | ★★★★☆ | 128K | $0.003/$0.015 | Real-time data |

#### How Model Switching Works

```
User: "Hello, how are you?"
    ↓
LLMRouter evaluates:
  • Context size: 250 tokens
  • Budget mode: balanced
  • Available providers: ollama (enabled)
    ↓
Decision: Use ollama/mistral
  Reason: Free tier, fits context, good quality
    ↓
Send to OllamaAdapter
    ↓
Response streamed back token-by-token
    ↓
Cost tracked: $0.00 ✓
```

If Ollama becomes unavailable and OpenAI is configured, system automatically fails over to gpt-4o-mini with no code changes needed.

### B. Configure Knowledge Base

1. Go to **Knowledge** → **Upload Source**
2. Choose file:
   - PDF, DOCX, TXT, CSV, JSON, HTML
   - Max 50MB
3. Enter title and description
4. Click **Upload**
5. Wait 30-60 seconds for processing
6. Status shows **"Approved"**

**Test Knowledge Search:**
1. Go to **Knowledge** → **Search**
2. Type a question about your document
3. Results appear instantly

### C. Configure Chat SDK

For embedding chat in your website:

```html
<!-- Add to your website -->
<div id="raze-chat"></div>

<script>
  window.RazeConfig = {
    apiUrl: 'http://your-server-ip/api',
    theme: {
      primaryColor: '#7C3AED',
      accentColor: '#06B6D4'
    }
  };
</script>
<script src="http://your-server-ip/raze-widget.js"></script>
```

Or via API:

```bash
# Get auth token
TOKEN=$(curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email":"admin@yourcompany.com",
    "password":"YOUR_PASSWORD"
  }' | jq -r '.access_token')

# Send message (non-streaming)
curl -X POST http://localhost/api/v1/chat/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message":"Hello! What can you do?",
    "use_knowledge":true
  }' | jq .

# Stream message (SSE)
curl -X POST http://localhost/api/v1/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message":"Explain quantum computing"
  }'
```

### D. Custom Branding (Optional)

Edit `.env` to customize appearance:

```bash
# Company Info
BRAND_NAME=YourCompanyName
CHATBOT_NAME=Your AI Assistant
COMPANY_NAME=Your Company Inc.

# Colors
THEME_PRIMARY_COLOR=#7C3AED
THEME_ACCENT_COLOR=#06B6D4
THEME_TEXT_COLOR=#1F2937

# Industry Type
INDUSTRY_TYPE=healthcare  # or: legal, finance, saas, ecommerce, education, creative
```

Then rebuild:
```bash
docker compose build frontend
docker compose up -d frontend
```

---

## Production Setup (HTTPS/Security)

### A. Enable HTTPS

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone -d your-domain.com

# Update .env
NEXT_PUBLIC_API_URL=https://your-domain.com/api
ALLOWED_ORIGINS=https://your-domain.com

# Restart
docker compose restart nginx
```

### B. Security Hardening

```bash
# Setup firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw enable

# Set strong passwords
# - Update .env with strong credentials
# - Change admin password in dashboard
# - Rotate API keys regularly

# Backup database
bash scripts/backup-database.sh

# Enable automated backups (crontab)
sudo crontab -e
# Add: 0 2 * * * cd /opt/raze && bash scripts/backup-database.sh
```

### C. Monitoring & Logs

```bash
# View all logs
docker compose logs -f

# View specific service
docker compose logs -f backend
docker compose logs -f postgres

# Check health
make health  # or docker compose exec backend curl http://localhost:8000/health

# Monitor performance
docker stats
```

---

## Manage Your Installation

### Common Commands

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart all services
docker compose restart

# View logs
docker compose logs -f

# Access database shell
docker compose exec postgres psql -U raze -d raze

# Access backend shell
docker compose exec backend bash

# Create database backup
bash scripts/backup-database.sh

# Restore from backup
docker compose exec postgres pg_restore -U raze -d raze < backup.pgdump

# Run migrations
docker compose exec backend alembic upgrade head

# Check migrations status
docker compose exec backend alembic current

# Create new migration (after model changes)
docker compose exec backend alembic revision --autogenerate -m "description"
```

### Update RAZE

```bash
# Pull latest code
git pull origin main

# Rebuild images
docker compose build

# Apply migrations
docker compose exec backend alembic upgrade head

# Restart
docker compose up -d
```

### Verify Installation

```bash
# Run comprehensive tests
bash scripts/test-deployment.sh

# Expected output:
# ✓ Docker daemon running
# ✓ PostgreSQL healthy
# ✓ Redis responsive
# ✓ Qdrant vector database
# ✓ Backend API responding
# ✓ Frontend accessible
# ✓ Nginx routing working
# ✓ All tests passed!
```

---

## Troubleshooting

### Services won't start

```bash
# Check logs
docker compose logs

# Common issues:
# 1. Port already in use - change in docker-compose.yml
# 2. Missing .env file - copy .env.example and fill it
# 3. Low disk space - clean Docker: docker system prune -a
```

### Backend crashes

```bash
# View logs
docker compose logs backend

# Wait for PostgreSQL to be ready
sleep 30
docker compose restart backend

# Check database connection
docker compose exec postgres pg_isready -U raze -d raze
```

### Database errors

```bash
# Check database is running
docker compose exec postgres pg_isready

# Reset database (⚠️ LOSES DATA)
docker compose down
docker volume rm raze_postgres_data
docker compose up -d
docker compose exec backend alembic upgrade head
```

### Chat API not responding

```bash
# Check backend health
curl http://localhost/health

# Check OpenAI key is set
grep OPENAI_API_KEY .env

# Verify API docs load
curl http://localhost/docs

# Check backend logs
docker compose logs backend | grep -i error
```

### Forgot admin password

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

## Features After Installation

✅ **Chat & Conversation**
- Streaming responses (real-time token delivery)
- Multiple LLM support (OpenAI, Anthropic, Gemini)
- Memory persistence across sessions
- Knowledge base injection
- Tool/function calling

✅ **Knowledge Management**
- Upload documents (PDF, DOCX, TXT, CSV, JSON, HTML)
- Semantic search (Qdrant vectors)
- Full-text search
- Hybrid search (semantic + keyword)
- Version history & rollback
- Approval workflow

✅ **Admin Panel**
- User management
- AI configuration
- Knowledge management
- Memory management
- Analytics (30-day tracking)
- Audit logs
- System health monitoring

✅ **Enterprise Features**
- JWT authentication
- Role-based access control (RBAC)
- Rate limiting (per user, per operation)
- Circuit breakers (error recovery)
- Metrics & monitoring
- Distributed tracing
- Structured logging

---

## Support Resources

| Problem | Solution |
|---------|----------|
| Installation stuck? | Check `docker compose logs` for errors |
| API key errors? | Verify API key in `.env` and in admin dashboard |
| Database locked? | Wait 60 seconds and restart: `docker compose restart postgres` |
| Nginx not proxying? | Check `/etc/nginx/conf.d/raze.conf` exists |
| HTTPS not working? | Verify certificate paths in nginx config |
| Out of memory? | Increase Docker memory or reduce batch sizes |

---

## Next Steps

1. ✅ Install RAZE (this guide)
2. 📝 Upload your documents to knowledge base
3. 👥 Invite team members
4. 🔧 Configure AI models per your needs
5. 🚀 Go live!

---

**Your RAZE platform is ready for production. 🚀**

For detailed API documentation, visit: `http://your-server-ip/docs`
