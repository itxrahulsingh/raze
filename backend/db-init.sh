#!/bin/bash
set -e

echo "=========================================="
echo "Database Initialization Script"
echo "=========================================="

# Extract PostgreSQL connection details from DATABASE_URL
# DATABASE_URL format: postgresql+asyncpg://user:password@host:port/database
# We need to convert this to psycopg2 format for Alembic/psycopg2-based CLI tools

if [ -z "$DATABASE_URL" ]; then
  echo "ERROR: DATABASE_URL environment variable not set"
  exit 1
fi

echo "Database URL detected: ${DATABASE_URL:0:50}..."

# Convert asyncpg URL to psycopg2 for Alembic/psycopg2-based CLI tools
SYNC_DATABASE_URL=$(echo "$DATABASE_URL" | sed 's/postgresql+asyncpg:\/\//postgresql+psycopg2:\/\//')

# Extract individual components for health check
# postgresql+psycopg2://user:password@host:port/database
DB_USER=$(echo "$SYNC_DATABASE_URL" | sed -E 's|.*://([^:]+):.*|\1|')
DB_PASSWORD=$(echo "$SYNC_DATABASE_URL" | sed -E 's|.*://[^:]+:([^@]+)@.*|\1|')
DB_HOST=$(echo "$SYNC_DATABASE_URL" | sed -E 's|.*@([^:]+):.*|\1|')
DB_PORT=$(echo "$SYNC_DATABASE_URL" | sed -E 's|.*:([0-9]+)/.*|\1|')
DB_NAME=$(echo "$SYNC_DATABASE_URL" | sed -E 's|.*/(.+)$|\1|')

echo "Extracted DB connection: host=$DB_HOST port=$DB_PORT user=$DB_USER database=$DB_NAME"

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
max_attempts=30
attempt=0
until PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "SELECT 1" 2>/dev/null; do
  attempt=$((attempt + 1))
  if [ $attempt -ge $max_attempts ]; then
    echo "ERROR: PostgreSQL failed to become ready after $max_attempts attempts"
    exit 1
  fi
  echo "PostgreSQL not ready yet, retrying... (attempt $attempt/$max_attempts)"
  sleep 2
done

echo "✓ PostgreSQL is ready"

# Alembic migrations - skip automatic run since app ORM creates tables on startup
# Tables are created by the application startup using ORM metadata
echo "✓ Tables will be created by application ORM on startup"

echo "=========================================="
echo "Database initialization complete"
echo "=========================================="
