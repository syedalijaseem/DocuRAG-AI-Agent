# M2: Ingestion Pipeline - Task Breakdown

## Overview

Refactor the PDF ingestion pipeline to use the M1 Chunk model, update Document status, and enable vector search via the chunks collection.

**Estimated Duration:** 2-3 days  
**Dependencies:** M1 (Core Data Model) - Complete ✅

---

## Tasks

### M2.1: Refactor rag_ingest_pdf (~3h)

- [ ] Update `IngestPdfEventData` model to include `document_id`
- [ ] Modify `_upsert` function in `rag_ingest_pdf`:
  - [ ] Create Chunk model instances instead of raw dicts
  - [ ] Use deterministic IDs: `uuid5(NAMESPACE_URL, f"{doc_id}:{index}")`
  - [ ] Bulk insert to `chunks` collection via pymongo
  - [ ] Remove scope_type/scope_id from chunk data (use DocumentScope)
- [ ] Add `_update_status` step to set Document status to `ready`

---

### M2.2: Update Vector Search (~2h)

- [ ] Modify `MongoDBStorage.search()` to query `chunks` collection
- [ ] Update collection name from `documents` to `chunks`
- [ ] Update filter to use `document_id` instead of `scope_type/scope_id`
- [ ] Add two-stage query approach:
  1. Get document_ids from DocumentScope for user's scopes
  2. Vector search chunks with document_id IN filter
- [ ] Preserve source info by looking up Document.filename

---

### M2.3: Update document_routes.py (~1h)

- [ ] Verify `document_id` is passed in Inngest event (already done in M1)
- [ ] Ensure upload returns immediately, ingestion is async
- [ ] Add endpoint to check document status: `GET /api/documents/{id}/status`

---

### M2.4: Create Chunk Storage Service (~2h)

- [ ] Create `chunk_service.py` with:
  - [ ] `save_chunks(document_id, chunks)` - bulk insert
  - [ ] `delete_chunks(document_id)` - cascade delete
  - [ ] `get_chunks(document_id)` - for debugging
- [ ] Use pymongo directly (not MongoDBStorage)
- [ ] Include proper error handling

---

### M2.5: File Validation Enhancement (~1h)

- [ ] Add validation in ingestion (not just upload):
  - [ ] PDF parsing error handling
  - [ ] Empty document handling
  - [ ] Max page count limit (optional)
- [ ] Set status to `error` on validation failure

---

## Testing Tasks

### M2.6: Unit Tests (~1.5h)

- [ ] Create `tests/test_ingestion.py`
- [ ] Test chunk ID generation is deterministic
- [ ] Test Chunk model creation
- [ ] Test status transitions
- [ ] Test chunk service functions

---

### M2.7: Integration Tests (~1.5h)

- [ ] Test full ingest flow with mock PDF
- [ ] Test re-ingest produces same chunks
- [ ] Test vector search returns correct results
- [ ] Test failed ingest handling

---

### M2.8: Quality Tests (~1h)

- [ ] Performance: batch embedding within limits
- [ ] Reliability: idempotent ingestion
- [ ] Robustness: error handling

---

## Documentation Tasks

### M2.9: Update Documentation (~0.5h)

- [ ] Update vector search index instructions
- [ ] Document new chunk_service.py
- [ ] Create M2 walkthrough

---

## Task Summary

| Category      | Tasks       | Estimated Time      |
| ------------- | ----------- | ------------------- |
| Refactoring   | M2.1-M2.5   | 9h                  |
| Testing       | M2.6-M2.8   | 4h                  |
| Documentation | M2.9        | 0.5h                |
| **Total**     | **9 tasks** | **~13.5h (2 days)** |

---

## Completion Checklist

- [ ] rag_ingest_pdf creates Chunk records
- [ ] Document status updates to `ready`
- [ ] Vector search queries chunks collection
- [ ] Deterministic chunk IDs work
- [ ] All tests passing
- [ ] 9 quality aspects verified
- [ ] Committed and pushed
- [ ] Ready for M3 (Query Integration)
