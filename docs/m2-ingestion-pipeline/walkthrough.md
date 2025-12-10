# M2: Ingestion Pipeline - Development Walkthrough

## Overview

M2 refactored the PDF ingestion pipeline to use the new Chunk model from M1, integrating with the document upload flow and enabling proper status tracking.

**Duration:** December 10, 2025  
**Branch:** `feature/m2-ingestion-pipeline`

---

## What Was Implemented

### New Services Created

| Service            | Purpose                                               |
| ------------------ | ----------------------------------------------------- |
| `chunk_service.py` | Save/delete chunks, deterministic IDs, status updates |
| `chunk_search.py`  | Document-scoped vector search via DocumentScope       |

### Key Changes

1. **IngestPdfEventData** - Added `document_id` field for chunk linking

2. **rag_ingest_pdf** - Refactored to:

   - Use `chunk_service.save_chunks()` instead of MongoDBStorage.upsert()
   - Save to `chunks` collection (not `documents`)
   - Update Document status to `ready` after ingest

3. **rag_query_pdf_ai** - Updated to:
   - Use `chunk_search.search_for_scope()`
   - Query `chunks` collection with document_id filter
   - Get document_ids from DocumentScope first

---

## Architectural Changes

### Before (M0-M1)

```
Upload → MongoDBStorage.upsert(scope_type, scope_id)
                    ↓
         documents collection (chunks + scope info)
```

### After (M2)

```
Upload → chunk_service.save_chunks(document_id)
                    ↓
         chunks collection (references document_id only)
                    ↓
         Document.status = "ready"
```

---

## Deterministic Chunk IDs

Chunks are now idempotent:

```python
chunk_id = uuid5(NAMESPACE_URL, f"{document_id}:{chunk_index}")
```

Same document + same chunk = same ID → re-ingest updates, not duplicates.

---

## Test Results

### Summary: 139 Tests Passing ✅

| Test Suite     | Tests | Status |
| -------------- | ----- | ------ |
| Auth (M0)      | 50    | ✅     |
| Document (M1)  | 70    | ✅     |
| Ingestion (M2) | 19    | ✅     |

---

## Files Changed

| File                          | Change                                             |
| ----------------------------- | -------------------------------------------------- |
| `models.py`                   | Added `document_id` to IngestPdfEventData          |
| `main.py`                     | Refactored `rag_ingest_pdf` and `rag_query_pdf_ai` |
| `chunk_service.py`            | NEW - Chunk CRUD operations                        |
| `chunk_search.py`             | NEW - Document-scoped vector search                |
| `tests/test_ingestion.py`     | NEW - 19 unit tests                                |
| `docs/m2-ingestion-pipeline/` | requirements.md, tasks.md                          |

---

## MongoDB Vector Search Index Required

Update the vector search index on `chunks` collection:

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

- **M3**: Query Integration (already using chunk_search)
- **M4**: Frontend Chat Upload UI
- **M5**: Frontend Project Upload UI
