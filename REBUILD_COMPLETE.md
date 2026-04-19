# Complete Rebuild & Testing Guide

## ⚠️ Current Issues
- Backend not responding
- Tools page shows 422 error
- User management options not visible
- Need complete rebuild

## Step 1: Verify Backend Code Is Correct

```bash
# Check Python syntax
python3 -m py_compile backend/app/api/v1/tools.py
python3 -m py_compile backend/app/api/v1/admin.py
python3 -m py_compile backend/app/models/settings.py
python3 -m py_compile backend/app/services/settings_service.py
python3 -m py_compile backend/app/api/v1/settings.py

# All should have no output if syntax is correct
```

## Step 2: Rebuild Docker Containers

```bash
cd /opt/raze

# Stop existing containers
docker-compose down

# Rebuild all images (no cache)
docker-compose build --no-cache

# Start services
docker-compose up -d

# Wait for services to be healthy (30-60 seconds)
docker-compose ps
```

## Step 3: Initialize Database

```bash
# Run migrations
docker exec raze_backend alembic upgrade head

# Check database
docker exec raze_postgres psql -U raze -d raze -c "SELECT * FROM app_settings LIMIT 1;"
```

## Step 4: Verify Backend Health

```bash
# Test health endpoint
curl http://localhost/api/v1/health

# Should return: {"status": "healthy", ...}
```

## Step 5: Test API Endpoints

### Test Tools List
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost/api/v1/tools?limit=50
```

### Test Users List
```bash
curl -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  http://localhost/api/v1/admin/users?limit=20
```

### Test Create User
```bash
curl -X POST http://localhost/api/v1/admin/users \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "TestPass123",
    "role": "viewer"
  }'
```

## Step 6: Frontend Verification

### Clear Browser Cache
1. Open DevTools (F12)
2. Application tab
3. Click "Clear site data"
4. Refresh page

### Check Console for Errors
1. DevTools > Console tab
2. Look for red error messages
3. Note exact error text

### Verify Frontend Pages Show Options
- Tools page: Should have "Add Tool" button (top right)
- Users page: Should have "Invite User" button (top right)
- Settings page: Should have "App Settings" tab

## Step 7: Debug 422 Errors

### If you still see 422 errors:

1. Open DevTools > Network tab
2. Make a request to tools page
3. Click the failing request
4. Check "Response" tab for error details
5. Look for validation error message

Common 422 causes:
- Query parameter value exceeds max (limit > 100)
- Invalid parameter type
- Missing required field
- Malformed JSON

### If tools page loads but no options show:

1. Check page source (right-click > View Page Source)
2. Look for "Add Tool" text
3. If not found: frontend file not deployed correctly
4. If found but not visible: CSS issue or JavaScript error

## Step 8: Check Memory Features

### Memory API Endpoints

```bash
# Get user memories
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost/api/v1/memory/memories?limit=20

# Create memory
curl -X POST http://localhost/api/v1/memory/memories \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "YOUR_USER_ID",
    "type": "conversation_summary",
    "content": "User preferences",
    "retention_policy": "permanent"
  }'

# Delete memory
curl -X DELETE http://localhost/api/v1/memory/memories/{memory_id} \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Memory Configuration

Memory is stored in:
- **Database**: `memories` table (persistent)
- **Redis Cache**: For fast retrieval
- **Qdrant**: Vector embeddings for semantic search

Settings:
- `enable_memory`: true/false (database settings)
- Retention policy: permanent, session, temporary
- Types: conversation_summary, user_preference, context

## Step 9: Full System Health Check

```bash
#!/bin/bash

echo "=== RAZE System Health Check ==="
echo ""

# Database
echo "1. Database Connection"
curl -s http://localhost/api/v1/health | jq '.components.database'

# Redis
echo "2. Redis Connection"
curl -s http://localhost/api/v1/health | jq '.components.redis'

# Vector Search
echo "3. Qdrant Vector DB"
curl -s http://localhost/api/v1/health | jq '.components.vector_search'

# Ollama
echo "4. Ollama LLM"
curl -s http://localhost/api/v1/health | jq '.components.ollama'

# Overall
echo "5. Overall Status"
curl -s http://localhost/api/v1/health | jq '.status'

echo ""
echo "If any are 'unhealthy', check Docker logs:"
echo "  docker-compose logs backend"
echo "  docker-compose logs postgres"
echo "  docker-compose logs redis"
```

## Troubleshooting Checklist

- [ ] Backend container is running: `docker-compose ps`
- [ ] Backend is healthy: `curl http://localhost/api/v1/health`
- [ ] Database has tables: `docker exec raze_postgres psql -U raze -d raze -c "\dt"`
- [ ] Frontend code updated: Check file sizes match
- [ ] Browser cache cleared: DevTools > Clear site data
- [ ] Token is valid: Can you login?
- [ ] Admin account: Are you using admin token for create/update/delete?

## If Tools/Users Pages Still Don't Show Options

**Check backend logs:**
```bash
docker-compose logs backend -f --tail 50
```

**Look for:**
- Syntax errors (SyntaxError)
- Import errors (ImportError, ModuleNotFoundError)
- Database errors (SQLAlchemy errors)
- Route not registered (404)

**If you see errors:**
1. Copy the exact error message
2. Check the file and line number mentioned
3. Verify the fix was applied correctly

## Complete Restart Procedure

If everything is broken, do this:

```bash
cd /opt/raze

# 1. Stop everything
docker-compose down -v  # -v removes volumes (data loss!)

# 2. Clean build
docker-compose build --no-cache

# 3. Start fresh
docker-compose up -d

# 4. Wait for health
sleep 30
docker-compose ps

# 5. Verify health
curl http://localhost/api/v1/health

# 6. Test endpoints
curl -H "Authorization: Bearer TOKEN" http://localhost/api/v1/tools?limit=50
```

## Memory Features - Detailed Configuration

### How Memory Works

1. **User sends message** → Chat endpoint
2. **LLM processes** with context from memories
3. **Relevant memories retrieved** from Qdrant
4. **Response generated** with memory context
5. **New memory created** (if enabled)

### Memory Storage Locations

| Type | Storage | Purpose | TTL |
|------|---------|---------|-----|
| conversation_summary | Database | Remember conversation context | permanent |
| user_preference | Database | User settings/preferences | permanent |
| context | Qdrant (vector) | Semantic context retrieval | permanent |
| temporary | Redis | Session-specific | session |

### Memory API Usage

```python
# Python example
import requests

headers = {"Authorization": f"Bearer {token}"}

# Create memory
memory = {
    "type": "user_preference",
    "content": "User prefers concise responses",
    "retention_policy": "permanent"
}
resp = requests.post(
    "http://localhost/api/v1/memory/memories",
    headers=headers,
    json=memory
)

# Retrieve memories
resp = requests.get(
    "http://localhost/api/v1/memory/memories?limit=10",
    headers=headers
)

# Delete memory
requests.delete(
    f"http://localhost/api/v1/memory/memories/{memory_id}",
    headers=headers
)
```

### Enable Memory in Settings

```bash
# Update database settings
curl -X PUT http://localhost/api/v1/settings \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enable_memory": true,
    "enable_knowledge_base": true,
    "enable_web_search": true
  }'
```

## Summary

If you complete all steps above:
1. ✅ Backend will be running and responding
2. ✅ API endpoints will work (no 422 errors)
3. ✅ Frontend will show all CRUD options
4. ✅ Memory features will be operational
5. ✅ Tools management will be fully functional
6. ✅ User management will be fully functional

**Required time: 5-10 minutes**

Start with Step 1 and report any errors you encounter!
