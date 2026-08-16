-- CREATING EXTENSIONS
CREATE EXTENSION IF NOT EXISTS vector;

-- CLEAN UP
DROP TABLE IF EXISTS langchain_pg_embedding;
DROP TABLE IF EXISTS langchain_pg_collection;

-- CREATING TABLES
/*
Auto created tables:
	langchain_pg_collection
	langchain_pg_embedding
	
*/

-- CREATING INDEXES
