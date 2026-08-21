from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from common import constants
from model.admin_response import AdminResponse
from model.prompt_response import PromptResponse


@pytest.mark.asyncio
async def test_health_and_root_return_service_identity(client):
    for path in ("/", "/health"):
        response = await client.get(path)
        assert response.status_code == 200
        assert response.json() == {"status": constants.OK, "service": constants.APP_NAME}
        assert response.headers[constants.REQUEST_ID_HEADER]


@pytest.mark.asyncio
async def test_admin_get_uses_injected_service(client, override_admin_service):
    service = Mock()
    service.admin = AsyncMock(return_value=AdminResponse(ai_response="dashboard", status=constants.OK))
    override_admin_service(service)

    response = await client.get("/admin", headers={constants.REQUEST_ID_HEADER: "request-123"})

    assert response.status_code == 200
    assert response.json()["aiResponse"] == "dashboard"
    assert response.headers[constants.REQUEST_ID_HEADER] == "request-123"
    service.admin.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_upload_files_passes_multipart_files_to_service(client, override_admin_service):
    service = Mock()
    service.upload_files = AsyncMock(
        return_value=AdminResponse(ai_response="uploaded", status=constants.OK, added_files=1)
    )
    override_admin_service(service)

    response = await client.post(
        "/admin/upload-files",
        files={"files": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["addedFiles"] == 1
    service.upload_files.assert_awaited_once()
    assert service.upload_files.call_args.args[0][0].filename == "notes.txt"


@pytest.mark.asyncio
async def test_upload_files_requires_files(client):
    response = await client.post("/admin/upload-files")
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "missing"


@pytest.mark.asyncio
@pytest.mark.parametrize("path, method_name", [
    ("/admin/ingest/documents", "ingest_documents"),
    ("/admin/refresh/database", "refresh_database"),
])
async def test_admin_operations_delegate_to_service(client, override_admin_service, path, method_name):
    service = Mock()
    method = AsyncMock(return_value=AdminResponse(ai_response="done", status=constants.OK))
    setattr(service, method_name, method)
    override_admin_service(service)

    response = await client.get(path)

    assert response.status_code == 200
    assert response.json()["status"] == constants.OK
    method.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_rag_endpoint_delegates_to_service(client, override_rag_service):
    service = Mock()
    service.process_rag_prompt = AsyncMock(
        return_value=PromptResponse(status=constants.OK, response="<p>answer</p>")
    )
    override_rag_service(service)

    response = await client.get("/rag", params={"prompt": "What is AI?"})

    assert response.status_code == 200
    assert response.json() == {"status": constants.OK, "response": "<p>answer</p>"}
    service.process_rag_prompt.assert_awaited_once_with("What is AI?")


@pytest.mark.asyncio
async def test_rag_endpoint_validates_query(client):
    missing = await client.get("/rag")
    empty = await client.get("/rag", params={"prompt": ""})
    too_long = await client.get("/rag", params={"prompt": "x" * 10_001})

    assert missing.status_code == 422
    assert empty.status_code == 422
    assert too_long.status_code == 422
    assert missing.json()["detail"][0]["type"] == "missing"


@pytest.mark.asyncio
async def test_http_exception_includes_request_id(client, override_rag_service):
    service = Mock()
    service.process_rag_prompt = AsyncMock(side_effect=HTTPException(status_code=429, detail="busy"))
    override_rag_service(service)

    response = await client.get("/rag", params={"prompt": "retry"}, headers={"x-request-id": "abc"})

    assert response.status_code == 429
    assert response.json() == {"error": "Request Failed", "detail": "busy", "request_id": "abc"}
