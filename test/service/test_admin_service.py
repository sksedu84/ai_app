"""
Tests for admin service layer.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException, UploadFile
from io import BytesIO

from service.admin_service import AdminServiceImpl
from common import constants
from model.admin_response import AdminResponse


class TestAdminService(unittest.IsolatedAsyncioTestCase):
    """Test suite for AdminServiceImpl."""

    async def asyncSetUp(self) -> None:
        """Setup test fixtures."""
        self.admin_service = AdminServiceImpl()

    def test_get_file_name_from_dir_empty_dir(self) -> None:
        """Test getting file list from empty directory."""
        # Arrange
        with patch('service.admin_service.os.path.exists', return_value=False):
            # Act
            result = self.admin_service.get_file_name_from_dir()

        # Assert
        assert result == []

    def test_get_file_name_from_dir_with_files(self) -> None:
        """Test getting file list with existing files."""
        # Arrange
        mock_files = ['file1.txt', 'file2.pdf', 'file3.doc']
        
        with patch('service.admin_service.os.path.exists', return_value=True), \
             patch('service.admin_service.os.walk') as mock_walk, \
             patch('service.admin_service.os.path.relpath', side_effect=lambda x, y: x):
            
            mock_walk.return_value = [
                (constants.DATA_DIR, [], ['file1.txt', 'file2.pdf', 'file3.doc'])
            ]
            
            # Act
            result = self.admin_service.get_file_name_from_dir(sort_by='name', reverse=False)

        # Assert
        assert len(result) == 3

    def test_get_file_name_from_dir_invalid_sort(self) -> None:
        """Test getting file list with invalid sort parameter."""
        # Arrange
        with patch('service.admin_service.os.path.exists', return_value=False):
            # Act
            result = self.admin_service.get_file_name_from_dir(sort_by='invalid')

        # Assert
        assert result == []

    def test_get_file_name_from_dir_permission_error(self) -> None:
        """Test getting file list with permission error."""
        # Arrange
        with patch('service.admin_service.os.path.exists', return_value=True), \
             patch('service.admin_service.os.walk', side_effect=PermissionError()):
            
            # Act
            result = self.admin_service.get_file_name_from_dir()

        # Assert
        assert result == []

    def test_validate_file_missing_filename(self) -> None:
        """Test file validation with missing filename."""
        # Arrange
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = None

        # Act & Assert
        with self.assertRaises(HTTPException) as context:
            self.admin_service._validate_file(mock_file)
        
        assert context.exception.status_code == 400

    def test_validate_file_unsupported_extension(self) -> None:
        """Test file validation with unsupported file extension."""
        # Arrange
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.exe"

        # Act & Assert
        with self.assertRaises(HTTPException) as context:
            self.admin_service._validate_file(mock_file)
        
        assert context.exception.status_code == 400
        assert "Unsupported file type" in str(context.exception.detail)

    def test_validate_file_valid_txt(self) -> None:
        """Test file validation with valid txt file."""
        # Arrange
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.txt"

        # Act & Assert (should not raise)
        try:
            self.admin_service._validate_file(mock_file)
        except HTTPException:
            self.fail("Validation raised HTTPException unexpectedly")

    def test_validate_file_valid_pdf(self) -> None:
        """Test file validation with valid pdf file."""
        # Arrange
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.pdf"

        # Act & Assert (should not raise)
        try:
            self.admin_service._validate_file(mock_file)
        except HTTPException:
            self.fail("Validation raised HTTPException unexpectedly")

    def test_validate_file_valid_sql(self) -> None:
        """Test file validation with valid sql file."""
        # Arrange
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "query.sql"

        # Act & Assert (should not raise)
        try:
            self.admin_service._validate_file(mock_file)
        except HTTPException:
            self.fail("Validation raised HTTPException unexpectedly")

    async def test_admin_success(self) -> None:
        """Test admin method returns welcome message."""
        # Arrange
        with patch.object(self.admin_service, 'get_file_name_from_dir', return_value=['file1.txt']):
            # Act
            result = await self.admin_service.admin()

        # Assert
        assert isinstance(result, AdminResponse)
        assert result.status == constants.OK
        assert "Welcome" in result.ai_response
        assert result.uploaded_files == ['file1.txt']

    async def test_admin_error(self) -> None:
        """Test admin method error handling."""
        # Arrange
        with patch.object(self.admin_service, 'get_file_name_from_dir', side_effect=Exception("Test error")):
            # Act & Assert
            with self.assertRaises(HTTPException) as context:
                await self.admin_service.admin()
            
            assert context.exception.status_code == 500

    async def test_upload_files_no_files(self) -> None:
        """Test upload_files with no files."""
        # Act & Assert
        with self.assertRaises(HTTPException) as context:
            await self.admin_service.upload_files([])
        
        assert context.exception.status_code == 400

    async def test_upload_files_success(self) -> None:
        """Test successful file upload."""
        # Arrange
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.read = AsyncMock(return_value=b"test content")
        
        with patch('service.admin_service.os.makedirs'), \
             patch.object(self.admin_service, 'save_file', new_callable=AsyncMock), \
             patch.object(self.admin_service, 'get_file_name_from_dir', return_value=['test.txt']):
            
            # Act
            result = await self.admin_service.upload_files([mock_file])

        # Assert
        assert isinstance(result, AdminResponse)
        assert result.status == constants.OK
        assert result.added_files == 1

    async def test_upload_files_invalid_file(self) -> None:
        """Test upload_files with invalid file."""
        # Arrange
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "test.exe"
        
        with patch('service.admin_service.os.makedirs'):
            # Act & Assert
            with self.assertRaises(HTTPException) as context:
                await self.admin_service.upload_files([mock_file])
            
            assert context.exception.status_code == 400

    async def test_document_embeddings_success(self) -> None:
        """Test document_embeddings returns a valid AdminResponse."""
        with patch('service.admin_service.ingest_to_vectordb', return_value={
            "status": constants.OK,
            "message": "Documents ingested successfully",
            "added_chunks": 3,
            "added_files": 1,
        }), patch.object(self.admin_service, 'get_file_name_from_dir', return_value=['doc.txt']):
            result = await self.admin_service.document_embeddings()

        assert isinstance(result, AdminResponse)
        assert result.status == constants.OK
        assert result.added_chunks == 3
        assert result.added_files == 1

    async def test_document_embeddings_invalid_status_defaults_to_error(self) -> None:
        """Test unexpected ingestion statuses are normalized for AdminResponse."""
        with patch('service.admin_service.ingest_to_vectordb', return_value={
            "status": "success",
            "message": "Documents ingested successfully",
            "added_chunks": 3,
            "added_files": 1,
        }), patch.object(self.admin_service, 'get_file_name_from_dir', return_value=['doc.txt']):
            result = await self.admin_service.document_embeddings()

        assert isinstance(result, AdminResponse)
        assert result.status == constants.ERROR


if __name__ == "__main__":
    unittest.main()