-- TrustChain Database Initialization
-- This script runs automatically when PostgreSQL container starts
--
-- Built with care by Kareem & Claude

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search optimization

-- Create schema for TrustChain
CREATE SCHEMA IF NOT EXISTS trustchain;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA trustchain TO trustchain;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA trustchain TO trustchain;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA trustchain TO trustchain;

-- Set default schema
ALTER USER trustchain SET search_path TO trustchain, public;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'TrustChain database initialized successfully';
END $$;
