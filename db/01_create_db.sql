-- ============================================
-- MassMutual Financial Pipeline — Database Init
-- ============================================
-- This script runs on the default 'airflow' database first
-- to create the application database and user.

-- Create application user (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'massmutual') THEN
        CREATE ROLE massmutual WITH LOGIN PASSWORD 'massmutual123';
    END IF;
END
$$;

-- Create the application database owned by massmutual
SELECT 'CREATE DATABASE massmutual OWNER massmutual'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'massmutual')\gexec

