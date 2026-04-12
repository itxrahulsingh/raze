# RAZE Enterprise AI OS - Architecture Documentation

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     RAZE AI Operating System                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │                  Internet / Users                      │    │
│  │  (Browser, SDK Embed, Mobile, API Clients)            │    │
│  └────────────────────┬─────────────────────────────────┘    │
│                       │                                         │
│  ┌────────────────────▼─────────────────────────────────┐    │
│  │          Nginx Reverse Proxy (Port 80/443)           │    │
│  │  - Route /api/* → Backend (8000)                     │    │
│  │  - Route / → Frontend (3000)                         │    │
│  │  - Route /chat-sdk → CDN                             │    │
│  └────────────────────┬─────────────────────────────────┘    │
│                       │                                         │
│  ┌────────────────────┴─────────────────────────────────┐    │
│  │              Microservices Layer (Docker)            │    │
│  │                                                       │    │
│  ├─────────────────────────────────────────────────────┤    │
│  │  FastAPI Backend (Port 8000)                         │    │
│  │  - AI Orchestration Engine  \                        │    │
│  │  - Multi-LLM Router          \  Core Engines        │    │
│  │  - Memory Engine              |   (8 modules)       │    │
│  │  - Knowledge Engine           |                      │    │
│  │  - Tool Engine               |                       │    │
│  │  - Vector Search            /                        │    │
│  │  - Observability           /                         │    │
│  │  - REST API Routes                                   │    │
│  ├─────────────────────────────────────────────────────┤    │
│  │  Next.js Admin Frontend (Port 3000)                  │    │
│  │  - Dashboard                                         │    │
│  │  - Knowledge Management                              │    │
│  │  - Conversation Monitoring                           │    │
│  │  - Analytics                                         │    │
│  │  - Settings                                          │    │
│  ├─────────────────────────────────────────────────────┤    │
│  │  Data Layer                                          │    │
│  │  - PostgreSQL (Primary DB + Vector) | Port 5432     │    │
│  │  - Qdrant (Vector Search)          | Port 6333      │    │
│  │  - Redis (Cache + Sessions)        | Port 6379      │    │
│  │  - MinIO (Object Storage)          | Port 9000      │    │
│  │                                                      │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. **Frontend Layer**

#### 1.1 Admin Dashboard (Next.js 14)
- **Purpose**: System administration and configuration
- **Components**:
  - Dashboard (overview, metrics, health)
  - Knowledge Management (upload, approve, view)
  - Conversation Monitoring (view sessions, replay)
  - Memory Management (view/edit memories)
  - Tool Management (CRUD tools, test)
  - Analytics (charts, metrics, observability logs)
  - Settings (AI config, users, security)
- **Technology**: Next.js 14, React 18, TypeScript, Tailwind CSS, shadcn/ui
- **Data Fetching**: React Query (TanStack Query) with automatic caching
- **State**: URL-based routing + local component state

#### 1.2 Chat SDK (Embedded Widget)
- **Purpose**: Embeddable chat widget for end users
- **Features**:
  - Floating chat button
  - Message history in session
  - Streaming responses (SSE)
  - Customizable theme
  - Session-based or API key auth
- **Technology**: Vanilla TypeScript, compiled to IIFE
- **Size**: ~15KB gzipped
- **Integration**: One `<script>` tag

### 2. **API Gateway Layer**

#### 2.1 Nginx Reverse Proxy
- **Purpose**: Request routing, SSL termination, rate limiting, compression
- **Configuration**:
  ```
  /api/* → backend:8000
  /ws/* → backend:8000 (WebSocket upgrade)
  /_next/static/* → cached
  / → frontend:3000
  ```
- **Features**:
  - Gzip compression
  - Rate limiting (global + per-endpoint)
  - Security headers
  - Upload size limits (100MB)
  - Keep-alive timeouts

### 3. **Backend - FastAPI Application**

#### 3.1 Application Structure
```
backend/
├── app/
│   ├── main.py                  # FastAPI app entry
│   ├── config.py                # Configuration (Pydantic)
│   ├── database.py              # SQLAlchemy setup
│   ├── models/                  # Database models (14 tables)
│   ├── schemas/                 # Pydantic schemas
│   ├── api/v1/                  # API routes (8 route files)
│   │   ├── auth.py              # Authentication
│   │   ├── chat.py              # Chat messages
│   │   ├── knowledge.py         # Knowledge management
│   │   ├── memory.py            # Memory system
│   │   ├── tools.py             # Tool management
│   │   ├── admin.py             # Admin panel
│   │   ├── analytics.py         # Observability
│   │   └── sdk.py               # SDK endpoints
│   └── core/                    # Core AI engines (8 modules)
│       ├── orchestrator.py      # Main AI orchestrator
│       ├── llm_router.py        # Multi-LLM routing
│       ├── memory_engine.py     # Memory management
│       ├── knowledge_engine.py  # Knowledge ingestion
│       ├── tool_engine.py       # Tool execution
│       ├── vector_search.py     # Vector search
│       ├── observability.py     # AI decision logging
│       └── security.py          # JWT, auth helpers
└── alembic/                     # Database migrations
```

#### 3.2 Core AI Engines

**AI Orchestrator** (Main Orchestration Engine)
```
User Message
    ↓
Detect Intent (chat/knowledge/tool/clarification)
    ↓
Build Context (memories + knowledge + history)
    ↓
Decide Action (answer_directly / search_knowledge / execute_tool)
    ↓
Generate Response (via LLM Router)
    ↓
Execute Tools (if needed, with results)
    ↓
Post-Process (extract memories, update context)
    ↓
Log Decision (observability)
    ↓
Return Response (streaming or sync)
```

**Multi-LLM Router**
- Supports: OpenAI, Anthropic, Google Gemini, Grok, Ollama
- Routing Strategies:
  - **Cost**: Minimize price
  - **Performance**: Maximize speed
  - **Balanced**: Mix of both
- Features:
  - Token counting per model
  - Automatic failover
  - Cost tracking
  - Per-task model selection
  - Unified message format

**Memory Engine** (Multi-Layer)
- **Context Memory**: Session-based, Redis-backed (circular buffer)
- **User Memory**: Persistent user facts, semantic searchable
- **Operational Memory**: Tool results from current session
- **Knowledge Memory**: Facts extracted from conversations
- Features:
  - Importance scoring (0-1)
  - Memory decay over time
  - Auto-consolidation of similar memories
  - Retention policies (TTL, max count)
  - Vector embeddings for semantic search

**Knowledge Engine**
- **Ingestion**:
  - File types: PDF, DOCX, TXT
  - Sources: URLs, manual entry
  - Processing: Extraction → Chunking → Embedding
- **Storage**:
  - Chunks in PostgreSQL + pgvector
  - Distributed to Qdrant for scale
  - Deduplication via content hash
- **Access**:
  - Admin approval/rejection workflow
  - Persistent vs Linked modes
  - Hybrid search (BM25 + vector)
  - Knowledge decay not applicable

**Tool Engine**
- **Tool Definition**: OpenAI function calling format (JSON schema)
- **Execution**: HTTP API calls with auth (bearer, API key, basic, OAuth2)
- **Validation**: Input schema + output validation
- **Retry**: Exponential backoff (max 3 attempts)
- **Tracking**: Execution logs with latency, status, error
- **Rendering**: Formatted results (text, table, card)

**Vector Search Engine**
- **Dual Implementation**:
  - Primary: Qdrant (cluster-ready)
  - Fallback: pgvector (built-in PostgreSQL)
- **Features**:
  - Semantic search (<200ms response)
  - Hybrid search (keyword + vector)
  - Re-ranking for relevance
  - Distributed indexing (IVFFlat)
  - Collections: "knowledge", "memory"

**Observability Engine**
- **Decision Logging**:
  - Intent detected
  - Model selected (with reason)
  - Tools considered and selected
  - Confidence score
  - Context retrieved
  - Latency and cost
- **Metrics Aggregation**:
  - Per-model usage
  - Per-intent distribution
  - Per-tool execution
  - Daily rollup to database
- **Cost Calculation**: Real-time per-token costs

#### 3.3 API Routes (8 modules)

| Route | Purpose | Methods |
|-------|---------|---------|
| `/auth` | Authentication & users | POST login/refresh, GET me |
| `/chat` | Conversational AI | POST message/stream, GET conversations |
| `/knowledge` | Knowledge management | POST upload, GET sources/search, PUT approve |
| `/memory` | Memory system | GET/POST/PUT/DELETE memories, search |
| `/tools` | Tool management | CRUD tools, POST test, GET executions |
| `/admin` | Admin controls | GET dashboard, CRUD AI configs, health |
| `/analytics` | Observability | GET metrics, logs, usage, models |
| `/sdk` | Embedded widget | POST init/message/stream, GET config |

### 4. **Data Layer**

#### 4.1 PostgreSQL Database (14 Tables)
```
Users
├── User (id, email, username, hashed_password, role, is_active, last_login)
└── APIKey (id, user_id, name, key_hash, key_prefix, permissions, rate_limit)

Conversations
├── Conversation (id, session_id, user_id, title, status, message_count, total_tokens)
└── Message (id, conversation_id, role, content, tool_calls, tokens_used, model_used)

Knowledge
├── KnowledgeSource (id, name, type, status, file_path, url, file_size, content_hash, chunk_count)
└── KnowledgeChunk (id, source_id, content, chunk_index, embedding[pgvector])

Memory System
├── Memory (id, user_id, session_id, type, content, importance_score, embedding[pgvector])
└── MemoryRetentionPolicy (id, name, type, max_count, ttl_days, min_importance)

Tool Execution
├── Tool (id, name, description, type, schema, endpoint_url, auth_type, auth_config)
└── ToolExecution (id, tool_id, conversation_id, input_data, output_data, status)

AI Configuration
└── AIConfig (id, name, is_default, provider, model_name, temperature, max_tokens, routing_strategy)

Analytics
├── ObservabilityLog (id, message_id, intent, model_selected, tools_considered, confidence, latency, cost)
├── UsageMetrics (id, date, total_requests, total_tokens, total_cost, avg_latency)
└── UserSession (id, session_id, ip_address, user_agent, device_type, country)
```

**Indexing Strategy**:
- Primary keys: UUID
- Foreign keys: Indexed
- Vector search: pgvector with IVFFlat index
- Text search: Full-text search on knowledge chunks
- Partitioning: By date for large tables (conversations, observability logs)

#### 4.2 Qdrant Vector Database
- **Collections**:
  - `knowledge`: Knowledge chunk embeddings (HNSW index)
  - `memory`: User memory embeddings (HNSW index)
- **Purpose**: Fast semantic search, distributed scaling
- **Fallback**: Drop into pgvector if Qdrant unavailable

#### 4.3 Redis Cache
- **Session Storage**: `raze:context:{session_id}` (circular buffer)
- **Operational Memory**: `raze:operations:{session_id}`
- **Daily Metrics**: `raze:metrics:{YYYY-MM-DD}`
- **Cache Keys**: Model outputs, vector embeddings
- **TTL**: Session 7 days, metrics 90 days
- **Authentication**: Password-protected connection

#### 4.4 MinIO Object Storage
- **S3-Compatible API**
- **Buckets**:
  - `raze-files`: Uploaded knowledge files
  - `raze-logs`: Application logs
  - `raze-exports`: Conversation exports
  - `raze-embeddings`: Embedding cache
- **Lifecycle**: Auto-delete old logs after 90 days

### 5. **Message Flow Architecture**

#### 5.1 User Message Processing Flow
```
1. User sends message (via chat interface or SDK)
   ↓
2. Nginx routes to backend /api/v1/chat/stream
   ↓
3. FastAPI endpoint receives request
   ↓
4. Extract session/user context
   ↓
5. Call AI Orchestrator.process_message()
   │
   ├→ Detect Intent (NLP heuristics + optional LLM)
   │
   ├→ Build Context
   │  ├→ Fetch user memories from DB + vector search
   │  ├→ Get session context from Redis
   │  └→ Fetch conversation history from DB
   │
   ├→ Decide Action
   │  ├→ If knowledge_query: Search knowledge base
   │  ├→ If tool_use: Select best tool for task
   │  └→ If chat: Proceed to LLM generation
   │
   ├→ Assemble Messages for LLM
   │  ├→ System prompt (with injected context)
   │  ├→ Conversation history (truncated to token budget)
   │  └→ Current message
   │
   ├→ Call Multi-LLM Router
   │  ├→ Select provider/model based on routing strategy
   │  ├→ Call LLM (with retry)
   │  └→ Stream response chunks
   │
   ├→ Process Tool Calls (if any)
   │  ├→ Validate tool input
   │  ├→ Execute HTTP call
   │  ├→ Validate output
   │  └→ Log execution
   │
   ├→ Post-Process Response
   │  ├→ Store message in DB
   │  ├→ Add to session context (Redis)
   │  └→ Extract and store new memories
   │
   └→ Log Decision
       ├→ Store observability log
       └→ Update metrics

6. Stream response back as SSE
   ↓
7. Frontend receives and renders
```

#### 5.2 Knowledge Ingestion Flow
```
1. Admin uploads file or submits URL
   ↓
2. Backend receives, saves to MinIO
   ↓
3. Background task processes
   ├→ Extract text (PDF, DOCX, etc.)
   ├→ Chunk text (intelligent, with overlap)
   ├→ Generate embeddings (batch)
   ├→ Deduplicate (via content_hash)
   └→ Store chunks in DB + Qdrant
   ↓
4. Mark as "pending_approval"
   ↓
5. Admin reviews and approves
   ↓
6. Knowledge becomes available for search
```

#### 5.3 Memory Decay Flow (Async Task)
```
Every 24 hours:
1. For each user:
   ├→ Fetch all memories
   ├→ For each memory:
   │  ├→ Calculate decay: importance * (decay_rate ^ days_old)
   │  ├→ If < threshold: Mark inactive
   │  └→ Update score
   └→ Auto-consolidate similar memories
```

### 6. **Security Architecture**

#### 6.1 Authentication & Authorization
- **JWT Tokens**:
  - Access token: 30 minutes (HS256)
  - Refresh token: 7 days
  - Algorithm: HS256 (with SECRET_KEY)
  - Claims: user_id, email, role, exp, iat

- **API Keys**:
  - Stored as bcrypt hash
  - Prefix for searching (hint)
  - Per-key rate limits
  - Optional expiration

- **Roles**:
  - `superadmin`: Full access
  - `admin`: System management
  - `viewer`: Read-only analytics
  - (SDK users: Session-based, no role)

#### 6.2 Data Protection
- **At Rest**: Database passwords, API keys encrypted with env SECRET_KEY
- **In Transit**: TLS 1.2+ (when domain/SSL added)
- **Secrets**: Never in code, always in .env

#### 6.3 Input Validation
- **Pydantic Schemas**: All inputs validated before processing
- **SQL Injection**: SQLAlchemy parameterized queries (async)
- **Prompt Injection**: Sanitization of user inputs for LLM
- **File Upload**: Type validation, size limits, virus scanning (optional)

#### 6.4 Rate Limiting
- **Global**: 100 requests/minute per IP
- **Auth**: 5 login attempts/minute
- **Chat**: 30 messages/minute per user
- **Storage**: Redis-backed counters

### 7. **Scalability Strategy**

#### 7.1 Current (Single Server)
- All services on one Docker Compose
- Suitable for: 50-100 concurrent users
- Database: Single PostgreSQL instance
- Cache: Single Redis instance
- Storage: Local MinIO

#### 7.2 Multi-Server (Phase 2)
- **Load Balancer**: HAProxy or AWS ALB
- **API Servers**: 2-3 stateless FastAPI instances
- **Database**: PostgreSQL Primary/Replica RDS
- **Cache**: Redis Cluster or ElastiCache
- **Vector DB**: Qdrant cluster (3+ nodes)
- **Storage**: S3 or MinIO distributed

#### 7.3 Kubernetes (Phase 3)
- **Containerized**: All services already Docker-ready
- **Helm Charts**: For deployment and scaling
- **Horizontal Pod Autoscaling**: Based on CPU/memory
- **Database**: Managed PostgreSQL (Cloud SQL, RDS)
- **Queue**: Kafka for async processing
- **Logging**: ELK Stack or Cloud Logging

### 8. **Performance Characteristics**

| Metric | Target | Typical |
|--------|--------|---------|
| Chat Response | <2s | 1.2-1.8s |
| Knowledge Search | <200ms | 80-150ms |
| Vector Embedding | <500ms | 200-400ms |
| API Response | <500ms | 50-200ms |
| Concurrent Users | 100+ | 500+ K8s |
| Storage (per 1000 users) | 50-100 GB | Depends on knowledge |
| Cache Hit Rate | >80% | 85-95% |

### 9. **Deployment Topology**

```
                    INTERNET
                      ↓
        ┌─────────────────────────┐
        │ Nginx Reverse Proxy     │
        │ (Port 80/443)           │
        └──────────┬──────────────┘
                   ↓
        ┌──────────────────────────┐
        │ FastAPI Backend (8000)   │
        └──────────┬───────────────┘
                   ↓
        ┌──────────────────────────┐
        │   Data Layer             │
        ├──────────────────────────┤
        │ PostgreSQL  | Port 5432  │
        │ Redis      | Port 6379   │
        │ Qdrant     | Port 6333   │
        │ MinIO      | Port 9000   │
        └──────────────────────────┘
```

### 10. **Technology Stack Summary**

| Layer | Technology | Version |
|-------|-----------|---------|
| Reverse Proxy | Nginx | 1.25+ |
| API Framework | FastAPI | 0.104+ |
| Database | PostgreSQL | 16 |
| Vector DB | Qdrant | Latest |
| Cache | Redis | 7 |
| Storage | MinIO | Latest |
| Frontend | Next.js | 14 |
| SDK | TypeScript | 5.4+ |
| ORM | SQLAlchemy | 2.0+ |
| Auth | JWT + bcrypt | - |
| Async | AsyncIO | Python 3.12 |
| Container | Docker | 20.10+ |
| Orchestration | Docker Compose | v2 |
| LLMs | Multiple APIs | Latest |

---

For deployment details, see [DEPLOYMENT.md](./DEPLOYMENT.md)

For API details, see [API.md](./API.md)
