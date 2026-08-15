from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from common import constants
from common.vector_util import VectorDatabaseManager


class TestVectorDatabaseManager(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = VectorDatabaseManager.__new__(VectorDatabaseManager)
        self.manager.db = MagicMock()

    def test_ingest_documents_updates_metadata_for_renamed_file_without_reembedding(self) -> None:
        renamed_document = MagicMock()
        renamed_document.metadata = {"source": "/tmp/renamed.txt"}

        self.manager._get_file_hash = MagicMock(return_value="same-hash")
        self.manager._get_stored_file_hash = MagicMock(return_value=None)
        self.manager._get_existing_source_for_hash = MagicMock(return_value="/tmp/original.txt")
        self.manager._update_source_metadata = MagicMock(return_value=3)

        with patch.object(VectorDatabaseManager, "_load_documents", return_value=[renamed_document]), \
             patch.object(VectorDatabaseManager, "_chunk_documents") as mock_chunk_documents:
            result = self.manager.ingest_documents("/tmp")

        self.manager._update_source_metadata.assert_called_once_with(
            current_source="/tmp/original.txt",
            new_source="/tmp/renamed.txt",
            file_hash="same-hash",
        )
        mock_chunk_documents.assert_not_called()
        self.manager.db.add_documents.assert_not_called()
        assert result["status"] == constants.OK
        assert result["added_chunks"] == 0
        assert result["added_files"] == 0
        assert "without re-embedding" in result["message"]
        assert result["renamed_files"] == 1
        assert result["skipped_files"] == 1

    def test_ingest_documents_still_indexes_duplicate_content_when_original_is_present(self) -> None:
        original_document = MagicMock()
        original_document.metadata = {"source": "/tmp/original.txt"}
        duplicate_document = MagicMock()
        duplicate_document.metadata = {"source": "/tmp/duplicate.txt"}
        chunk = MagicMock()
        chunk.metadata = {"source": "/tmp/duplicate.txt"}

        self.manager._get_file_hash = MagicMock(side_effect=lambda path: "same-hash")
        self.manager._get_stored_file_hash = MagicMock(
            side_effect=lambda source: "same-hash" if source == "/tmp/original.txt" else None
        )
        self.manager._get_existing_source_for_hash = MagicMock(return_value="/tmp/original.txt")
        self.manager._update_source_metadata = MagicMock()
        self.manager._get_source_chunk_ids = MagicMock(return_value=[])

        with patch.object(
            VectorDatabaseManager,
            "_load_documents",
            return_value=[original_document, duplicate_document],
        ), patch.object(VectorDatabaseManager, "_chunk_documents", return_value=[chunk]) as mock_chunk_documents:
            result = self.manager.ingest_documents("/tmp")

        self.manager._update_source_metadata.assert_not_called()
        mock_chunk_documents.assert_called_once()
        self.manager.db.add_documents.assert_called_once()
        assert result["status"] == constants.OK
        assert result["added_chunks"] == 1
        assert result["added_files"] == 1
        assert result["renamed_files"] == 0


if __name__ == "__main__":
    unittest.main()

