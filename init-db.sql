-- Database initialization script for Interview Assistant
-- This script sets up the PostgreSQL database with optimized settings

-- Create extensions for better performance
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create optimized indexes for frequent queries
-- These will be created by SQLAlchemy, but we can prepare the database

-- Set optimal PostgreSQL settings for the interview assistant workload
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';

-- Create the main database user if not exists (should already be created by Docker)
-- This is just for documentation purposes
-- CREATE USER interview_user WITH PASSWORD 'interview_password_2024';
-- GRANT ALL PRIVILEGES ON DATABASE interview_assistant TO interview_user;

-- Create schemas for organization (optional)
-- CREATE SCHEMA IF NOT EXISTS interview_data;
-- CREATE SCHEMA IF NOT EXISTS analytics;

-- Initial data setup can be added here
-- For now, tables will be created by SQLAlchemy models

COMMENT ON DATABASE interview_assistant IS 'Interview Assistant application database with enhanced Phase 1 features including context-aware AI, PIN codes, response scoring, and dynamic caching';