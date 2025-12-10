# M2: Ingestion Pipeline - Requirements Specification

## Overview

M2 refactors the existing PDF ingestion pipeline to use the new Chunk model from M1. It integrates with the document upload flow, validates files, tracks progress via Document status, and uses deterministic chunking for deduplication.

**Estimated Duration:** 2-3 days  
**Dependencies:** M1 (Core Data Model) - Complete ✅

---

## Current State

The existing ingestion pipeline (`rag_ingest_pdf` in `main.py`):

1. Downloads PDF from S3 to temp file
2. Calls `load_and_chunk_pdf()` to extract text chunks
3. Generates embeddings via `embed_texts()`
4. Stores in `documents` collection via `MongoDBStorage.upsert()`

**Issues:**

- Uses separate `documents` collection, not the new `chunks` collection
- Doesn't update Document model status
- No document_id linkage between chunks and Document record
- Duplicates scope_type/scope_id on every chunk

---

## Target State

After M2:

1. Upload endpoint (M1) creates Document with status=`pending`
2. Inngest job downloads, chunks, embeds
3. Chunks saved to `chunks` collection with `document_id` reference
4. Document status updated to `ready`
5. Vector search queries `chunks` collection by `document_id`

---

## Functional Requirements

### FR-1: Refactor Ingest to Use Chunk Model

**Description:** Update `rag_ingest_pdf` to create Chunk records instead of using MongoDBStorage.upsert().

**Changes:**

- Accept `document_id` in event data (sent by upload endpoint)
- Create Chunk model instances for each text chunk
- Save directly to `chunks` collection via pymongo
- Reference document by `document_id` only

**Acceptance Criteria:**

- [ ] Event data includes `document_id`
- [ ] Chunks saved to `chunks` collection
- [ ] Each chunk has `document_id`, `chunk_index`, `page_number`, `text`, `embedding`
- [ ] No scope info duplicated on chunks (scopes are via DocumentScope)

---

### FR-2: Update Document Status After Ingest

**Description:** Set Document status to `ready` after successful ingestion.

**Changes:**

- After all chunks are saved, update Document: `status: "ready"`
- On failure, leave status as `pending` (retry will happen)

**Acceptance Criteria:**

- [ ] Document status changes from `pending` to `ready` after ingest
- [ ] Status stays `pending` if ingest fails
- [ ] Queries can filter for `ready` documents only

---

### FR-3: Deterministic Chunk IDs

**Description:** Generate deterministic chunk IDs to support idempotent ingestion.

**Implementation:**

```python
# Chunk ID = UUID5(document_id, chunk_index)
chunk_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document_id}:{chunk_index}"))
```

**Acceptance Criteria:**

- [ ] Same document produces same chunk IDs
- [ ] Re-ingest of same document updates existing chunks (upsert)
- [ ] Different documents have different chunk IDs

---

### FR-4: Update Vector Search to Query Chunks

**Description:** Refactor `MongoDBStorage.search()` or replace with direct chunk queries.

**Changes:**

- Query `chunks` collection instead of `documents`
- Filter by `document_id` joined via DocumentScope
- Maintain score and source info in results

**Acceptance Criteria:**

- [ ] Vector search queries `chunks` collection
- [ ] Results include document/source info via lookup
- [ ] Scope filtering works via DocumentScope join

---

## Non-Functional Requirements

### NFR-1: Performance - Batch Embedding

**Category:** Performance

**Description:** Embedding generation should be batched for efficiency.

**Metric:** Process 100 chunks in < 30 seconds

---

### NFR-2: Reliability - Idempotent Ingestion

**Category:** Reliability

**Description:** Re-running ingest on the same document should be safe.

**Implementation:**

- Use upsert with deterministic chunk IDs
- Final status update is atomic

**Metric:** Re-ingest produces identical result, no duplicates

---

### NFR-3: Robustness - Error Handling

**Category:** Robustness

**Description:** Failed ingestions should not leave corrupted state.

**Implementation:**

- Keep Document status as `pending` until ALL chunks saved
- Only then update to `ready`
- Failed partial ingests can be retried

---

## MongoDB Collections (Updated)

### `chunks` collection (new usage)

```javascript
{
  "id": "chunk_abc123",
  "document_id": "doc_xyz789",  // FK to documents
  "chunk_index": 0,
  "page_number": 1,
  "text": "The text content...",
  "embedding": [0.1, 0.2, ...]  // 1536 dims
}
```

### Vector Search Index (update required)

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

## Files to Modify

| File                 | Change                                       |
| -------------------- | -------------------------------------------- |
| `main.py`            | Refactor `rag_ingest_pdf` to use Chunk model |
| `vector_db.py`       | Update search to query `chunks` collection   |
| `document_routes.py` | Ensure `document_id` passed to Inngest event |

---

## Acceptance Tests

| ID    | Test              | Pass Criteria                                 |
| ----- | ----------------- | --------------------------------------------- |
| M2-T1 | Ingest PDF        | Chunks created in chunks collection           |
| M2-T2 | Document status   | Status changes from pending to ready          |
| M2-T3 | Deterministic IDs | Re-ingest produces same chunks (no dupes)     |
| M2-T4 | Vector search     | Search returns results from chunks collection |
| M2-T5 | Error recovery    | Failed ingest leaves status as pending        |
