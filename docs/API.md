# RAZE Enterprise AI OS - API Documentation

## Base URL

```
http://<SERVER_IP>/api/v1
```

## Authentication

### Methods

1. **Bearer Token (JWT)**
```
Authorization: Bearer <access_token>
```

2. **API Key**
```
X-API-Key: <api_key>
```

3. **Session ID (SDK)**
```
X-Session-ID: <session_id>
```

## Rate Limiting

- **Standard endpoints**: 100 requests/minute
- **Chat endpoints**: 30 messages/minute
- **Auth endpoints**: 5 attempts/minute

Limits are per IP address or API key.

---

## Authentication Endpoints

### POST /auth/login
Login with email and password.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Example:**
```bash
curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@raze.local",
    "password": "password"
  }'
```

---

### POST /auth/refresh
Refresh access token using refresh token.

**Request:**
```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "expires_in": 1800
}
```

---

### GET /auth/me
Get current user profile.

**Headers required:**
- Authorization: Bearer `<token>`

**Response:**
```json
{
  "id": "user-001",
  "email": "user@example.com",
  "username": "user",
  "role": "admin",
  "is_active": true,
  "last_login": "2024-04-12T10:30:00Z"
}
```

---

## Chat Endpoints

### POST /chat/message
Send a message and get synchronous response.

**Request:**
```json
{
  "session_id": "sess-123",
  "message": "What is RAZE?",
  "ai_config_id": "config-001"  // optional
}
```

**Response:**
```json
{
  "message_id": "msg-789",
  "conversation_id": "conv-456",
  "content": "RAZE is an Enterprise AI Operating System...",
  "model": "gpt-4-turbo",
  "tokens_used": 150,
  "latency_ms": 2345
}
```

---

### POST /chat/stream
Send a message and get streaming response (Server-Sent Events).

**Request:**
```json
{
  "session_id": "sess-123",
  "message": "Tell me about yourself"
}
```

**Response (SSE stream):**
```
data: {"type":"intent","intent":"chat"}

data: {"type":"text","content":"I"}
data: {"type":"text","content":"'m"}
data: {"type":"text","content":" RAZE"}
...
data: {"type":"done","message_id":"msg-789"}
```

**Example with curl:**
```bash
curl -N -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"sess-123","message":"Hello"}' \
  http://localhost/api/v1/chat/stream
```

---

### GET /chat/conversations
List conversations (paginated).

**Query Parameters:**
- `skip`: offset (default: 0)
- `limit`: items per page (default: 50)
- `user_id`: filter by user

**Response:**
```json
[
  {
    "id": "conv-001",
    "session_id": "sess-123",
    "title": "General Questions",
    "status": "active",
    "message_count": 15,
    "total_tokens": 2500,
    "created_at": "2024-04-10T08:00:00Z",
    "updated_at": "2024-04-12T10:30:00Z"
  }
]
```

---

### GET /chat/conversations/{id}
Get conversation with all messages.

**Response:**
```json
{
  "id": "conv-001",
  "title": "Knowledge Query",
  "messages": [
    {
      "id": "msg-001",
      "role": "user",
      "content": "What are the company policies?",
      "created_at": "2024-04-12T10:00:00Z"
    },
    {
      "id": "msg-002",
      "role": "assistant",
      "content": "Our policies include...",
      "model": "gpt-4",
      "tokens_used": 250,
      "created_at": "2024-04-12T10:00:05Z"
    }
  ]
}
```

---

### DELETE /chat/conversations/{id}
Delete a conversation.

**Response:**
```json
{
  "deleted": true,
  "id": "conv-001"
}
```

---

## Knowledge Management Endpoints

### POST /knowledge/sources
Upload a knowledge source (file or URL).

**Multipart Form:**
- `file`: PDF, DOCX, TXT file
- OR `url`: Web URL to ingest

**Response:**
```json
{
  "id": "src-001",
  "name": "Company Handbook",
  "type": "pdf",
  "status": "processing",
  "file_size": 2048576,
  "created_at": "2024-04-12T10:00:00Z"
}
```

**Example:**
```bash
curl -X POST http://localhost/api/v1/knowledge/sources \
  -H "Authorization: Bearer <token>" \
  -F "file=@handbook.pdf"
```

---

### GET /knowledge/sources
List knowledge sources.

**Query Parameters:**
- `skip`: offset
- `limit`: items per page
- `status`: pending, processing, approved, rejected

**Response:**
```json
[
  {
    "id": "src-001",
    "name": "Company Handbook",
    "type": "pdf",
    "status": "approved",
    "chunk_count": 45,
    "embedding_model": "text-embedding-3-small",
    "mode": "persistent",
    "created_at": "2024-04-10T08:00:00Z"
  }
]
```

---

### PUT /knowledge/sources/{id}/approve
Approve a pending knowledge source.

**Headers required:**
- Admin authorization required

**Response:**
```json
{
  "id": "src-001",
  "status": "approved",
  "approved_at": "2024-04-12T10:30:00Z",
  "approved_by": "admin-001"
}
```

---

### PUT /knowledge/sources/{id}/reject
Reject a knowledge source.

**Request:**
```json
{
  "reason": "Contains outdated information"
}
```

**Response:**
```json
{
  "id": "src-001",
  "status": "rejected",
  "reason": "Contains outdated information"
}
```

---

### POST /knowledge/search
Semantic search across knowledge base.

**Request:**
```json
{
  "query": "company vacation policy",
  "top_k": 5,
  "search_type": "hybrid",  // semantic, keyword, hybrid
  "filters": {
    "source_id": "src-001"  // optional
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "chunk_id": "chunk-001",
      "source_id": "src-001",
      "source_name": "Company Handbook",
      "content": "Vacation Policy: Employees receive...",
      "relevance_score": 0.95,
      "metadata": {}
    }
  ],
  "total": 1,
  "query_time_ms": 145
}
```

---

## Memory Management Endpoints

### GET /memory
List memories.

**Query Parameters:**
- `user_id`: required
- `type`: context, user, operational, knowledge
- `skip`, `limit`

**Response:**
```json
[
  {
    "id": "mem-001",
    "type": "user",
    "content": "User prefers concise responses",
    "importance_score": 0.8,
    "created_at": "2024-04-10T08:00:00Z",
    "last_accessed": "2024-04-12T10:00:00Z"
  }
]
```

---

### POST /memory
Manually add a memory.

**Request:**
```json
{
  "user_id": "user-001",
  "session_id": "sess-123",
  "type": "user",
  "content": "Prefers technical explanations",
  "importance_score": 0.7
}
```

---

### PUT /memory/{id}
Update memory.

**Request:**
```json
{
  "importance_score": 0.9,
  "content": "Updated memory content"
}
```

---

### DELETE /memory/{id}
Delete memory.

**Response:**
```json
{
  "deleted": true
}
```

---

## Tool Management Endpoints

### POST /tools
Create a tool/action.

**Request:**
```json
{
  "name": "Send Email",
  "description": "Send an email to a recipient",
  "type": "http_api",
  "endpoint_url": "https://api.email.com/send",
  "method": "POST",
  "schema": {
    "type": "object",
    "properties": {
      "to": {"type": "string"},
      "subject": {"type": "string"},
      "body": {"type": "string"}
    },
    "required": ["to", "subject", "body"]
  },
  "auth_type": "bearer",
  "auth_config": {
    "token": "secret-token"
  }
}
```

**Response:**
```json
{
  "id": "tool-001",
  "name": "Send Email",
  "description": "Send an email to a recipient",
  "is_active": true,
  "usage_count": 0,
  "created_at": "2024-04-12T10:00:00Z"
}
```

---

### GET /tools
List all tools.

**Headers required:**
- Admin authorization

**Response:**
```json
[
  {
    "id": "tool-001",
    "name": "Send Email",
    "type": "http_api",
    "is_active": true,
    "usage_count": 45,
    "success_rate": 0.98
  }
]
```

---

### POST /tools/{id}/test
Test tool with sample input.

**Request:**
```json
{
  "to": "test@example.com",
  "subject": "Test",
  "body": "This is a test"
}
```

**Response:**
```json
{
  "status": "success",
  "result": {
    "message_id": "msg-abc123"
  },
  "latency_ms": 234
}
```

---

## Admin Control Panel Endpoints

### GET /admin/dashboard
Get admin dashboard overview.

**Headers required:**
- Admin authorization

**Response:**
```json
{
  "total_conversations": 124,
  "total_messages": 3456,
  "active_users": 28,
  "health": "healthy",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "qdrant": "healthy"
  }
}
```

---

### GET /admin/ai-config
List AI configurations.

**Response:**
```json
[
  {
    "id": "config-001",
    "name": "Default",
    "is_default": true,
    "provider": "openai",
    "model_name": "gpt-4-turbo",
    "temperature": 0.7,
    "max_tokens": 2000,
    "routing_strategy": "balanced"
  }
]
```

---

### POST /admin/ai-config
Create AI configuration.

**Request:**
```json
{
  "name": "Creative",
  "provider": "anthropic",
  "model_name": "claude-3-opus",
  "temperature": 0.9,
  "max_tokens": 4000,
  "system_prompt": "You are a creative AI...",
  "routing_strategy": "performance"
}
```

---

### PUT /admin/ai-config/{id}/set-default
Set configuration as default.

**Response:**
```json
{
  "id": "config-001",
  "is_default": true
}
```

---

### GET /admin/system/health
Get detailed system health.

**Response:**
```json
{
  "database": {
    "status": "healthy",
    "response_time_ms": 12,
    "connections": 25
  },
  "redis": {
    "status": "healthy",
    "memory_mb": 256
  },
  "qdrant": {
    "status": "healthy",
    "collections": 2,
    "vectors": 45000
  }
}
```

---

## Analytics and Observability Endpoints

### GET /analytics/overview
Get analytics overview.

**Response:**
```json
{
  "today_requests": 342,
  "week_requests": 2145,
  "month_requests": 9234,
  "total_cost_usd": 45.23,
  "avg_latency_ms": 1234
}
```

---

### GET /analytics/usage
Get usage metrics by date range.

**Query Parameters:**
- `start_date`: YYYY-MM-DD
- `end_date`: YYYY-MM-DD

**Response:**
```json
[
  {
    "date": "2024-04-12",
    "total_requests": 342,
    "total_tokens": 125000,
    "total_cost_usd": 2.50,
    "avg_latency_ms": 1245,
    "error_count": 2
  }
]
```

---

### GET /analytics/models
Get model usage breakdown.

**Response:**
```json
{
  "models": [
    {
      "model": "gpt-4-turbo",
      "usage_count": 234,
      "total_cost": 45.60,
      "avg_latency_ms": 1450
    },
    {
      "model": "claude-3-opus",
      "usage_count": 108,
      "total_cost": 12.45,
      "avg_latency_ms": 980
    }
  ]
}
```

---

### GET /analytics/observability
Get AI decision logs.

**Query Parameters:**
- `skip`, `limit`

**Response:**
```json
[
  {
    "id": "log-001",
    "message_id": "msg-789",
    "intent": "chat",
    "model_selected": "gpt-4-turbo",
    "confidence_score": 0.92,
    "tools_considered": ["send_email", "search"],
    "tool_selected": null,
    "latency_ms": 1234,
    "cost_usd": 0.045,
    "created_at": "2024-04-12T10:00:00Z"
  }
]
```

---

## SDK Endpoints

### POST /sdk/init
Initialize chat session for embedded widget.

**Response:**
```json
{
  "session_id": "sess-xyz123",
  "expires_in": 2592000,
  "config": {
    "bot_name": "RAZE AI",
    "welcome_message": "Hi! How can I help?",
    "theme": {
      "primary_color": "#7C3AED"
    }
  }
}
```

---

### POST /sdk/message
Send message via SDK (non-streaming).

**Request:**
```json
{
  "session_id": "sess-xyz123",
  "message": "Hello RAZE"
}
```

**Response:**
```json
{
  "message_id": "msg-001",
  "content": "Hello! I'm RAZE assistant...",
  "timestamp": "2024-04-12T10:00:00Z"
}
```

---

### POST /sdk/stream
Stream response via SDK (Server-Sent Events).

**Request:**
```json
{
  "session_id": "sess-xyz123",
  "message": "Tell me about RAZE"
}
```

**Response (SSE):**
```
data: {"type":"text","content":"RAZE"}
data: {"type":"text","content":" is"}
data: {"type":"text","content":" an"}
...
data: {"type":"done","message_id":"msg-001"}
```

---

### GET /sdk/config
Get public SDK configuration.

**Response:**
```json
{
  "bot_name": "RAZE AI",
  "welcome_message": "Welcome!",
  "theme": {
    "primary_color": "#7C3AED",
    "text_color": "#1F2937"
  },
  "supported_features": [
    "streaming",
    "file_upload",
    "tool_execution"
  ]
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "status_code": 400,
  "timestamp": "2024-04-12T10:00:00Z"
}
```

### Common Status Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error

---

## WebSocket Streaming

For real-time conversation, you can use WebSocket on `/ws/chat` endpoint:

```javascript
const ws = new WebSocket('ws://localhost/api/v1/ws/chat');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log(message);
};

ws.send(JSON.stringify({
  type: 'message',
  content: 'Hello'
}));
```

---

## Rate Limiting Headers

All responses include:
- `X-RateLimit-Limit`: 100
- `X-RateLimit-Remaining`: 95
- `X-RateLimit-Reset`: 1712156430

---

## Pagination

List endpoints support pagination:

```bash
curl http://localhost/api/v1/conversations?skip=0&limit=10
```

---

## Filtering and Sorting

Most list endpoints support:
- `sort_by`: field to sort by
- `sort_order`: asc or desc
- Endpoint-specific filters (see each endpoint)

---

For more information, visit the [RAZE Documentation](https://raze.example.com/docs)
