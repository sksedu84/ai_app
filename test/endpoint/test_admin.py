import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from common import constants
from model.admin_response import AdminResponse
from main import app


# noinspection PyClassHasNoInit
class TestAdminEndpoint:
    """Test suite for Admin endpoints."""
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = TestClient(app)

    @patch("endpoint.admin.AdminServiceImpl.admin", new_callable=AsyncMock)
    def test_admin_get(self, mock_admin):
        # Arrange
        mock_response = AdminResponse(
            ai_response="Welcome to admin page.",
            status=constants.OK,
            uploaded_files=["file1.txt"]
        )
        mock_admin.return_value = mock_response

        # Act
        response = self.client.get("/admin")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["aiResponse"] == "Welcome to admin page."
        assert data["status"] == constants.OK
        assert data["uploadedFiles"] == ["file1.txt"]
        mock_admin.assert_called_once()

    @patch("endpoint.admin.AdminServiceImpl.admin", new_callable=AsyncMock)
    def test_admin_get_error(self, mock_admin):
        # Arrange
        from fastapi import HTTPException
        mock_admin.side_effect = HTTPException(status_code=500, detail="Failed to load admin data.")

        # Act
        response = self.client.get("/admin")

        # Assert
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to load admin data."

    @patch("endpoint.admin.AdminServiceImpl.upload_files", new_callable=AsyncMock)
    def test_upload_files_post(self, mock_upload):
        # Arrange
        mock_response = AdminResponse(
            ai_response="Files are uploaded.",
            status=constants.OK,
            uploaded_files=["test.txt"]
        )
        mock_upload.return_value = mock_response

        # Act
        files = [
            ("files", ("test.txt", b"hello world", "text/plain"))
        ]
        response = self.client.post("/admin/upload-files", files=files)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["aiResponse"] == "Files are uploaded."
        assert data["status"] == constants.OK
        mock_upload.assert_called_once()

    @patch("endpoint.admin.AdminServiceImpl.upload_files", new_callable=AsyncMock)
    def test_upload_files_post_error(self, mock_upload):
        # Arrange
        from fastapi import HTTPException
        mock_upload.side_effect = HTTPException(status_code=400, detail="Unsupported file type.")

        # Act
        files = [
            ("files", ("test.exe", b"binary", "application/x-msdownload"))
        ]
        response = self.client.post("/admin/upload-files", files=files)

        # Assert
        assert response.status_code == 400
        assert response.json()["detail"] == "Unsupported file type."

if __name__ == "__main__":
    pytest.main([__file__])