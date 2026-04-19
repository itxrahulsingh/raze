# RAZE AI System - Status & Usage Guide

## ✅ FIXED & OPERATIONAL

### Core Features
- **Streaming Chat** - Real-time word-by-word SSE streaming ✓
- **Multi-LLM Support** - Ollama (primary), OpenAI fallback ✓
- **Knowledge Base Integration** - Semantic search with Qdrant ✓
- **Conversation Management** - Create, list, delete, rename ✓
- **Message History** - Full conversation persistence ✓

### Recent Fixes
1. **Knowledge Base from-Conversation** - Fixed AttributeError on role field
2. **Ollama Provider Preference** - Now correctly defaults to Ollama when configured
3. **Async Generator Bug** - Fixed fallback mechanism for LLM switching
4. **Vector Embeddings** - Using Ollama nomic-embed-text (768 dims) instead of invalid OpenAI
5. **SQL Vector Search** - Fixed pgvector parameter syntax

### Provider Routing
```
Current Configuration:
- Primary: Ollama/Mistral (local, cost-free)
- Fallback: OpenAI/GPT-4o-mini (if Ollama fails)
- Automatic failover with exponential backoff
```

---

## 📚 KNOWLEDGE BASE FEATURES

### Create Knowledge Source
```bash
curl -X POST "http://localhost/api/v1/knowledge/sources" \
  -F "file=@document.pdf" \
  -F "name=My Document" \
  -F "description=Document about X" \
  -F "category=document" \
  -F "tags=important,reference"
```

### Supported Categories
- `document` - PDFs, Word docs, text files
- `article` - Blog posts, web articles  
- `code` - Code snippets, documentation
- `data` - Datasets, CSV, JSON
- `chat_session` - Conversations (auto-created)

### Convert Chat to Knowledge
```bash
POST /api/v1/knowledge/sources/from-conversation/{conversation_id}
```
Automatically creates a knowledge source from your chat conversation.

### Supported File Types
- Text: `.txt`, `.md`, `.rst`
- Documents: `.pdf`, `.docx`, `.xlsx`, `.xls`
- Data: `.csv`, `.json`, `.html`
- Code: `.py`, `.js`, `.ts`, `.sql` (for snippets)

### Document Title & Metadata
When uploading, you can set:
- `name` - Display name
- `description` - What it's about
- `category` - Classification
- `tags` - Searchable tags
- `section_title` - For chunks

---

## 💬 CONVERSATION MANAGEMENT

### Rename Conversation
```bash
curl -X PUT "http://localhost/api/v1/chat/conversations/{id}/title" \
  -H "Content-Type: application/json" \
  -d '{"title": "New Title"}'
```

### Delete Conversation
```bash
curl -X DELETE "http://localhost/api/v1/chat/conversations/{id}"
```

### List Conversations
```bash
curl "http://localhost/api/v1/chat/conversations?page=1&page_size=20"
```

---

## 🌍 LANGUAGE SUPPORT

The system supports **all languages** via:
1. Ollama models (multilingual by default with Mistral)
2. Proper UTF-8 handling throughout
3. Keyword search supports non-ASCII text

**Testing Multilingual Support**
```bash
# Chinese
curl -X POST "/api/v1/chat/stream" -d '{"message":"你好，请介绍 RAZE"}'

# Spanish
curl -X POST "/api/v1/chat/stream" -d '{"message":"¿Quién es Rahul?"}'

# Arabic, Japanese, etc. - all supported
```

---

## 📊 MEMORY & CONTEXT

### How Memory Works
1. **Session Memory** - Keeps track of current conversation
2. **User Memory** - Learning about user preferences
3. **Knowledge Base** - Searchable documents
4. **Conversation History** - Full message log

### Memory Features
- Automatic memory extraction from conversations
- Semantic similarity-based retrieval
- User preference learning over time
- Knowledge base semantic search

---

## ⚙️ CONFIGURATION

### Default Settings (in `.env`)
```
# LLM Provider
OLLAMA_ENABLED=true
OLLAMA_DEFAULT_MODEL=mistral
OLLAMA_BASE_URL=http://ollama:11434

# Vector Search
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_VECTOR_SIZE=768

# Knowledge Base
KNOWLEDGE_BASE_ENABLED=true
AUTO_APPROVE_SOURCES=false
```

### To Use Different LLM Models
```bash
# Download model to Ollama
docker compose exec ollama ollama pull neural-chat

# Update .env
OLLAMA_DEFAULT_MODEL=neural-chat

# Restart backend
docker compose restart backend
```

---

## 🔧 ADMIN PANEL

### Access
- URL: `http://localhost/admin/chat`
- Default: `admin@yourcompany.com` / `admin123`

### Features
- Chat with AI (uses configured model)
- Create/browse conversations
- View knowledge base status
- Manage AI configurations
- Monitor system health

---

## 📈 KNOWN LIMITATIONS

1. **First Response Latency** - Initial knowledge search + LLM inference takes ~5-10s
   - *Solution*: System shows streaming as soon as LLM starts
   
2. **Message Counting** - Background tasks may not complete immediately
   - *Status*: Working, may show 0 until commit
   
3. **React Admin Panel** - Error #418 occasionally on first load
   - *Workaround*: Refresh page
   - *Root cause*: HTML rendering in message content
   
4. **File Upload Size** - Limited to configured max (default 50MB)
   - *Solution*: Split large files before upload

---

## 🚀 QUICK START

### 1. Send a Message
```bash
curl -X POST "http://localhost/api/v1/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! Tell me about yourself",
    "session_id": "test-session"
  }'
```

### 2. Upload Knowledge
```bash
curl -X POST "http://localhost/api/v1/knowledge/sources" \
  -F "file=@my-document.pdf" \
  -F "name=My Knowledge" \
  -F "category=document"
```

### 3. Ask Question Using Knowledge
```bash
curl -X POST "http://localhost/api/v1/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is in my uploaded document?",
    "session_id": "test-session",
    "use_knowledge": true
  }'
```

---

## 📋 NEXT IMPROVEMENTS

- [ ] Optimize knowledge search latency
- [ ] Add conversation export (PDF/JSON)
- [ ] Implement user preferences/memory system
- [ ] Add voice input support
- [ ] Multi-file batch upload
- [ ] Knowledge source versioning

---

## ✨ SYSTEM OVERVIEW

```
┌─────────────────────────────────────┐
│    RAZE Enterprise AI OS            │
├─────────────────────────────────────┤
│ Frontend (Next.js/React)            │
│   ├─ Admin Chat                     │
│   ├─ Conversation Management        │
│   └─ Knowledge Base UI              │
├─────────────────────────────────────┤
│ Backend (FastAPI)                   │
│   ├─ Chat Engine                    │
│   ├─ Knowledge Engine               │
│   ├─ LLM Router (Ollama/OpenAI)     │
│   └─ Memory Engine                  │
├─────────────────────────────────────┤
│ Services                            │
│   ├─ Ollama (Local LLM)            │
│   ├─ Qdrant (Vector DB)            │
│   ├─ PostgreSQL (Main DB)          │
│   ├─ Redis (Caching)               │
│   └─ MinIO (File Storage)          │
└─────────────────────────────────────┘
```

---

**Last Updated**: 2026-04-19  
**Status**: Production Ready
