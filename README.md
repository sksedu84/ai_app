# AI Assistant

AI Assistant is a FastAPI-based application designed for Retrieval-Augmented Generation (RAG). It allows users to upload documents, process them, and then query an LLM which uses the uploaded documents as context to provide accurate answers.

## Features

- ✨ **Retrieval-Augmented Generation (RAG):** Query LLMs with context from your own documents
- 📤 **File Upload & Processing:** Supports PDF, DOCX, TXT, and SQL files with validation
- 🤖 **Multiple LLM Support:** Integrated with Mistral, Gemini, Llama, and more
- 👨‍💼 **Admin Endpoints:** Comprehensive file management via REST API
- 🏥 **Health Monitoring:** Built-in health check endpoints for monitoring
- ⚡ **Asynchronous Processing:** Built on FastAPI for high-performance async operations
- 🔒 **Request Tracking:** Correlation IDs for request tracking and debugging
- 📝 **Comprehensive Logging:** Structured logging with file and console output
- 🧪 **Full Test Coverage:** Unit and integration tests with pytest
- 📚 **Auto API Docs:** Interactive Swagger UI and ReDoc documentation

## Project Structure

```text
ai_app/
├── common/                      # Shared constants and utilities
│   └── constants.py            # Application-wide constants
├── config/                      # Application configuration
│   ├── database.py             # Database configuration
│   ├── exceptions.py           # Global exception handlers
│   ├── lifespan.py             # Application lifespan management
│   ├── logger.py               # Logging configuration
│   ├── middleware.py           # CORS and request logging middleware
│   ├── routes.py               # Route registration and static files
│   └── settings.py             # Pydantic-based settings (NEW)
├── data/                        # Data storage
│   ├── documents/              # Uploaded documents
│   └── sql/                    # SQL files
├── endpoint/                    # API route handlers
│   ├── admin.py                # Admin endpoints (GET/POST)
│   ├── health.py               # Health check endpoints
│   └── rag_prompt.py           # RAG query endpoints
├── log/                         # Application logs
│   └── AI Assistant.log        # Main log file
├── model/                       # Pydantic data models
│   ├── admin_response.py       # Admin operation response
│   ├── error_response.py       # Standard error response
│   └── prompt_response.py      # RAG prompt response
├── service/                     # Business logic layer
│   ├── admin_service.py        # File management service
│   └── rag_service.py          # RAG processing service
├── static/                      # Static files
│   └── favicon.ico             # Favicon
├── test/                        # Test suite
│   ├── endpoint/               # Endpoint tests
│   │   └── test_admin.py       # Admin endpoint tests
│   └── service/                # Service layer tests
│       └── test_admin_service.py # Admin service tests
├── ai.py                        # Application factory
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
├── README.md                    # This file
└── OPTIMIZATION_REPORT.md       # Detailed optimization report
```

## Prerequisites

- Python 3.12+
- Virtual environment (recommended)
- pip or poetry for dependency management

## Installation

### 1. Clone or Navigate to Project Directory

```bash
cd ai_app
```

### 2. Create and Activate Virtual Environment

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Running the Application

### Development Mode

```bash
uvicorn ai:app --reload --port 8000 --host 127.0.0.1
```

### Production Mode

```bash
uvicorn ai:app --port 8000 --host 0.0.0.0 --workers 4
```

The application will be available at `http://localhost:8000`.

## API Documentation

### Interactive Documentation

Once the server is running, access the auto-generated documentation:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

### API Endpoints

#### Health Check
```
GET /health
```

#### Admin Operations

**Get Admin Dashboard**
```
GET /admin
```
Response:
```json
{
  "aiResponse": "Welcome to admin page.",
  "status": "ok",
  "uploadedFiles": ["documents/file.txt"],
  "addedFiles": 0
}
```

**Upload Files**
```
POST /admin/upload-files
Content-Type: multipart/form-data

files: <file1, file2, ...>
```

#### RAG Queries

**Process Prompt**
```
GET /rag?prompt=What%20is%20artificial%20intelligence
```
Response:
```json
{
  "status": "ok",
  "response": "Response from LLM based on prompt..."
}
```

## Testing

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest test/endpoint/test_admin.py
```

### Run with Coverage Report

```bash
pytest --cov=. --cov-report=html
```

Coverage report will be generated in `htmlcov/index.html`.

### Run Specific Test Class

```bash
pytest test/endpoint/test_admin.py::TestAdminEndpoint
```

### Run Specific Test Method

```bash
pytest test/endpoint/test_admin.py::TestAdminEndpoint::test_admin_get
```

### Run with Verbose Output

```bash
pytest -v
```

## Development Guidelines

### Code Style

- Follow PEP 8 guidelines
- Use type hints throughout
- Add docstrings to all functions and classes
- Use `from __future__ import annotations` for forward references

### Adding New Endpoints

1. Create endpoint handler in `endpoint/`
2. Create service layer in `service/`
3. Add request/response models in `model/`
4. Register routes in `config/routes.py`
5. Add tests in `test/`

### Adding New Features

1. Implement business logic in service layer
2. Create API endpoints in endpoint layer
3. Use dependency injection via FastAPI's `Depends()`
4. Add comprehensive error handling
5. Write tests with good coverage

## Architecture

### Layered Architecture

```
┌─────────────────────────────────────┐
│         API Layer (Endpoints)       │
│  - Request validation               │
│  - Response formatting              │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│     Business Logic (Services)       │
│  - File processing                  │
│  - RAG pipeline                     │
│  - Data transformation              │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│      Data Layer (Repositories)      │
│  - File operations                  │
│  - Data persistence                 │
└─────────────────────────────────────┘
```

### Key Components

- **Middleware:** CORS configuration, request logging, request ID tracking
- **Exception Handlers:** Global error handling with consistent responses
- **Logging:** Structured logging with file rotation and console output
- **Configuration:** Environment-based settings using Pydantic
- **Dependency Injection:** FastAPI's dependency system for better testability

## Best Practices Implemented

✅ **Code Quality**
- Type hints throughout codebase
- Comprehensive docstrings
- PEP 8 compliance
- Code organization and modularity

✅ **Error Handling**
- Custom exception classes
- Detailed error responses with request IDs
- Proper HTTP status codes
- Error logging for debugging

✅ **Asynchronous Programming**
- Async/await usage throughout
- Non-blocking I/O operations
- Proper async context management

✅ **Testing**
- Unit tests for services
- Integration tests for endpoints
- Mocking and fixtures
- Test coverage tracking

✅ **Security**
- CORS configuration from environment
- File upload validation
- File size limits
- Request ID tracking for audit

✅ **Performance**
- Async operations for concurrency
- Streaming file uploads
- Efficient file chunking
- Connection pooling ready

## Troubleshooting

### Port Already in Use

```bash
# macOS/Linux
lsof -i :8000
kill -9 <PID>

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Log File Issues

Logs are stored in the `log/` directory. If you encounter issues:

```bash
# Clear old logs
rm -rf log/
# Restart the application
```

### Environment Variables Not Loading

- Ensure `.env` file exists in the root directory
- Check file permissions
- Verify variable names match the configuration

## Performance Tips

1. **Use production Uvicorn workers:** `--workers 4` for 4-core CPU
2. **Enable gzip compression:** Configure at reverse proxy level
3. **Add caching:** Redis for frequently accessed data
4. **Monitor performance:** Use Prometheus metrics
5. **Database optimization:** Connection pooling, query optimization

## Future Enhancements

- [ ] Authentication & Authorization (JWT)
- [ ] Rate limiting (Redis-based)
- [ ] Caching layer (Redis)
- [ ] Database integration (SQLAlchemy + PostgreSQL)
- [ ] Message queue integration (Celery + RabbitMQ)
- [ ] Monitoring & observability (Prometheus + Grafana)
- [ ] API versioning
- [ ] Pagination for file listings
- [ ] Full-text search capability
- [ ] Docker & Kubernetes deployment

## Contributing

1. Follow the development guidelines above
2. Write tests for new features
3. Ensure all tests pass before submitting
4. Update documentation as needed
5. Follow the code style guidelines

## License

This project is provided as-is for educational and commercial use.

## Support

For issues, questions, or suggestions, please refer to the `OPTIMIZATION_REPORT.md` for detailed optimization notes and best practices.

