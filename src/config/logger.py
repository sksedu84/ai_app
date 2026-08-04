import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from common import constants

class Logger:
    @staticmethod
    def get_logger() -> logging.Logger:
        logger = logging.getLogger(constants.APP_NAME)
        logger.setLevel(logging.INFO)
        logger.propagate = False

        log_format = logging.Formatter(constants.LOGGING_FORMAT)

        has_console = any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
        has_file = any(isinstance(h, RotatingFileHandler) for h in logger.handlers)
        if has_console and has_file:
            return logger

        log_dir = Path(os.getcwd()) / constants.LOG_FILE_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / constants.LOG_FILE_NAME

        if not has_file:
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=constants.ROTATING_FILE_MAX_SIZE,
                backupCount=constants.BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(log_format)
            logger.addHandler(file_handler)

        if not has_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(log_format)
            logger.addHandler(console_handler)

        return logger