# Settings Management Implementation

## Overview
Centralized configuration management has been implemented to eliminate repeated API calls and provide a single source of truth for all application settings.

## What Was Implemented

### 1. Database Model (`/opt/raze/backend/app/models/settings.py`)
- **AppSettings** table (singleton pattern with id="singleton")
- All branding, page, chat, theme, SDK, and feature flag settings stored in one table
- Fields include:
  - Branding: `brand_name`, `brand_color`, `logo_url`, `favicon_url`
  - Page: `page_title`, `page_description`, `copyright_text`
  - Chat: `chat_welcome_message`, `chat_placeholder`, `enable_suggestions`, `chat_suggestions`
  - Theme: `theme_mode`, `accent_color`
  - SDK: `sdk_api_endpoint`, `sdk_websocket_endpoint`, `sdk_auth_type`
  - Features: `enable_knowledge_base`, `enable_web_search`, `enable_memory`, `enable_voice`
  - Knowledge: `require_source_approval`, `auto_approve_sources`, `max_file_size_mb`
  - Tracking: `updated_at` timestamp

### 2. Service Layer (`/opt/raze/backend/app/services/settings_service.py`)
- **SettingsService** manages AppSettings with Redis caching
- Cache key: `app:settings:singleton` (cached forever, only invalidated on explicit update)
- Methods:
  - `get_all_settings()` - Returns cached settings or fetches from database
  - `update_settings(updates)` - Updates database and invalidates Redis cache
  - `get_setting(key)` - Gets a single setting value
  - `set_setting(key, value)` - Sets a single setting value
  - `reset_to_defaults()` - Resets all settings to defaults

### 3. API Endpoints (`/opt/raze/backend/app/api/v1/settings.py`)
Routes registered at `/api/v1/settings`:
- **GET /settings** - Retrieve all cached settings (all users)
- **GET /settings/{key}** - Retrieve single setting value (all users)
- **PUT /settings** - Update settings (admin/superadmin only)
- **POST /settings/reset** - Reset to defaults (admin/superadmin only)

### 4. Database Migration (`/opt/raze/backend/alembic/versions/002_add_app_settings.py`)
- Creates `app_settings` table with all required columns
- Includes server-side defaults for all fields
- Can be rolled back if needed

### 5. Application Startup
Modified `/opt/raze/backend/app/main.py`:
- Imports settings module to register AppSettings with ORM
- Initializes default AppSettings on startup if none exist
- Includes settings router in FastAPI app

### 6. Database Configuration
Updated `/opt/raze/backend/app/database.py`:
- Added `settings` to model imports for table creation
- AppSettings table created automatically on connect_db()

### 7. Models Registration
Updated `/opt/raze/backend/app/models/__init__.py`:
- Added AppSettings and AppConfig to imports and __all__ exports

## How It Works

### First Run (Table Creation)
1. App starts and calls `connect_db()`
2. Database imports all models including `settings`
3. AppSettings table created automatically (if not exists)
4. Startup initializes with default settings if none exist

### API Usage
```
GET /api/v1/settings
→ Check Redis cache (key: app:settings:singleton)
  → If hit: return cached settings
  → If miss: query database, cache result, return

PUT /api/v1/settings
→ Admin only
→ Update database
→ Invalidate Redis cache
→ Return updated settings

GET /api/v1/settings/{key}
→ Get single setting from cache
```

### Frontend Integration
Frontend should fetch settings once on app load:
```javascript
const settings = await fetch('/api/v1/settings').then(r => r.json());
// Use settings.brand_name, settings.chat_welcome_message, etc.
// Don't call this endpoint repeatedly - settings are cached forever
```

## Configuration Fields Available

### Branding
- `brand_name` - Display name for the application
- `brand_color` - Primary brand color (hex)
- `logo_url` - URL to logo image
- `favicon_url` - URL to favicon

### Page
- `page_title` - Browser page title
- `page_description` - Meta description
- `copyright_text` - Footer copyright text

### Chat
- `chat_welcome_message` - Initial greeting
- `chat_placeholder` - Input placeholder text
- `enable_suggestions` - Show suggestion chips
- `chat_suggestions` - Array of suggestion texts

### Theme
- `theme_mode` - 'dark', 'light', or 'auto'
- `accent_color` - Secondary accent color (hex)

### SDK Configuration
- `sdk_api_endpoint` - API URL for external integrations
- `sdk_websocket_endpoint` - WebSocket URL (optional)
- `sdk_auth_type` - 'bearer' or 'api-key'

### Features
- `enable_knowledge_base` - Enable document search
- `enable_web_search` - Enable web search
- `enable_memory` - Enable conversation memory
- `enable_voice` - Enable voice features

### Knowledge Base
- `require_source_approval` - Require admin approval for uploads
- `auto_approve_sources` - Automatically approve new sources
- `max_file_size_mb` - Maximum file upload size

## Performance Impact

### Before
- Settings API called every second by frontend
- Each call hits database
- Redis not used
- High unnecessary load

### After
- Settings fetched once on app startup
- Cached forever in Redis
- Only database hit when explicitly updated
- Frontend uses cached values

## Testing

### Check Settings Table Exists
```bash
docker exec raze_postgres psql -U raze -d raze -c "SELECT * FROM app_settings;"
```

### Fetch Settings
```bash
curl http://localhost/api/v1/settings
```

### Update Settings (requires auth)
```bash
curl -X PUT http://localhost/api/v1/settings \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"brand_name": "My Custom App", "brand_color": "#FF0000"}'
```

### Reset to Defaults (requires auth)
```bash
curl -X POST http://localhost/api/v1/settings/reset \
  -H "Authorization: Bearer <token>"
```

## Next Steps

1. **Frontend Integration** - Update frontend to call `/api/v1/settings` once on load instead of repeatedly
2. **Admin Panel** - Create admin UI to manage these settings
3. **White-Label** - Remove/deprecate the old white-label API in favor of this unified settings API
4. **Audit Logging** - Add audit logs when settings are modified

## Files Modified/Created

### New Files
- `/opt/raze/backend/app/models/settings.py` - AppSettings model
- `/opt/raze/backend/app/services/settings_service.py` - Settings service
- `/opt/raze/backend/app/api/v1/settings.py` - Settings API endpoints
- `/opt/raze/backend/alembic/versions/002_add_app_settings.py` - Database migration

### Modified Files
- `/opt/raze/backend/app/main.py` - Added settings initialization and router
- `/opt/raze/backend/app/database.py` - Added settings import for table creation
- `/opt/raze/backend/app/models/__init__.py` - Added settings exports
- `/opt/raze/backend/alembic/env.py` - Added settings import for migration discovery

## Status
✅ Implementation complete
✅ Database migration created
✅ API endpoints ready
✅ Caching configured
⏳ Awaiting frontend integration
