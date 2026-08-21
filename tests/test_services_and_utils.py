from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_core.documents import Document
from fastapi import HTTPException

from common import constants
from common.ai_app_util import AiAppUtil
from common.rag_util import RAGUtil
from common.rerank_util import RerankUtil
from common.validate_util import ValidateUtil
from common.vector_util import VectorDatabaseManager
from model.admin_response import AdminResponse
from model.prompt_response import PromptResponse
from service.rag_service import RAGServiceImpl


def test_text_to_safe_html_strips_unsafe_markup():
    result = AiAppUtil.text_to_safe_html("**bold** <script>alert(1)</script><img src=x>")
    assert "<strong>bold</strong>" in result
    assert "script" not in result
    assert "img" not in result


def test_move_to_archive_moves_files_and_avoids_collision(tmp_path, monkeypatch):
    source = tmp_path / "documents"
    archive = tmp_path / "archive"
    source.mkdir()
    archive.mkdir()
    (source / "doc.txt").write_text("new")
    (archive / "doc.txt").write_text("old")
    monkeypatch.setattr(constants, "ARCHIVE_DIR", str(archive))

    assert AiAppUtil.move_to_archive(source) == 1
    assert not (source / "doc.txt").exists()
    archived = list(archive.glob("doc_*.txt"))
    assert len(archived) == 1
    assert archived[0].read_text() == "new"


def test_rag_context_and_prompt_formatting():
    documents = [
        (Document(page_content=" first fact ", metadata={"source": "a.txt"}), 0.9876),
        Document(page_content="", metadata={"source": "empty"}),
        Document(page_content="second fact", metadata={}),
    ]
    context = RAGUtil.build_context(documents)
    assert "[1] (source: a.txt, relevance: 0.988)" in context
    assert "first fact" in context and "second fact" in context
    assert "empty" not in context
    assert RAGUtil.format_prompt(context, "question").endswith("Question: question\n\nAnswer:")


@pytest.mark.asyncio
async def test_rag_generate_calls_ollama_and_sanitizes_response(monkeypatch):
    chat = AsyncMock(return_value=Mock(message=Mock(content="**answer** <script>bad</script>")))
    client = Mock(chat=chat)
    monkeypatch.setattr("common.rag_util.ollama.AsyncClient", Mock(return_value=client))

    result = await RAGUtil.generate("question", [Document(page_content="context")])

    assert result == "<p><strong>answer</strong> bad</p>"
    chat.assert_awaited_once()
    assert chat.call_args.kwargs["model"] == constants.RAG_MODEL


def test_validate_prompt_rejects_invalid_before_external_guard():
    with patch.object(ValidateUtil, "_validate_with_llama_guard") as guard:
        for value in (None, "", "   ", "```wrapped```", "'" * (constants.MAX_PROMPT_LENGTH + 1)):
            status, normalized = ValidateUtil.validate_prompt(value)
            assert (status, normalized) == ("unsafe", None)
        guard.assert_not_called()


def test_validate_prompt_escapes_and_calls_guard(monkeypatch):
    monkeypatch.setattr(ValidateUtil, "_validate_with_llama_guard", Mock(return_value="safe"))
    status, normalized = ValidateUtil.validate_prompt("  hello\n<world>  ")
    assert status == "safe"
    assert normalized == "hello &lt;world&gt;"


def test_validate_prompt_rejects_guard_unsafe(monkeypatch):
    monkeypatch.setattr(ValidateUtil, "_validate_with_llama_guard", Mock(return_value="unsafe"))
    assert ValidateUtil.validate_prompt("hello") == ("unsafe", None)


@pytest.mark.asyncio
async def test_rag_service_stops_when_prompt_is_unsafe(monkeypatch):
    monkeypatch.setattr("service.rag_service.validate_prompt", Mock(return_value=("unsafe", None)))
    generate = AsyncMock()
    monkeypatch.setattr("service.rag_service.RAGUtil.generate", generate)

    response = await RAGServiceImpl.process_rag_prompt("unsafe")

    assert response == PromptResponse(status=constants.ERROR, response="Prompt validation failed. Please ensure your prompt is safe and valid.")
    generate.assert_not_called()


@pytest.mark.asyncio
async def test_rag_service_retrieves_and_generates(monkeypatch):
    monkeypatch.setattr("service.rag_service.validate_prompt", Mock(return_value=("safe", "normalized")))
    vector_db = Mock()
    vector_db.similarity_search.return_value = [(Document(page_content="fact"), 0.9)]
    monkeypatch.setattr("service.rag_service.get_vector_db_manager", Mock(return_value=vector_db))
    monkeypatch.setattr("service.rag_service.RAGUtil.generate", AsyncMock(return_value="answer"))

    response = await RAGServiceImpl.process_rag_prompt("raw")

    assert response == PromptResponse(status=constants.OK, response="answer")
    vector_db.similarity_search.assert_called_once_with("normalized", k=constants.RAG_CONTEXT_TOP_K)


def test_rerank_heuristic_prioritizes_lexical_overlap():
    reranker = RerankUtil()
    docs = [
        (Document(page_content="unrelated text"), 0.8),
        (Document(page_content="python testing guide"), 0.7),
    ]
    result = reranker._heuristic_rerank_documents("python testing", docs, 2)
    assert result[0][0].page_content == "python testing guide"


def test_vector_helpers_dedupe_and_boost_exact_matches():
    first = Document(page_content="Exact phrase", metadata={"source": "a"})
    duplicate = Document(page_content="Exact phrase", metadata={"source": "a"})
    other = Document(page_content="other", metadata={"source": "b"})
    manager = VectorDatabaseManager.__new__(VectorDatabaseManager)
    assert manager._dedupe_documents([first, duplicate, other]) == [first, other]
    scored = manager._boost_exact_matches(" exact   phrase ", [(first, 0.4), (other, 0.9)])
    assert scored[0][1] == 1.0
    assert scored[1][1] == 0.9
