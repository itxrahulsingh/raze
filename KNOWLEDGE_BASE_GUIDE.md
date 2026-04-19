# Knowledge Base Complete Guide

## What are the Flags? (Clarification)

### `can_use_in_knowledge` (✅ WORKING)
- **What it does**: Controls if this source is included in semantic search for knowledge retrieval
- **When enabled**: Knowledge search will find and return this source's content
- **When disabled**: This source is completely excluded from knowledge search, even if it's active
- **Example**: Disable for sources that should NOT be used to answer user questions

### `can_use_in_chat` (✅ WORKING)  
- **What it does**: Controls if AI gets access to this source's content during chat
- **When enabled**: AI can use this knowledge to improve answers
- **When disabled**: AI won't receive this source's content in the context window
- **Example**: Enable for important internal docs, disable for drafts/incomplete docs

### `can_use_in_search` (✅ WORKING)
- **What it does**: Controls if this source appears in semantic search results for exploration
- **When enabled**: Users can find this source through search UI
- **When disabled**: Hidden from search UI, but might still be used in chat if `can_use_in_chat` is enabled
- **Example**: Enable for public docs, disable for confidential sources

### `is_active` (✅ WORKING)
- **What it does**: Master on/off switch for the entire source
- **When enabled**: Source can be used in knowledge, chat, and search (if those flags allow)
- **When disabled**: Source is completely disabled everywhere
- **Example**: Turn off for archived/outdated sources

---

## Status States

### `pending`
- Source uploaded but not yet approved
- Won't be used in any operations until approved
- Requires admin approval (if enabled in settings)

### `approved`
- Source is approved and ready to use
- Will be processed and chunks extracted
- Available in knowledge, chat, and search based on individual flags

### `processing`
- Source is currently being ingested (extracting chunks, creating embeddings)
- Not yet available for use

### `failed`
- Source failed during processing
- **Common reasons**:
  - File upload corruption
  - Unsupported file format
  - Processing error
  - Missing content
- **Solution**: Delete and re-upload the source

### `rejected`
- Source was explicitly rejected by admin
- Won't be used anywhere
- Can be re-submitted for approval

---

## How Sources Get Processed

```
Upload File/Create Content
        ↓
File Validation (format, size, content)
        ↓
Create KnowledgeSource record (status: processing)
        ↓
Extract Text/Content
        ↓
Split into Chunks (with context)
        ↓
Generate Embeddings (768-dim vectors via Ollama)
        ↓
Store Chunks in Qdrant Vector DB
        ↓
Update Status (approved/failed)
        ↓
Ready for Use
```

---

## Complete Feature Matrix

| Feature | Document | Article | Chat Session | CSV | JSON |
|---------|----------|---------|--------------|-----|------|
| Upload via UI | ✅ | ✅ | Auto | ✅ | ✅ |
| Extract Text | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create Chunks | ✅ | ✅ | ✅ | ✅ | ✅ |
| Embed & Index | ✅ | ✅ | ✅ | ✅ | ✅ |
| Search Knowledge | ✅ | ✅ | ✅ | ✅ | ✅ |
| Use in Chat | ✅ | ✅ | ✅ | ✅ | ✅ |
| Categorize | ✅ | ✅ | ✅ | ✅ | ✅ |
| Add Metadata | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## API Examples

### Enable for Chat Only (Disable Search)
```bash
curl -X PUT "http://localhost/api/v1/knowledge/sources/{id}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "can_use_in_chat": true,
    "can_use_in_search": false,
    "can_use_in_knowledge": true
  }'
```

### Disable Source Temporarily
```bash
curl -X PUT "http://localhost/api/v1/knowledge/sources/{id}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

### Check Source Status
```bash
curl "http://localhost/api/v1/knowledge/sources/{id}" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Troubleshooting

### Status Shows "failed"
1. Check file was uploaded correctly
2. Verify file format is supported
3. Re-upload the source
4. Check backend logs for detailed error

### Shows 0 Chunks
1. If `status=approved`: Chunks may still be processing, wait a few seconds
2. If `status=pending`: Wait for admin approval
3. If `status=failed`: Source needs to be re-uploaded

### Source Not Used in Chat
1. Check `is_active = true`
2. Check `can_use_in_chat = true`
3. Check source status is `approved`
4. Ensure chunks were successfully created

### Can't Find in Search
1. Check `is_active = true`
2. Check `can_use_in_search = true`
3. Verify source has chunks (process completed)
4. Try exact phrase match in search

---

## Settings & Configuration

### Knowledge Base Settings
```json
{
  "enable_knowledge_base": true,
  "require_source_approval": false,
  "auto_approve_sources": true,
  "max_file_size_mb": 50,
  "max_chunks_per_source": 1000,
  "enabled_categories": [
    "document", "article", "chat_session", "code", "data"
  ]
}
```

### Performance Notes
- **Embedding generation**: ~100ms per chunk (using local Ollama)
- **Semantic search**: ~200ms per query (across all sources)
- **Chat integration**: Knowledge added to context without latency

---

## Multi-Language Support

All features work in any language:
- **Text extraction**: Arabic, Chinese, Japanese, etc.
- **Semantic search**: Cross-lingual similarity
- **AI understanding**: Full language support via Ollama

Example:
```bash
# Arabic
curl -X POST "/api/v1/knowledge/sources" \
  -F "file=@arabic-document.pdf" \
  -F "name=وثيقة مهمة"

# Chinese  
curl -X POST "/api/v1/knowledge/sources" \
  -F "file=@chinese-document.docx" \
  -F "name=重要文档"
```

---

## Web Search Integration

**Current Status**: Not yet implemented

When enabled (future release), the system will:
1. Detect when AI needs current information
2. Automatically search the web
3. Retrieve latest information
4. Cite sources in response

---

## Browser Configuration

### Page Title (Browser Tab)
- Currently: "RAZE - Admin"
- Can be customized via:
  - White label settings
  - Environment variables
  - Database configuration

### Browser Tab Title During Chat
- Shows current conversation title
- Updates automatically when title changes
- Helps with tab organization

---

**Last Updated**: 2026-04-19  
**Status**: All core features operational
