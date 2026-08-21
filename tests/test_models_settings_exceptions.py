import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from common import constants
from config.exceptions import ApplicationError, ValidationError, exception_handlers
from config.settings import Settings, _parse_cors_list_value
from model.admin_response import AdminResponse
from model.error_response import ErrorResponse
from model.prompt_response import PromptResponse


def test_response_models_use_aliases_and_reject_invalid_values():
    admin = AdminResponse(ai_response="ok", status="ok")
    assert admin.model_dump(by_alias=True)["aiResponse"] == "ok"
    assert PromptResponse(status="ok", response="answer").model_dump(by_alias=True)["response"] == "answer"
    with pytest.raises(ValueError):
        AdminResponse(ai_response="bad", status="pending")
    with pytest.raises(ValueError):
        AdminResponse(ai_response="bad", status="ok", added_files=-1)


def test_error_response_forbids_extra_fields():
    with pytest.raises(ValueError):
        ErrorResponse(error="bad", unexpected="value")


@pytest.mark.parametrize("value, expected", [
    (None, ["*"]),
    ("*", ["*"]),
    ("https://a.test, https://b.test", ["https://a.test", "https://b.test"]),
    ('["GET", "POST"]', ["GET", "POST"]),
    (("GET", "POST"), ["GET", "POST"]),
])
def test_parse_cors_values(value, expected):
    assert _parse_cors_list_value(value) == expected


def test_settings_parse_cors_from_init_values():
    settings = Settings(CORS_ORIGINS="https://example.test, https://admin.test")
    assert settings.cors_origins == ["https://example.test", "https://admin.test"]


@pytest.mark.asyncio
async def test_exception_handlers_format_application_and_unhandled_errors():
    app = FastAPI()
    exception_handlers(app)

    @app.get("/application")
    async def application_error():
        raise ValidationError("invalid input")

    @app.get("/unhandled")
    async def unhandled_error():
        raise RuntimeError("boom")

    @app.get("/http")
    async def http_error():
        raise HTTPException(status_code=404, detail={"reason": "missing"})

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        application = await client.get("/application", headers={"x-request-id": "one"})
        unhandled = await client.get("/unhandled", headers={"x-request-id": "two"})
        http = await client.get("/http", headers={"x-request-id": "three"})

    assert application.status_code == 400
    assert application.json() == {"error": "Application Error", "detail": "invalid input", "request_id": "one"}
    assert unhandled.status_code == 500
    assert unhandled.json()["error"] == "Internal Server Error"
    assert unhandled.json()["request_id"] == "two"
    assert http.status_code == 404
    assert http.json()["detail"] == "{'reason': 'missing'}"
