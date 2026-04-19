# RAZE Database Migration Setup

## Overview

The RAZE system now uses **Alembic database migrations** to automatically set up and maintain database schema on fresh Docker deployments. This ensures:
- ✅ No manual SQL commands needed
- ✅ Proper version control of schema changes
- ✅ Safe rollbacks with downgrade support
- ✅ Works on fresh deployments without configuration

## How It Works

### Fresh Deployment Flow

When you run `docker-compose up` on a fresh setup:

1. **PostgreSQL starts** and becomes healthy
2. **Backend service waits** for PostgreSQL health check
3. **db-init.sh runs** before the app starts:
   - Waits for PostgreSQL to be fully ready
   - Extracts database credentials from `DATABASE_URL`
   - Converts async URL to sync URL for Alembic
   - Runs `alembic upgrade head` to apply all pending migrations
4. **Backend app starts** with fully initialized schema
5. **main.py lifespan startup** initializes default AppSettings

### Migration Files

**Location**: `/opt/raze/backend/alembic/versions/`

| Revision | File | Purpose |
|----------|------|---------|
| 001 | `001_initial_schema.py` | Mark initial version (tables created by ORM) |
| 002 | `002_add_app_settings.py` | Create `app_settings` table with branding/feature flags |
| 003 | `003_add_web_search_settings.py` | Add `web_search_engine`, `web_search_max_results`, `include_web_search_in_chat` columns |

## Configuration Files

### Updated Files

1. **`/opt/raze/backend/Dockerfile`**
   - Copies `db-init.sh` into container
   - Changed CMD to run `db-init.sh` before starting uvicorn

2. **`/opt/raze/docker/db-init.sh`** (new)
   - Waits for PostgreSQL health
   - Extracts DB credentials from `DATABASE_URL`
   - Runs Alembic migrations
   - Detailed logging for debugging

3. **`/opt/raze/backend/alembic/env.py`**
   - Updated to read `SQLALCHEMY_URL` env var (for container)
   - Falls back to `settings.sync_database_url` (for local development)
   - Converts async PostgreSQL URLs to sync (psycopg2)

4. **`/opt/raze/backend/alembic.ini`**
   - Cleared `sqlalchemy.url` (now provided at runtime)

## Environment Variables

All needed variables are automatically set by `docker-compose.yml`:

```bash
DATABASE_URL=postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@postgres:5432/{POSTGRES_DB}
POSTGRES_USER=raze
POSTGRES_PASSWORD={from .env}
POSTGRES_DB=raze
```

The `db-init.sh` script extracts and converts these automatically.

## Local Development

### Running Migrations Locally

```bash
cd /opt/raze/backend

# Install dependencies
pip install -r requirements.txt

# Ensure PostgreSQL is running and DATABASE_URL is set
export DATABASE_URL="postgresql+psycopg2://raze:password@localhost:5432/raze"

# Apply all pending migrations
alembic upgrade head

# Check current migration status
alembic current

# View migration history
alembic history
```

### Creating New Migrations

When you add new fields to models:

```bash
cd /opt/raze/backend

# Auto-generate migration (compares ORM to current schema)
alembic revision --autogenerate -m "Add new feature columns"

# Review the generated file in alembic/versions/
# Edit if needed to ensure correctness

# Apply it
alembic upgrade head
```

### Rolling Back Migrations

```bash
# Go back one migration
alembic downgrade -1

# Go back to specific revision
alembic downgrade 002

# Go back to initial
alembic downgrade base
```

## Verification

### Check Migration Status in Running Container

```bash
# View current migration
docker exec raze_backend alembic current

# View migration history
docker exec raze_backend alembic history

# View all heads
docker exec raze_backend alembic heads
```

### Check Database Schema

```bash
# Connect to PostgreSQL
docker exec -it raze_postgres psql -U raze -d raze

# List tables
\dt

# Describe app_settings table
\d app_settings

# Check web_search columns exist
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_name = 'app_settings' AND column_name LIKE 'web_search%';
```

## Troubleshooting

### Issue: "alembic_version" table doesn't exist

**Symptom**: Migration fails with "relation 'alembic_version' does not exist"

**Cause**: PostgreSQL was not ready when migration ran

**Fix**:
```bash
docker-compose down -v
docker-compose up
# Wait for all services to start
```

### Issue: "column already exists"

**Symptom**: Migration 003 fails with "column web_search_engine already exists"

**Cause**: Migrations were partially applied or manual SQL was run

**Fix**:
```bash
# Check current migration status
docker exec raze_backend alembic current

# If stuck, manually set version (use with caution)
docker exec raze_backend alembic stamp 003
```

### Issue: Database won't start on fresh deployment

**Symptom**: Backend stuck waiting for PostgreSQL

**Cause**: Database initialization taking too long

**Fix**:
```bash
# Check PostgreSQL logs
docker logs raze_postgres

# Increase timeout in docker-compose.yml:
# Change "retries: 5" to "retries: 10" for postgres healthcheck

# If stuck, restart
docker-compose restart
```

## Testing Fresh Deployment

To verify migrations work on a completely fresh setup:

```bash
# Clean everything
docker-compose down -v

# Remove any cached containers
docker system prune

# Fresh start - migrations should run automatically
docker-compose up

# Check logs
docker logs raze_backend | grep -E "migration|upgrade|Alembic"

# Verify schema
docker exec raze_postgres psql -U raze -d raze -c "\d app_settings"
```

## Migration Best Practices

1. **Always use migrations** - never manually modify schema
2. **Review generated migrations** - `autogenerate` can make mistakes
3. **Test locally first** - before merging to main
4. **Keep migrations small** - one logical change per migration
5. **Document rationale** - add comments to migration docstrings if schema change is not obvious
6. **Never edit past migrations** - create new ones instead

## Security

- Alembic files contain no secrets (URL provided at runtime)
- Database credentials come from environment variables
- `db-init.sh` is run with `raze` user (non-root)
- PostgreSQL credentials not logged in docker-compose.yml

## Performance

Migrations are designed to be fast:
- Minimal DDL operations
- No data transformations
- Parallel table creation (PostgreSQL handles this)
- Typical fresh deployment migration time: < 1 second

## Next Steps

1. ✅ Fresh deployment - migrations run automatically
2. ✅ Knowledge base works end-to-end without manual SQL
3. ✅ No column undefined errors on fresh setup
4. When adding new columns:
   - Update the ORM model in `/opt/raze/backend/app/models/`
   - Run `alembic revision --autogenerate -m "description"`
   - Test locally, commit, push, deploy (migrations run automatically)
