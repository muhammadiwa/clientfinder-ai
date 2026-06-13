-- =============================================================
-- ClientFinder — PostgreSQL Initialization
-- =============================================================
-- This file runs ONCE on first container startup.
-- Schema migrations are handled by Alembic (see backend/alembic/).
-- =============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Note: full schema is created via Alembic migrations in T2.
-- This file is reserved for any DB-level bootstrap (roles, etc).
