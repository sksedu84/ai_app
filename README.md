# AI Assistant

AI Assistant is a FastAPI-based application designed for Retrieval-Augmented Generation (RAG). It allows users to upload documents, process them, and then query an LLM which uses the uploaded documents as context to provide accurate answers.

## Features

- **Retrieval-Augmented Generation (RAG):** Query LLMs with context from your own documents.
- **File Upload & Processing:** Supports multiple file formats including PDF, DOCX, TXT, and SQL.
- **Multiple LLM Support:** Integrated with various models like Mistral, Gemini, Llama, and more.
- **Admin Endpoints:** Manage the application and upload files via dedicated admin routes.
- **Health Monitoring:** Built-in health check endpoints.
- **Asynchronous Processing:** Built on FastAPI for high-performance asynchronous operations.

## Project Structure

```text
.
├── common/             # Shared constants and utilities
├── config/             # Application configuration (routes, logger, middleware, etc.)
├── data/               # Data storage (documents, sql files)
├── endpoint/           # API route handlers
├── log/                # Application logs
├── model/              # Pydantic data models
├── service/            # Business logic and service implementations
├── static/             # Static files (favicon, etc.)
├── test/               # Unit and integration tests
├── main.py             # Application entry point
└── requirements.txt    # Project dependencies
```

## Prerequisites

- Python 3.12+
- Virtual environment (recommended)

## Installation

1. **Root Directory:**
   ```bash
   ai_app
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Create a `.env` file in the root directory and configure necessary environment variables (e.g., API keys, database configuration).
   Example `.env`:
   ```env
   KEY=your_key
   USER=your_user
   PASSWORD=your_password
   DATABASE=your_db
   ```

## Running the Application

Start the FastAPI server using Uvicorn:

```bash
uvicorn ai:app --reload
```

The application will be available at `http://127.0.0.1:8000`.

## API Documentation

FastAPI automatically generates interactive API documentation. Once the server is running, you can access:

- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Testing

Run tests using `pytest`:

```bash
pytest
```
