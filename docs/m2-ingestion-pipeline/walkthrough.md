# M2: Ingestion Pipeline - Development Walkthrough

## Overview

M2 refactored the PDF ingestion pipeline to use the new Chunk model from M1, integrating with the document upload flow and enabling proper status tracking.

**Duration:** December 10, 2025  
**Branch:** `feature/m2-ingestion-pipeline`  
**Final Commit:** `47d08df`

---

## What Was Implemented

### Services Created

| Service            | Purpose                                               |
| ------------------ | ----------------------------------------------------- |
| `chunk_service.py` | Save/delete chunks, deterministic IDs, status updates |
| `chunk_search.py`  | Document-scoped vector search via DocumentScope       |

### API Endpoints Added

| Method | Endpoint                     | Description              |
| ------ | ---------------------------- | ------------------------ |
| GET    | `/api/documents/{id}/status` | Track ingestion progress |

### Key Changes

1. **IngestPdfEventData** - Added `document_id` field
2. **rag_ingest_pdf** - Uses chunk_service, updates status to ready
3. **rag_query_pdf_ai** - Uses chunk_search with document_id filter
4. **PDF Error Handling** - Empty content detection, error logging

---

## Architectural Changes

```
Before: chunks stored with scope_type/scope_id
After:  chunks reference document_id only → scope via DocumentScope
```

---

## Deterministic Chunk IDs

```python
chunk_id = uuid5(NAMESPACE_URL, f"{document_id}:{chunk_index}")
```

Same document + same chunk = same ID → re-ingest updates, not duplicates.

---

## Test Results

### Summary: 293 Tests Passing ✅

| Test Suite                     | Tests |
| ------------------------------ | ----- |
| Auth (M0)                      | 50    |
| Document (M1)                  | 70    |
| Ingestion (M2)                 | 35    |
| Query (M3)                     | 6     |
| Availability/Speed             | 11    |
| API Routes                     | 20    |
| Other (security, models, etc.) | 101   |

### 9-Aspect Quality Coverage ✅

| Aspect         | Status                                          |
| -------------- | ----------------------------------------------- |
| Security       | ✅ Path validation, null bytes, scope isolation |
| Scalability    | ✅ Bulk ops, 100 chunks/call                    |
| Robustness     | ✅ Empty scope, error propagation               |
| Efficiency     | ✅ 1536 dims, single bulk_write                 |
| Availability   | ✅ Graceful degradation                         |
| Speed          | ✅ 10K IDs < 1s, pipeline latency               |
| Optimization   | ✅ Atomic updates, checksum dedup               |
| Best Practices | ✅ Docstrings, Pydantic, types                  |
| Architecture   | ✅ Service separation, DocumentScope            |

---

## Files Changed

| File                               | Change                                        |
| ---------------------------------- | --------------------------------------------- |
| `models.py`                        | Added `document_id` to IngestPdfEventData     |
| `main.py`                          | Refactored ingest + query, PDF error handling |
| `document_routes.py`               | Added status endpoint                         |
| `api_routes.py`                    | M1 migration: DocumentScope, checksum dedup   |
| `chunk_service.py`                 | NEW - Chunk CRUD operations                   |
| `chunk_search.py`                  | NEW - Document-scoped vector search           |
| `tests/test_ingestion.py`          | NEW - 19 unit tests                           |
| `tests/test_ingestion_quality.py`  | NEW - 16 quality tests                        |
| `tests/test_availability_speed.py` | NEW - 11 quality tests                        |

---

## MongoDB Vector Search Index

Required on `chunks` collection:

```json
{
  "fields": [
    {
      "numDimensions": 1536,
      "path": "embedding",
      "similarity": "cosine",
      "type": "vector"
    },
    { "path": "document_id", "type": "filter" }
  ]
}
```

---

## Next Steps

- **M4**: Frontend Chat Upload UI
- **M5**: Frontend Project Upload UI
