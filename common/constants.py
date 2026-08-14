"""
Application-wide constants and configurations.

This module contains all constants used throughout the application,
organized by category for better maintainability.
"""

from typing import Final

# ============================================================================
# Application Configuration
# ============================================================================
APP_NAME: Final[str] = "AI Assistant"

# ============================================================================
# Response / Request Constants
# ============================================================================
OK: Final[str] = "ok"
ERROR: Final[str] = "error"
REQUEST_ID_HEADER: Final[str] = "x-request-id"

# ============================================================================
# Numeric Constants
# ============================================================================
N_0: Final[int] = 0
N_10: Final[int] = 10
N_100: Final[int] = 100
N_1024: Final[int] = 1024

# ============================================================================
# File Extensions and Upload Configuration
# ============================================================================
SQL_EXT: Final[str] = ".sql"
PDF_EXT: Final[str] = ".pdf"
DOCX_EXT: Final[str] = ".docx"
DOC_EXT: Final[str] = ".doc"
TXT_EXT: Final[str] = ".txt"

DOCUMENT_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {PDF_EXT, TXT_EXT, DOCX_EXT, DOC_EXT}
)
SUPPORTED_UPLOAD_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {*DOCUMENT_EXTENSIONS, SQL_EXT}
)

# ============================================================================
# Data Directories
# ============================================================================
DATA_DIR: Final[str] = "data"
DOCUMENT_DATA_DIR: Final[str] = f"{DATA_DIR}/documents"
SQL_DATA_DIR: Final[str] = f"{DATA_DIR}/sql"

# ============================================================================
# Logging Configuration
# ============================================================================
LOG_FILE_DIR: Final[str] = "log"
LOG_FILE_NAME: Final[str] = f"{APP_NAME}.log"
LOGGING_FORMAT: Final[str] = "%(asctime)s %(filename)s %(levelname)s %(message)s"
BACKUP_COUNT: Final[int] = 3
ROTATING_FILE_MAX_SIZE: Final[int] = N_1024 * BACKUP_COUNT

# ============================================================================
# LLM Model Names
# ============================================================================
# Local Models
EMBEDDING_MODEL: Final[str] = "nomic-embed-text:latest"
GUARD_MODEL: Final[str] = "llama-guard3:1b"
RAG_MODEL: Final[str] = "llama3.2:3b"
EMBEDDING_API_BATCH_SIZE: Final[int] = 128
EMBEDDING_FALLBACK_WORKERS: Final[int] = 6
EMBEDDING_NUM_THREAD: Final[int | None] = None
EMBEDDING_NUM_GPU: Final[int | None] = None

# Cloud-based Models


# ============================================================================
# RAG Configuration
# ============================================================================
CHUNK_OVERLAP: Final[int] = 64
CHUNK_SIZE: Final[int] = N_1024 * 2
VECTOR_DB_BATCH_SIZE: Final[int] = 400

# ============================================================================
# Metadata Keys
# ============================================================================
CHUNK_INDEX: Final[str] = "chunk_index"
CHUNK_IDS: Final[str] = "chunk_ids"
FILE_HASH: Final[str] = "file_hash"
SOURCE_FILE: Final[str] = "source_file"
HASH: Final[str] = "hash"

# ============================================================================
# Sorting and Encoding
# ============================================================================
SORT_BY_DATE: Final[str] = "date"
ENCODING_UTF8: Final[str] = "utf-8"
