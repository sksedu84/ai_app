from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from common import constants
from model.admin_response import AdminResponse
from service.admin_service import AdminServiceImpl


@pytest.fixture
def service():
    return AdminServiceImpl()


def upload(name: str, content: bytes = b"content") -> UploadFile:
    return UploadFile(filename=name, file=BytesIO(content))


def test_get_file_name_from_dir_filters_hidden_and_sorts(tmp_path, monkeypatch):
    (tmp_path / "b.txt").write_text("b")
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / ".hidden").write_text("hidden")
    nested = tmp_path / "documents"
    nested.mkdir()
    (nested / "c.pdf").write_text("c")
    monkeypatch.setattr(constants, "DATA_DIR", str(tmp_path))

    assert AdminServiceImpl.get_file_name_from_dir(sort_by="name", reverse=False) == [
        "a.txt", "b.txt", "documents/c.pdf"
    ]


def test_get_file_name_from_dir_invalid_sort_falls_back_to_name(tmp_path, monkeypatch):
    (tmp_path / "file.txt").write_text("data")
    monkeypatch.setattr(constants, "DATA_DIR", str(tmp_path))
    assert AdminServiceImpl.get_file_name_from_dir(sort_by="invalid", reverse=False) == ["file.txt"]


def test_validate_file_rejects_missing_and_unsupported_names(service):
    with pytest.raises(HTTPException, match="name is missing"):
        service._validate_file(upload(""))
    with pytest.raises(HTTPException, match="Unsupported file type"):
        service._validate_file(upload("payload.exe"))


@pytest.mark.asyncio
async def test_save_file_writes_upload(service, tmp_path):
    await service.save_file(str(tmp_path), upload("doc.txt", b"hello world"))
    assert (tmp_path / "doc.txt").read_bytes() == b"hello world"


@pytest.mark.asyncio
async def test_save_file_enforces_configured_size_limit(service, tmp_path, monkeypatch):
    monkeypatch.setattr("service.admin_service.settings.max_upload_size_mb", 0)
    with pytest.raises(HTTPException) as error:
        await service.save_file(str(tmp_path), upload("large.txt", b"x"))
    assert error.value.status_code == 413
    assert not (tmp_path / "large.txt").exists()


@pytest.mark.asyncio
async def test_upload_files_routes_document_and_sql_files(service, tmp_path, monkeypatch):
    document_dir = tmp_path / "documents"
    sql_dir = tmp_path / "sql"
    monkeypatch.setattr(constants, "DOCUMENT_DATA_DIR", str(document_dir))
    monkeypatch.setattr(constants, "SQL_DATA_DIR", str(sql_dir))
    monkeypatch.setattr(service, "get_file_name_from_dir", Mock(return_value=[]))

    response = await service.upload_files([upload("readme.txt", b"text"), upload("schema.sql", b"select 1")])

    assert response.status == constants.OK
    assert response.added_files == 2
    assert (document_dir / "readme.txt").read_bytes() == b"text"
    assert (sql_dir / "schema.sql").read_bytes() == b"select 1"


@pytest.mark.asyncio
async def test_upload_files_rejects_empty_and_invalid_files(service):
    with pytest.raises(HTTPException) as empty_error:
        await service.upload_files([])
    assert empty_error.value.status_code == 400

    with pytest.raises(HTTPException) as invalid_error:
        await service.upload_files([upload("bad.exe")])
    assert invalid_error.value.status_code == 400


@pytest.mark.asyncio
async def test_ingest_documents_archives_only_successful_ingestion(service, monkeypatch):
    monkeypatch.setattr(
        "service.admin_service.ingest_to_vectordb",
        lambda: {"status": constants.OK, "message": "indexed", "added_chunks": 3, "added_files": 1},
    )
    archive = Mock()
    monkeypatch.setattr("service.admin_service.AiAppUtil.move_to_archive", archive)
    monkeypatch.setattr(service, "get_file_name_from_dir", Mock(return_value=["documents/a.txt"]))

    response = await service.ingest_documents()

    assert response.status == constants.OK
    assert response.added_chunks == 3
    archive.assert_called_once_with(constants.DOCUMENT_DATA_DIR)


@pytest.mark.asyncio
async def test_ingest_documents_skips_archive_on_failure(service, monkeypatch):
    monkeypatch.setattr(
        "service.admin_service.ingest_to_vectordb",
        lambda: {"status": constants.ERROR, "message": "failed"},
    )
    archive = Mock()
    monkeypatch.setattr("service.admin_service.AiAppUtil.move_to_archive", archive)
    monkeypatch.setattr(service, "get_file_name_from_dir", Mock(return_value=[]))

    response = await service.ingest_documents()

    assert response.status == constants.ERROR
    archive.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_database_without_db_configuration_returns_ok(monkeypatch):
    monkeypatch.setattr(
        "service.admin_service.DatabaseConfig.psycopg_db_con_as_string",
        Mock(side_effect=ValueError("missing config")),
    )
    response = await AdminServiceImpl.refresh_database()
    assert response.status == constants.OK
    assert "skipped" in response.ai_response
