-- CREATING EXTENSIONS
CREATE EXTENSION IF NOT EXISTS vector;

-- CLEAN UP
DROP TABLE IF EXISTS langchain_pg_embedding;
DROP TABLE IF EXISTS langchain_pg_collection;
DROP TABLE IF EXISTS unexpected_prompt;

-- CREATING TABLES
/*
Auto created tables:
	langchain_pg_collection
	langchain_pg_embedding
	
*/

CREATE TABLE unexpected_prompt (
	prompt_hash VARCHAR(64) PRIMARY KEY,
	model_response TEXT NOT NULL,
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	hit_count INTEGER NOT NULL DEFAULT 1
);

-- CREATING INDEXES
