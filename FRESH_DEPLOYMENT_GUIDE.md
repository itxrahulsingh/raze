# Fresh Deployment Testing Guide

This guide walks through testing the complete fresh deployment workflow with automatic Alembic migrations.

## What Was Implemented

✅ **Automatic Database Migrations** - Alembic migrations run automatically on fresh deployment  
✅ **Zero Manual SQL** - All schema setup happens via proper migrations  
✅ **Fresh Deployment Support** - Works on completely fresh Docker deploys  
✅ **Proper Version Control** - All schema changes tracked in version control  

## Files Changed/Created

### Modified
- `/opt/raze/backend/Dockerfile` - Added db-init.sh execution
- `/opt/raze/backend/alembic/env.py` - Support for SQLALCHEMY_URL environment variable
- `/opt/raze/backend/alembic.ini` - Cleared default sqlalchemy.url
- `/opt/raze/ADVANCED_SETUP.md` - Added migration section

### Created
- `/opt/raze/backend/db-init.sh` - Database initialization script
- `/opt/raze/MIGRATION_SETUP.md` - Comprehensive migration documentation
- `/opt/raze/MIGRATION_CHANGES.md` - Implementation summary

## Testing Workflow

### Step 1: Clean Everything
```bash
docker-compose down -v
docker system prune -a
```

### Step 2: Fresh Start with Migrations
```bash
docker-compose up --build
# Wait for db-init.sh to complete, then all services to be healthy
```

### Step 3: Verify Migrations
```bash
# Check logs
docker logs raze_backend | grep -E "Database|migration|upgrade"

# Check current migration
docker exec raze_backend alembic current

# Check history
docker exec raze_backend alembic history
```

### Step 4: Verify Database
```bash
# Connect to database
docker exec -it raze_postgres psql -U raze -d raze

# Check app_settings table
\d app_settings

# Verify web_search columns
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'app_settings' 
AND column_name LIKE 'web_search%';

# Check default record
SELECT brand_name, web_search_engine FROM app_settings;

# Exit
\q
```

## Expected Results

✅ Backend starts without errors  
✅ "alembic current" shows "003_add_web_search_settings"  
✅ Database has all required columns  
✅ app_settings record has defaults  
✅ Knowledge base works end-to-end  
✅ No "undefined column" errors  

## Documentation

- **Full details**: [MIGRATION_SETUP.md](./MIGRATION_SETUP.md)
- **Implementation**: [MIGRATION_CHANGES.md](./MIGRATION_CHANGES.md)
- **Setup**: [ADVANCED_SETUP.md](./ADVANCED_SETUP.md)
