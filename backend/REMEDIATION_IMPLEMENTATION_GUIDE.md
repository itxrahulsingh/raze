# RAZE Enterprise AI OS - Remediation Implementation Guide

## Current Status Summary

**Completed Fixes:**
1. ✅ Fixed SQL queries in admin.py (wrapped func.count() in select())
2. ✅ Fixed .dict() → .model_dump() in admin.py
3. ✅ Fixed HTTP status codes in admin.py to use status.HTTP_* constants
4. ✅ Created rate limiter infrastructure (RateLimiter class with decorator support)
5. ✅ Created apply_rate_limit() dependency helper for easy integration
6. ✅ Added date validation in analytics.py with proper error handling
7. ✅ Added Enum-based validation for knowledge.py filter parameters
8. ✅ Applied rate limiting pattern to auth.py login endpoint (example)
9. ✅ Applied rate limiting pattern to auth.py refresh endpoint (example)

**Pending Fixes:**
- Apply rate limiting to remaining 64 endpoints
- Add structured logging to exception handlers
- Fix error handling consistency across all endpoints
- Add pagination input validation to endpoints with skip/limit

---

## Rate Limiting Implementation Pattern

### How to Apply Rate Limiting to an Endpoint

**Step 1: Add Request import**
```python
from fastapi import APIRouter, Depends, HTTPException, Request, status
```

**Step 2: Import the rate limit helper**
```python
from app.api.v1.deps import apply_rate_limit
```

**Step 3: Add Request parameter to endpoint signature**
```python
@router.post("/chat/message")
async def send_message(
    request: Request,  # ADD THIS
    body: ChatMessage,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
```

**Step 4: Call apply_rate_limit at the beginning of the handler**
```python
async def send_message(...):
    # Call this first, before any other logic
    await apply_rate_limit(request, "chat_message", 30, 60, current_user)
    # 30 = requests per minute, 60 = window in seconds
    # Rest of handler logic...
```

### Rate Limit Configuration by Endpoint Category

**Authentication Endpoints (auth.py):**
- `/login` - 5 requests/min (already done ✅)
- `/refresh` - 30 requests/min (already done ✅)
- `/logout` - 30 requests/min
- `/me` (GET) - 30 requests/min
- `/me` (PUT) - 30 requests/min
- `/change-password` - 30 requests/min
- `/api-keys` (POST) - 30 requests/min
- `/api-keys` (GET) - 30 requests/min
- `/api-keys/{id}` (DELETE) - 30 requests/min

**Chat Endpoints (chat.py):**
- `/message` (POST) - 30 requests/min
- `/stream` (WebSocket) - 10 requests/min
- Other chat endpoints - 30 requests/min (7 total endpoints)

**Knowledge Endpoints (knowledge.py):**
- `/sources` (POST - upload) - 10 requests/min
- `/sources` (GET - list) - 120 requests/min
- `/sources/{id}` - 120 requests/min
- `/sources/{id}/approve` - 30 requests/min
- `/sources/{id}/reject` - 30 requests/min
- `/sources/{id}/reprocess` - 10 requests/min
- `/search` (POST) - 120 requests/min
- `/sources/{id}/chunks` (GET) - 120 requests/min
- `/chunks/{id}` (PUT, DELETE) - 30 requests/min (11 total endpoints)

**Memory Endpoints (memory.py):**
- Most memory operations - 30 requests/min (8 endpoints)

**Tools Endpoints (tools.py):**
- Tool create/update - 30 requests/min
- Tool test - 10 requests/min
- Tool execute - 30 requests/min (8 endpoints)

**Admin Endpoints (admin.py):**
- All admin operations - 120 requests/min (9 endpoints)

**Analytics Endpoints (analytics.py):**
- All analytics queries - 120 requests/min (10 endpoints)

**SDK Endpoints (sdk.py):**
- All SDK operations - 10 requests/min per API key (4 endpoints)

---

## Quick Application Guide for Each File

### auth.py ✅ (9 endpoints - 2 DONE, 7 TODO)
Already applied to: login, refresh
To apply to: logout, /me (GET), /me (PUT), change-password, api-keys (POST), api-keys (GET), api-keys DELETE

### knowledge.py (11 endpoints)
Pattern:
```python
@router.post("/sources")
async def create_knowledge_source(
    file: UploadFile | None = File(default=None),
    request: Request,  # ADD
    name: str = Form(..., min_length=1, max_length=512),
    # ... other params
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await apply_rate_limit(request, "knowledge_upload", 10, 60, current_user)
    # ... rest of handler
```

### chat.py (7 endpoints)
Apply 30 requests/min to most, 10 requests/min to streaming endpoint

### memory.py (8 endpoints)
Apply 30 requests/min to all endpoints

### tools.py (8 endpoints)
Apply 30 requests/min to most, 10 requests/min to tool_test endpoint

### admin.py (9 endpoints - partially done)
Apply 120 requests/min to all endpoints
Note: Ensure all admin endpoints have `Depends(deps.get_current_admin)` requirement

### analytics.py (10 endpoints)
Apply 120 requests/min to all endpoints

### sdk.py (4 endpoints)
Apply 10 requests/min to all endpoints (per API key)

---

## Exception Handling and Structured Logging

### Current Pattern (Keep Consistent)
```python
try:
    # Do something
except Exception as exc:
    logger.exception("operation_name", error=str(exc), context="additional_info")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Descriptive error message"
    )
```

### Locations Needing Fixes
- knowledge.py line 112 - Add structured logging to except blocks
- llm_router.py line 116 - Add structured logging to except blocks

### Pattern for All HTTPExceptions
```python
# BEFORE:
raise HTTPException(status_code=404)

# AFTER:
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Resource not found - specific message"
)
```

---

## Pagination Validation Pattern

### Apply to All Endpoints with skip/limit Parameters

**Endpoints needing pagination validation:**
- memory.py: list memories, get memories
- tools.py: list tools, list executions
- chat.py: list conversations, list messages
- knowledge.py: list sources, list chunks
- analytics.py: several analytics endpoints
- admin.py: list users

### Implementation Pattern
```python
@router.get("/resources")
async def list_resources(
    skip: int = Query(0, ge=0, le=1000, description="Records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Records to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # The Query validation is now automatic!
    result = await db.execute(
        select(Model).offset(skip).limit(limit)
    )
    return result.scalars().all()
```

---

## Additional Validation Schemas to Create/Update

### 1. backend/app/schemas/auth.py
- ✅ PasswordChangeRequest: Already has 8-char min and uppercase+digit validators
- Add: Symbol requirement validator
- Add: API key rate_limit validation (1-10000)

### 2. backend/app/schemas/knowledge.py
- Add: KnowledgeSearchRequest with query length (1-1000) and limit (max 100)
- Add: Tag validators (max 20 tags, each max 50 chars)

### 3. backend/app/schemas/memory.py
- Add: MemorySearchRequest with query validation
- Add: MemoryCreate with content length and importance (0-1) validators

### 4. backend/app/schemas/tools.py
- Add: ToolCreate with valid URL validation and method validation
- Add: ToolExecutionTest with input_data validation

### 5. backend/app/schemas/admin.py
- Add: AIConfigCreate/Update validators for temperature (0-2), max_tokens (1-4096), top_p (0-1)

### 6. backend/app/schemas/sdk.py
- Add: SDKInitRequest with API key format validation

---

## Testing Rate Limiting

```bash
# Test rate limiting on a single endpoint
for i in {1..35}; do
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"password"}' \
    -w "Status: %{http_code}\n" \
    -s > /dev/null
  if [ $i -eq 30 ]; then
    echo "Request 30 completed - next should be rate limited (429)"
  fi
done
# Should get 429 after ~30 requests within 1 minute
```

---

## Implementation Checklist

### Phase 1: Rate Limiting (IN PROGRESS)
- [x] Create RateLimiter infrastructure
- [x] Create apply_rate_limit helper
- [x] Apply to auth.py endpoints (2 of 9)
- [ ] Apply to knowledge.py endpoints (0 of 11)
- [ ] Apply to chat.py endpoints (0 of 7)
- [ ] Apply to memory.py endpoints (0 of 8)
- [ ] Apply to tools.py endpoints (0 of 8)
- [ ] Apply to admin.py endpoints (0 of 9)
- [ ] Apply to analytics.py endpoints (0 of 10)
- [ ] Apply to sdk.py endpoints (0 of 4)

### Phase 2: Exception Handling (TODO)
- [ ] Add logger.exception() to knowledge.py
- [ ] Add logger.exception() to llm_router.py
- [ ] Add logger.exception() to all other files as needed

### Phase 3: Status Codes (TODO)
- [ ] Replace all hardcoded status codes with status.HTTP_* constants
- [ ] Add specific detail messages to all HTTPExceptions

### Phase 4: Pagination Validation (TODO)
- [ ] Add Query validators to all skip/limit parameters
- [ ] Ensure max limits are enforced

### Phase 5: Input Validation (TODO)
- [ ] Add validators to all new schemas
- [ ] Update endpoints to use new schemas

---

## Database Optimization (Phase 5 - Not Critical for Now)

Indexes to add via Alembic migration:
```python
# Priority 1 (CRITICAL)
CREATE INDEX ix_knowledge_sources_approved_by ON knowledge_sources(approved_by);
CREATE INDEX ix_memories_source_conversation_id ON memories(source_conversation_id);
CREATE INDEX ix_tool_executions_message_id ON tool_executions(message_id);
CREATE INDEX ix_conversations_ai_config_id ON conversations(ai_config_id);

# Priority 2 (HIGH)
CREATE INDEX ix_observability_logs_conversation_message ON observability_logs(conversation_id, message_id);
CREATE INDEX ix_tool_executions_tool_conversation ON tool_executions(tool_id, conversation_id);
CREATE INDEX ix_memories_user_session_active ON memories(user_id, session_id, is_active);
CREATE INDEX ix_knowledge_chunks_source_created ON knowledge_chunks(source_id, created_at);
```

---

## Next Steps

1. **Apply rate limiting systematically** to all 66 endpoints using the pattern shown above
2. **Add structured logging** to exception handlers in knowledge.py and llm_router.py
3. **Fix pagination validation** on all affected endpoints
4. **Add input validators** to all schemas as specified
5. **Ensure all status codes** use HTTP_* constants

Total remaining effort: ~4-6 hours for systematic application of patterns to all endpoints

---

## Files Modified So Far

- `/Users/rahul/Development/raze/backend/app/api/v1/admin.py` - Fixed SQL, status codes, .dict()
- `/Users/rahul/Development/raze/backend/app/core/security.py` - Added rate limiter decorators
- `/Users/rahul/Development/raze/backend/app/api/v1/deps.py` - Added apply_rate_limit helper
- `/Users/rahul/Development/raze/backend/app/api/v1/analytics.py` - Added date validation
- `/Users/rahul/Development/raze/backend/app/api/v1/knowledge.py` - Added Enum validation
- `/Users/rahul/Development/raze/backend/app/api/v1/auth.py` - Added rate limiting to login/refresh

## Files Needing Updates

- `/Users/rahul/Development/raze/backend/app/api/v1/auth.py` - 7 more endpoints
- `/Users/rahul/Development/raze/backend/app/api/v1/knowledge.py` - 11 endpoints
- `/Users/rahul/Development/raze/backend/app/api/v1/chat.py` - 7 endpoints
- `/Users/rahul/Development/raze/backend/app/api/v1/memory.py` - 8 endpoints
- `/Users/rahul/Development/raze/backend/app/api/v1/tools.py` - 8 endpoints
- `/Users/rahul/Development/raze/backend/app/api/v1/analytics.py` - 10 endpoints
- `/Users/rahul/Development/raze/backend/app/api/v1/sdk.py` - 4 endpoints
- `/Users/rahul/Development/raze/backend/app/core/llm_router.py` - Exception handling
- All schemas in `/Users/rahul/Development/raze/backend/app/schemas/` - Add validators

