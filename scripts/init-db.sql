-- =============================================================================
-- RAZE Enterprise AI OS — PostgreSQL initialization
-- =============================================================================
-- This file is executed automatically when the postgres container starts
-- for the first time (via docker-entrypoint-initdb.d/).
-- =============================================================================

-- Vector similarity search (pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

-- Full-text search acceleration
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- GIN index support for JSONB and array columns
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- UUID generation functions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Case-insensitive text type
CREATE EXTENSION IF NOT EXISTS citext;
