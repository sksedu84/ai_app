import bleach
import markdown
import shutil

from common import constants
from pathlib import Path
from config.logger import Logger

logger = Logger.get_logger()

class AiAppUtil:
    """Common input validation helpers."""

    @staticmethod
    def text_to_safe_html(text: str) -> str:
        raw_html = markdown.markdown(text)
        allowed_tags = [
            "p", "ul", "ol", "li", "strong", "em", "br", "blockquote"
        ]
        allowed_attrs = {}
        clean_html = bleach.clean(
            raw_html,
            tags=allowed_tags,
            attributes=allowed_attrs,
            strip=True
        )
        return clean_html

    @staticmethod
    def move_to_archive(source_dir_path) -> int:
        """Move files to the archive directory."""
        source_dir = Path(source_dir_path)
        archive_dir = Path(constants.ARCHIVE_DIR)
        if not source_dir.exists():
            logger.info("No document directory found to archive: %s", source_dir)
            return 0

        archive_dir.mkdir(parents=True, exist_ok=True)

        moved_files = 0
        for item in source_dir.iterdir():
            if item.name.startswith('.') or not item.is_file():
                continue

            destination = archive_dir / item.name
            if destination.exists():
                # Keep archive files unique by suffixing duplicate names.
                destination = archive_dir / f"{item.stem}_{int(item.stat().st_mtime_ns)}{item.suffix}"

            shutil.move(str(item), str(destination))
            moved_files += 1

        logger.info("Moved %d file(s) from %s to %s", moved_files, source_dir, archive_dir)
        return moved_files
