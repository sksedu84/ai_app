import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path

# Ollama creates a client during import. Keep that construction local to tests
# instead of inheriting a developer machine's proxy configuration.
for _proxy_name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(_proxy_name, None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from ai import ai_app
from endpoint.admin import get_admin_service
from endpoint.rag_prompt import get_rag_service


@pytest.fixture
def app():
    application = ai_app()
    yield application
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client


@pytest.fixture
def override_admin_service(app):
    def override(service):
        app.dependency_overrides[get_admin_service] = lambda: service
        return service

    return override


@pytest.fixture
def override_rag_service(app):
    def override(service):
        app.dependency_overrides[get_rag_service] = lambda: service
        return service

    return override
