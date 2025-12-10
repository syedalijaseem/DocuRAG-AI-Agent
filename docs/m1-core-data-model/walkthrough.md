# M1: Core Data Model & API - Development Walkthrough

## Overview

M1 established the core data models and API endpoints for the scoped document system. This enables documents to be uploaded to specific scopes (chats or projects), with deduplication via checksums and proper access control.

**Duration:** December 10, 2025  
**Branch:** `feature/m1-core-data-model`  
**Commits:** 2 (6a0c51f, 6b002a1)

---

## What Was Implemented

### Models Created

| Model                 | Purpose                                   |
| --------------------- | ----------------------------------------- |
| `DocumentStatus` enum | Lifecycle: pending → ready → deleting     |
| `Document`            | Global document store with checksum dedup |
| `DocumentScope`       | Junction table linking docs to scopes     |
| `Chunk`               | Text chunks with 1536-dim embeddings      |

### Key Design Decisions

1. **Global Document Store**: Documents stored once, linked many times via DocumentScope

   - Enables deduplication via SHA-256 checksum
   - Reuses storage for identical files across scopes

2. **Scope Junction Pattern**: DocumentScope links documents to chats/projects

   - One document can belong to multiple scopes
   - Clean deletion: remove link, orphan cleanup handles rest

3. **1536 Dimensions for Embeddings**: Chose text-embedding-3-small (1536) over large (3072)

   - 2x faster embedding generation
   - 50% less storage
   - Slightly lower quality but acceptable for speed priority

4. **Status-Based Lifecycle**: Documents transition through pending → ready → deleting
   - Immediate UI feedback (status=pending on upload)
   - Graceful deletion (status=deleting hides from queries)

---

## API Endpoints

| Method | Endpoint                       | Description                                      |
| ------ | ------------------------------ | ------------------------------------------------ |
| POST   | `/api/upload`                  | Upload PDF with scope validation, checksum dedup |
| GET    | `/api/chats/{id}/documents`    | Get chat docs (+project if requested)            |
| GET    | `/api/projects/{id}/documents` | Get project docs                                 |
| DELETE | `/api/documents/{id}`          | Unlink or cascade delete                         |

---

## Test Results

### Summary: 120 Tests Passing ✅

| Test Suite       | Tests | Status |
| ---------------- | ----- | ------ |
| Auth (M0)        | 50    | ✅     |
| Document Unit    | 25    | ✅     |
| Document Quality | 24    | ✅     |
| Document API     | 21    | ✅     |

### Quality Coverage (9 Aspects)

| Aspect         | Coverage                                                        |
| -------------- | --------------------------------------------------------------- |
| Security       | ✅ Path traversal blocked, checksum validation, scope ownership |
| Robustness     | ✅ Unicode support, edge cases, empty embeddings                |
| Scalability    | ✅ Lightweight models, ID-only references                       |
| Optimization   | ✅ Fast checksum (<1s for 5MB), 1536-dim embeddings             |
| Reliability    | ✅ Unique IDs, deterministic checksums, UTC timestamps          |
| Efficiency     | ✅ Checksum deduplication, minimal memory footprint             |
| Best Practices | ✅ Docstrings, type hints, Pydantic models                      |

---

## MongoDB Indexes Created

```javascript
// documents
{ checksum: 1 } (unique)
{ s3_key: 1 } (unique)
{ status: 1 }

// document_scopes
{ document_id: 1 }
{ scope_type: 1, scope_id: 1 }
{ document_id: 1, scope_type: 1, scope_id: 1 } (unique)

// chunks
{ document_id: 1 }
{ document_id: 1, chunk_index: 1 }
```

---

## Files Changed

| File                             | Change                                               |
| -------------------------------- | ---------------------------------------------------- |
| `models.py`                      | Added DocumentStatus, Document, DocumentScope, Chunk |
| `document_routes.py`             | NEW - Upload/Get/Delete endpoints                    |
| `setup_document_db.py`           | NEW - MongoDB indexes script                         |
| `main.py`                        | Registered document_routes                           |
| `tests/test_documents.py`        | NEW - 25 unit tests                                  |
| `tests/test_document_quality.py` | NEW - 24 quality tests                               |
| `tests/test_document_api.py`     | NEW - 21 integration tests                           |
| `docs/m1-core-data-model/`       | requirements.md, tasks.md, api_reference.md          |
| `docs/METHODOLOGY.md`            | NEW - Development workflow                           |

---

## Deviations from Original Plan

1. **No user_id on Documents**: Documents are owned via scopes, not directly

   - Rationale: Enables cross-user sharing in future team features

2. **Immediate cleanup instead of background job**: Delete cascade runs synchronously
   - Planned for M6 (background cleanup job)
   - Current implementation marks as "deleting" then cleans up immediately

---

## Verification

**Backend:**

- ✅ FastAPI docs loading at `/docs`
- ✅ Upload endpoint validates scope_type, scope_id, file
- ✅ All 120 tests passing

**Frontend:**

- ✅ Vite dev server running
- ✅ No regressions (M1 is backend-only)

---

## Next Steps

- **M2**: Refactor ingestion pipeline to use Chunk model
- **M4**: Frontend chat upload UI
- **M5**: Frontend project upload UI
