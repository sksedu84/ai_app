import bleach
import markdown
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