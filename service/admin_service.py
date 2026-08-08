import os
from pathlib import Path

import aiofiles
from fastapi import HTTPException, File, UploadFile

from common import constants
from config.logger import Logger
from model.admin_response import AdminResponse

logger = Logger.get_logger()

def get_file_name_from_dir(sort_by: str = 'name', reverse: bool = True) -> list[str]:
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


async def save_file(loc_dir: str, file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file name is missing.")

    file_path = os.path.join(loc_dir, file.filename)

    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            while content := await file.read(constants.N_1024 * constants.N_1024):
                await out_file.write(content)
    except PermissionError:
        logger.exception("Permission denied while saving file: %s", file.filename)
        raise HTTPException(status_code=500, detail=f"Permission denied while saving file '{file.filename}'.")
    except OSError as exc:
        logger.exception("OS error while saving file '%s': %s", file.filename, exc)
        raise HTTPException(status_code=500, detail=f"Failed to save file '{file.filename}'.")
    except Exception as exc:
        logger.exception("Unexpected error while saving file '%s': %s", file.filename, exc)
        raise HTTPException(status_code=500, detail=f"Unexpected error while saving file '{file.filename}'.")


class AdminServiceImpl:
    def __init__(self):
        pass

    @staticmethod
    async def admin() -> AdminResponse:
        try:
            admin_response = AdminResponse(ai_response="Welcome to admin page.", status=constants.OK)
            admin_response.uploaded_files = get_file_name_from_dir(constants.SORT_BY_DATE, reverse=True)
            return admin_response
        except Exception as exc:
            logger.exception("Failed to load admin page data: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to load admin data.")


    @staticmethod
    async def upload_files(files: list[UploadFile] = File(...)) -> AdminResponse:
        try:
            if not files:
                raise HTTPException(status_code=400, detail="No files were uploaded.")

            os.makedirs(constants.DOCUMENT_DATA_DIR, exist_ok=True)
            os.makedirs(constants.SQL_DATA_DIR, exist_ok=True)

            for file in files:
                if not file.filename:
                    raise HTTPException(status_code=400, detail="One of the uploaded files has no filename.")

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

                await save_file(file_dir, file)

            admin_response = AdminResponse(ai_response="Files are uploaded.", status=constants.OK)
            admin_response.uploaded_files = (get_file_name_from_dir(constants.SORT_BY_DATE, reverse=True))
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