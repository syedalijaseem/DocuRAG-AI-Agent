"""Scalability tests for performance and large data handling.

These tests verify the application can handle large volumes of data.
"""
import pytest
from unittest.mock import MagicMock, patch
import time

from models import (
    ChunkWithPage,
    RAGChunkAndSrc,
    SearchResult,
    QueryResult,
    QueryPdfEventData,
)


class TestLargeDataHandling:
    """Tests for handling large amounts of data."""
    
    def test_create_many_chunks(self):
        """Should handle creating many chunk objects efficiently."""
        start = time.time()
        chunks = [ChunkWithPage(text=f"Chunk {i}", page=i + 1) for i in range(1000)]
        elapsed = time.time() - start
        
        assert len(chunks) == 1000
        assert elapsed < 1.0  # Should be fast
    
    def test_rag_chunk_with_large_payload(self):
        """Should handle RAGChunkAndSrc with many chunks."""
        chunks = [ChunkWithPage(text=f"Content {i}", page=i + 1) for i in range(500)]
        rag_chunk = RAGChunkAndSrc(chunks=chunks, source_id="large_doc.pdf")
        
        assert len(rag_chunk.chunks) == 500
    
    def test_search_result_with_many_contexts(self):
        """Should handle search results with many contexts."""
        contexts = [f"Context {i}" for i in range(100)]
        sources = [f"source_{i}.pdf, page {i + 1}" for i in range(100)]
        scores = [0.99 - (i * 0.005) for i in range(100)]
        
        result = SearchResult(contexts=contexts, sources=sources, scores=scores)
        assert len(result.contexts) == 100
    
    def test_query_result_with_long_answer(self):
        """Should handle very long answers."""
        long_answer = "This is a detailed answer. " * 1000
        result = QueryResult(
            answer=long_answer,
            sources=["doc.pdf, page 1"],
            num_contexts=5
        )
        assert len(result.answer) > 25000
    
    def test_deep_history(self):
        """Should handle long conversation histories."""
        history = [
            {"role": "user", "content": f"Question {i}"}
            if i % 2 == 0 else
            {"role": "assistant", "content": f"Answer {i}"}
            for i in range(100)
        ]
        
        from models import ScopeType
        data = QueryPdfEventData(
            question="Next question",
            chat_id="chat_123",
            scope_type=ScopeType.CHAT,
            scope_id="chat_123",
            history=history
        )
        assert len(data.history) == 100


class TestBatchOperations:
    """Tests for batch operations and bulk processing."""
    
    @pytest.fixture
    def mock_mongo_setup(self):
        """Setup mocked MongoDB."""
        with patch('vector_db.MongoClient') as mock_client:
            with patch.dict('os.environ', {'MONGODB_URI': 'mongodb://test:27017'}):
                mock_collection = MagicMock()
                mock_db = MagicMock()
                mock_db.__getitem__ = MagicMock(return_value=mock_collection)
                mock_client.return_value.__getitem__ = MagicMock(return_value=mock_db)
                yield mock_client, mock_collection
    
    def test_bulk_upsert_many_documents(self, mock_mongo_setup):
        """Should handle bulk upserting many documents."""
        mock_client, mock_collection = mock_mongo_setup
        from vector_db import MongoDBStorage
        
        storage = MongoDBStorage()
        
        # Simulate 100 document chunks
        ids = [f"doc_{i}" for i in range(100)]
        vectors = [[0.1] * 10 for _ in range(100)]  # Simplified vectors
        payloads = [{"source": "test.pdf", "text": f"Text {i}", "page": i + 1} for i in range(100)]
        
        storage.upsert(ids, vectors, payloads)
        
        # Verify bulk_write was called once with all operations
        mock_collection.bulk_write.assert_called_once()
        call_args = mock_collection.bulk_write.call_args
        operations = call_args[0][0]
        assert len(operations) == 100
    
    def test_search_top_k_scaling(self, mock_mongo_setup):
        """Should handle various top_k values efficiently."""
        mock_client, mock_collection = mock_mongo_setup
        mock_collection.aggregate.return_value = iter([])
        
        from vector_db import MongoDBStorage
        storage = MongoDBStorage()
        
        for top_k in [1, 5, 10, 20, 50]:
            storage.search([0.1, 0.2], top_k=top_k)
            
        # Should have been called 5 times
        assert mock_collection.aggregate.call_count == 5


class TestModelSerialization:
    """Tests for model serialization performance."""
    
    def test_query_result_to_dict(self):
        """Should efficiently convert to dict."""
        result = QueryResult(
            answer="Test answer",
            sources=["src1", "src2", "src3"],
            num_contexts=3,
            history=[{"role": "user", "content": "q1"}, {"role": "assistant", "content": "a1"}],
            avg_confidence=0.85
        )
        
        start = time.time()
        for _ in range(1000):
            result.model_dump()
        elapsed = time.time() - start
        
        assert elapsed < 1.0  # 1000 serializations should be fast
    
    def test_chunk_batch_serialization(self):
        """Should efficiently serialize many chunks."""
        chunks = [ChunkWithPage(text=f"Content {i}", page=i + 1) for i in range(100)]
        
        start = time.time()
        serialized = [c.model_dump() for c in chunks]
        elapsed = time.time() - start
        
        assert len(serialized) == 100
        assert elapsed < 0.5


class TestMemoryEfficiency:
    """Tests for memory-efficient patterns."""
    
    def test_search_result_with_large_texts(self):
        """Should handle contexts with large text content."""
        large_text = "Lorem ipsum " * 1000  # ~12KB per context
        contexts = [f"{large_text} Context {i}" for i in range(10)]
        
        result = SearchResult(
            contexts=contexts,
            sources=[f"doc{i}.pdf" for i in range(10)],
            scores=[0.9] * 10
        )
        
        # Should handle without issue
        assert len(result.contexts) == 10
        assert len(result.contexts[0]) > 10000
    
    def test_chunk_with_large_text(self):
        """Should handle individual chunks with large text."""
        large_text = "Word " * 10000  # ~50KB
        chunk = ChunkWithPage(text=large_text, page=1)
        
        assert len(chunk.text) > 40000
