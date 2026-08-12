from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import HTTPException, File, UploadFile

from common import constants
from config.logger import Logger
from config.settings import settings
from model.admin_response import AdminResponse

logger = Logger.get_logger()


class AdminServiceImpl:
    """Service for admin operations."""
    
    def __init__(self) -> None:
        """Initialize admin service."""
        pass

    @staticmethod
    def get_file_name_from_dir(sort_by: str = 'name', reverse: bool = True) -> list[str]:
        """
        Retrieve file names from the data directory.

        Args:
            sort_by: Sort method - 'name' or 'date'
            reverse: Whether to reverse the sort order

        Returns:
            List of file paths relative to the data directory
            
        Raises:
            None (returns an empty list on error)
        """
        try:
            if sort_by not in {'name', 'date'}:
                logger.warning("Invalid sort_by value '%s'. Falling back to 'name'.", sort_by)
                sort_by = 'name'

            if not os.path.exists(constants.DATA_DIR):
                logger.warning("Data directory does not exist: %s", constants.DATA_DIR)
                return []

            files: list[str] = []
            for root, _, filenames in os.walk(constants.DATA_DIR):
                for filename in filenames:
                    if filename.startswith('.'):
                        continue
                    files.append(os.path.join(root, filename))

            if sort_by == 'date':
                files.sort(key=os.path.getctime, reverse=reverse)
            else:
                files.sort(key=lambda file_path: os.path.basename(file_path).lower(), reverse=reverse)

            return [os.path.relpath(file_path, constants.DATA_DIR) for file_path in files]

        except FileNotFoundError:
            logger.exception("Data directory not found while reading files: %s", constants.DATA_DIR)
            return []
        except PermissionError:
            logger.exception("Permission denied while accessing data directory: %s", constants.DATA_DIR)
            return []
        except OSError as exc:
            logger.exception("OS error while reading files from directory '%s': %s", constants.DATA_DIR, exc)
            return []
        except Exception as exc:
            logger.exception("Unexpected error while listing files from '%s': %s", constants.DATA_DIR, exc)
            return []

    @staticmethod
    def _validate_file(file: UploadFile) -> None:
        """
        Validate an uploaded file.
        
        Args:
            file: Uploaded file object
            
        Raises:
            HTTPException: If validation fails
        """
        if not file.filename:
            raise HTTPException(status_code=400, detail="Uploaded file name is missing.")

        # Validate file extension
        suffix = Path(file.filename).suffix.lower()
        if suffix not in constants.SUPPORTED_UPLOAD_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{suffix}'. Supported types: {', '.join(sorted(constants.SUPPORTED_UPLOAD_EXTENSIONS))}.",
            )

    @staticmethod
    async def save_file(loc_dir: str, file: UploadFile) -> None:
        """
        Save an uploaded file to the specified directory.

        Args:
            loc_dir: Directory to save the file
            file: Uploaded file object

        Raises:
            HTTPException: If file saving fails
        """
        if not file.filename:
            raise HTTPException(status_code=400, detail="Uploaded file name is missing.")

        file_path = os.path.join(loc_dir, file.filename)

        try:
            bytes_written = 0
            max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
            
            async with aiofiles.open(file_path, 'wb') as out_file:
                while content := await file.read(constants.N_1024 * constants.N_1024):
                    bytes_written += len(content)
                    if bytes_written > max_size_bytes:
                        # Clean up partial file
                        try:
                            os.remove(file_path)
                        except OSError:
                            pass
                        raise HTTPException(
                            status_code=413,
                            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB."
                        )
                    await out_file.write(content)
                    
            logger.info("File saved successfully: %s (size: %d bytes)", file.filename, bytes_written)
            
        except HTTPException:
            raise
        except PermissionError:
            logger.exception("Permission denied while saving file: %s", file.filename)
            raise HTTPException(status_code=500, detail=f"Permission denied while saving file '{file.filename}'.")
        except OSError as exc:
            logger.exception("OS error while saving file '%s': %s", file.filename, exc)
            raise HTTPException(status_code=500, detail=f"Failed to save file '{file.filename}'.")
        except Exception as exc:
            logger.exception("Unexpected error while saving file '%s': %s", file.filename, exc)
            raise HTTPException(status_code=500, detail=f"Unexpected error while saving file '{file.filename}'.")

    async def admin(self) -> AdminResponse:
        """
        Get admin page data with list of uploaded files.

        Returns:
            AdminResponse with welcome message and file list

        Raises:
            HTTPException: If loading admin data fails
        """
        try:
            admin_response = AdminResponse(ai_response="Welcome to admin page.", status=constants.OK)
            admin_response.uploaded_files = self.get_file_name_from_dir(constants.SORT_BY_DATE, reverse=True)
            logger.info("Admin page loaded successfully with %d files", len(admin_response.uploaded_files))
            return admin_response
        except Exception as exc:
            logger.exception("Failed to load admin page data: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to load admin data.") from exc

    async def upload_files(self, files: list[UploadFile] = File(...)) -> AdminResponse:
        """
        Upload and save multiple files to appropriate directories.

        Args:
            files: List of files to upload

        Returns:
            AdminResponse confirming file upload and updated file list

        Raises:
            HTTPException: If file upload or validation fails
        """
        try:
            if not files:
                raise HTTPException(status_code=400, detail="No files were uploaded.")

            os.makedirs(constants.DOCUMENT_DATA_DIR, exist_ok=True)
            os.makedirs(constants.SQL_DATA_DIR, exist_ok=True)

            uploaded_count = 0
            for file in files:
                try:
                    # Validate file
                    self._validate_file(file)
                    
                    suffix = Path(file.filename).suffix.lower()

                    if suffix in constants.DOCUMENT_EXTENSIONS:
                        file_dir = constants.DOCUMENT_DATA_DIR
                    elif suffix == constants.SQL_EXT:
                        file_dir = constants.SQL_DATA_DIR
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Unsupported file type for '{file.filename}'. Supported types: "
                                   f"{', '.join(sorted(constants.SUPPORTED_UPLOAD_EXTENSIONS))}.",
                        )

                    await self.save_file(file_dir, file)
                    uploaded_count += 1
                except HTTPException:
                    raise
                except Exception as exc:
                    logger.exception("Error uploading file '%s': %s", file.filename, exc)
                    raise HTTPException(status_code=500, detail=f"Failed to upload file '{file.filename}'.")

            admin_response = AdminResponse(
                ai_response=f"Successfully uploaded {uploaded_count} file(s).",
                status=constants.OK,
                added_files=uploaded_count
            )
            admin_response.uploaded_files = self.get_file_name_from_dir(constants.SORT_BY_DATE, reverse=True)
            logger.info("Files uploaded successfully. Total: %d", uploaded_count)
            return admin_response

        except HTTPException:
            raise
        except PermissionError:
            logger.exception("Permission denied while creating upload directories.")
            raise HTTPException(status_code=500, detail="Permission denied while preparing upload directories.")
        except OSError as exc:
            logger.exception("OS error during file upload: %s", exc)
            raise HTTPException(status_code=500, detail="File upload failed due to a system error.")
        except Exception as exc:
            logger.exception("Unexpected error during file upload: %s", exc)
            raise HTTPException(status_code=500, detail="Unexpected error occurred while uploading files.")