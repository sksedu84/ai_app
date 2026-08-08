from typing import Final


# Application
APP_NAME: Final[str] = "AI Assistant"
MANIFEST_FILE_NAME: Final[str] = ".vdb_manifest.json"

# Response / request constants
OK: Final[str] = "ok"
ERROR: Final[str] = "error"
REQUEST_ID_HEADER: Final[str] = "x-request-id"


# Numeric constants
N_0: Final[int] = 0
N_10: Final[int] = 10
N_100: Final[int] = 100
N_1024: Final[int] = 1024


# File extensions
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


# Data directories
DATA_DIR: Final[str] = "data"
DOCUMENT_DATA_DIR: Final[str] = f"{DATA_DIR}/documents"
SQL_DATA_DIR: Final[str] = f"{DATA_DIR}/sql"


# Logging
LOG_FILE_DIR: Final[str] = "log"
LOG_FILE_NAME: Final[str] = f"{APP_NAME}.log"
LOGGING_FORMAT: Final[str] = "%(asctime)s %(filename)s %(levelname)s %(message)s"
BACKUP_COUNT: Final[int] = 3
ROTATING_FILE_MAX_SIZE: Final[int] = N_1024 * BACKUP_COUNT


# Model names
RAG_MISTRAL: Final[str] = "mistral-small3.2:24b"
GUARD_LLAMA: Final[str] = "llama-guard3:1b"
RERANKER_QWEN: Final[str] = "sam860/qwen3-reranker:0.6b-Q8_0"
CODE_DEEPSEEK: Final[str] = "deepseek-coder:6.7b"
ROUTER_QWEN: Final[str] = "qwen3.5:0.8b"
EMBEDDING_MODEL: Final[str] = "all-MiniLM-L6-v2"

#Google Gemini
GEMINI_API: Final[str] = "gemini-3.1-flash-lite-preview"
MAX_GEMINI_HISTORY_MESSAGES = 5



# Chunking
CHUNK_OVERLAP: Final[int] = N_100
CHUNK_SIZE: Final[int] = CHUNK_OVERLAP * N_10


# Metadata keys
CHUNK_INDEX: Final[str] = "chunk_index"
CHUNK_IDS: Final[str] = "chunk_ids"
FILE_HASH: Final[str] = "file_hash"
SOURCE_FILE: Final[str] = "source_file"
HASH: Final[str] = "hash"


# Sorting / encoding
SORT_BY_DATE: Final[str] = "date"
ENCODING_UTF8: Final[str] = "utf-8"


# Manifest / sync result keys
ADDED_CHUNKS: Final[str] = "added_chunks"
ADDED_FILES: Final[str] = "added_files"
UPDATED_FILES: Final[str] = "updated_files"
DELETED_FILES: Final[str] = "deleted_files"
SKIPPED_FILES: Final[str] = "skipped_files"