"""
Tests for admin endpoints.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from common import constants
from model.admin_response import AdminResponse
from ai import app


class TestAdminEndpoint:
    """Test suite for Admin endpoints."""


    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Set up a test client."""
        self.client = TestClient(app)

    def test_admin_get_success(self) -> None:
        """Test GET /admin endpoint returns success."""
        # Act
        response = self.client.get("/admin")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == constants.OK
        assert "Welcome" in data["aiResponse"]

    def test_admin_response_format(self) -> None:
        """Test admin response has the correct format."""
        # Act
        response = self.client.get("/admin")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "aiResponse" in data
        assert "status" in data
        assert "uploadedFiles" in data
        assert "renamedFiles" in data
        assert isinstance(data["uploadedFiles"], list)
        assert isinstance(data["renamedFiles"], int)

    def test_upload_files_empty_request(self) -> None:
        """Test upload with empty files returns an error."""
        # Act
        response = self.client.post("/admin/upload-files", files=[])

        # Assert
        # FastAPI should reject Empty upload
        assert response.status_code >= 400

    def test_admin_response_model_valid(self) -> None:
        """Test AdminResponse model accepts valid data."""
        # Arrange & Act
        response = AdminResponse(
            ai_response="Test",
            status=constants.OK,
            uploaded_files=["file1.txt"],
            added_files=1,
            renamed_files=2,
        )

        # Assert
        assert response.ai_response == "Test"
        assert response.status == constants.OK
        assert len(response.uploaded_files) == 1
        assert response.renamed_files == 2

    def test_admin_response_model_invalid_status(self) -> None:
        """Test AdminResponse model rejects invalid status."""
        # Act & Assert
        with pytest.raises(ValueError):
            AdminResponse(
                ai_response="Test",
                status="invalid_status"
            )

    def test_health_check(self) -> None:
        """Test health check endpoint."""
        # Act
        response = self.client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == constants.OK
        assert data["service"] == constants.APP_NAME


if __name__ == "__main__":
    pytest.main([__file__])