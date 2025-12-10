# M1: Core Data Model & API - Task Breakdown

## Overview

Implement the core data models and API endpoints for the scoped document system. This milestone establishes the foundation for document management with proper scope isolation, checksum-based deduplication, and lifecycle status tracking.

**Estimated Duration:** 2-3 days  
**Dependencies:** M0 (Authentication) - Complete ✅

---

## Backend Tasks

### M1.1: Update Document Model (~2h)

- [ ] Add `status` field to Document model
  - [ ] Define DocumentStatus enum: `pending`, `ready`, `deleting`
  - [ ] Add default value: `pending`
  - [ ] Update existing Document model in `models.py`
- [ ] Add `checksum` field to Document model
  - [ ] SHA-256 hash of file content
  - [ ] Unique constraint
- [ ] Add `size_bytes` field to Document model
- [ ] Add field validators for status transitions
- [ ] Update any existing document queries to filter by status

---

### M1.2: Create DocumentScope Model (~1.5h)

- [ ] Define DocumentScope model in `models.py`
  - [ ] `id`: UUID primary key
  - [ ] `document_id`: Foreign key
  - [ ] `scope_type`: Enum ("chat" | "project")
  - [ ] `scope_id`: String
  - [ ] `linked_at`: DateTime, default now
- [ ] Define ScopeType enum
- [ ] Add Pydantic validators
  - [ ] scope_type must be valid enum
  - [ ] scope_id must be non-empty

---

### M1.3: Create Chunk Model (~1.5h)

- [ ] Define Chunk model in `models.py`
  - [ ] `id`: UUID primary key
  - [ ] `document_id`: Foreign key
  - [ ] `chunk_index`: Integer (0-indexed)
  - [ ] `page_number`: Integer
  - [ ] `text`: String
  - [ ] `embedding`: List[float] (1536 dimensions)
- [ ] Add field validators
  - [ ] chunk_index >= 0
  - [ ] page_number >= 0
  - [ ] embedding length = 1536

---

### M1.4: Setup MongoDB Indexes (~1h)

- [ ] Create `setup_document_indexes.py` script
  - [ ] Documents: unique index on checksum
  - [ ] Documents: unique index on s3_key
  - [ ] Documents: index on status
  - [ ] DocumentScopes: index on document_id
  - [ ] DocumentScopes: compound index on (scope_type, scope_id)
  - [ ] DocumentScopes: unique compound index on (document_id, scope_type, scope_id)
  - [ ] Chunks: index on document_id
- [ ] Run script against dev database
- [ ] Document vector search index setup (Atlas UI)

---

### M1.5: Upload Endpoint (~3h)

- [ ] Create `document_routes.py` with APIRouter
- [ ] Implement `POST /api/upload` endpoint
  - [ ] Accept multipart/form-data
  - [ ] Parse query params: scope_type, scope_id
  - [ ] Validate authenticated user
  - [ ] Validate scope ownership
    - [ ] For chat: check chat.user_id matches
    - [ ] For project: check project.user_id matches
  - [ ] Validate file type (PDF only)
    - [ ] Check file extension
    - [ ] Check magic bytes (%PDF-)
  - [ ] Validate file size (< 50MB)
  - [ ] Calculate SHA-256 checksum
  - [ ] Check for existing document by checksum
    - [ ] If exists: reuse document_id
    - [ ] If not: upload to S3, create Document
  - [ ] Create DocumentScope link
  - [ ] Queue ingestion job (if new document)
  - [ ] Return document metadata
- [ ] Add error handlers for:
  - [ ] 400: Invalid file type
  - [ ] 404: Scope not found
  - [ ] 413: File too large
  - [ ] 403: Not owner of scope
- [ ] Register router in main.py

---

### M1.6: Get Documents Endpoint (~2h)

- [ ] Implement `GET /api/chats/{chat_id}/documents`
  - [ ] Validate user owns chat
  - [ ] Query DocumentScopes for chat
  - [ ] Join to Documents (status != "deleting")
  - [ ] Optional query param: `include_project`
  - [ ] If true and chat has project_id, include project docs
  - [ ] Return separate arrays for chat and project docs
- [ ] Implement `GET /api/projects/{project_id}/documents`
  - [ ] Validate user owns project
  - [ ] Query DocumentScopes for project
  - [ ] Join to Documents (status != "deleting")
  - [ ] Return document list

---

### M1.7: Delete Document Endpoint (~2.5h)

- [ ] Implement `DELETE /api/documents/{doc_id}`
  - [ ] Parse optional query params: scope_type, scope_id
  - [ ] If scope params provided: unlink from specific scope
    - [ ] Validate user owns scope
    - [ ] Remove DocumentScope record
    - [ ] Check remaining scope links
    - [ ] If none: set status="deleting", queue cleanup
  - [ ] If no scope params: unlink from ALL user's scopes
    - [ ] Query all scopes user owns
    - [ ] Remove all DocumentScope links
    - [ ] If document orphaned: set status="deleting", queue cleanup
  - [ ] Return success status
- [ ] Add cleanup job placeholder (Inngest function stub)
  - [ ] Delete S3 file
  - [ ] Delete all Chunks
  - [ ] Delete Document record

---

## Integration Tasks

### M1.8: Wire Up Routes (~1h)

- [ ] Create `document_routes.py` APIRouter
- [ ] Add authentication dependency to all endpoints
- [ ] Register router in `main.py`
- [ ] Update CORS if needed
- [ ] Test all endpoints with curl/httpie

---

## Testing Tasks

### M1.9: Unit Tests (~2h)

- [ ] Create `tests/test_documents.py`
- [ ] Test Document model
  - [ ] Valid status values
  - [ ] Checksum format validation
  - [ ] Size validation
- [ ] Test DocumentScope model
  - [ ] Valid scope_type values
  - [ ] Scope ID validation
- [ ] Test Chunk model
  - [ ] Index validation
  - [ ] Embedding dimension validation

---

### M1.10: Integration Tests (~2h)

- [ ] Create `tests/test_document_api.py`
- [ ] Test upload endpoint
  - [ ] Success case: PDF upload to chat
  - [ ] Success case: duplicate file reuse
  - [ ] Failure: non-PDF file
  - [ ] Failure: oversized file
  - [ ] Failure: non-existent scope
  - [ ] Failure: scope not owned by user
- [ ] Test get documents endpoint
  - [ ] Success: get chat documents
  - [ ] Success: get with project docs
  - [ ] Failure: unauthorized chat
- [ ] Test delete endpoint
  - [ ] Success: unlink from scope
  - [ ] Success: orphan triggers delete
  - [ ] Failure: unauthorized

---

### M1.11: Quality Tests (~1.5h)

- [ ] Create `tests/test_document_quality.py`
- [ ] Security tests
  - [ ] Cross-user document access blocked
  - [ ] File type validation (magic bytes)
  - [ ] Scope ownership verification
- [ ] Performance tests
  - [ ] Checksum calculation < 1s for 5MB
  - [ ] Document query < 200ms
- [ ] Robustness tests
  - [ ] Handle corrupt PDF gracefully
  - [ ] Handle S3 upload failure

---

## Documentation Tasks

### M1.12: Update API Documentation (~0.5h)

- [ ] Document new endpoints in README or API docs
- [ ] Add example requests/responses
- [ ] Update implementation_plan.md to mark M1 complete

---

## Dependencies

```
M0 (Authentication) ──► M1 (Core Data Model)
                              │
                              ├──► User ownership validation
                              ├──► get_current_user dependency
                              └──► Protected route pattern
```

---

## Task Summary

| Category      | Tasks        | Estimated Time        |
| ------------- | ------------ | --------------------- |
| Models        | M1.1-M1.3    | 5h                    |
| Database      | M1.4         | 1h                    |
| Endpoints     | M1.5-M1.7    | 7.5h                  |
| Integration   | M1.8         | 1h                    |
| Testing       | M1.9-M1.11   | 5.5h                  |
| Documentation | M1.12        | 0.5h                  |
| **Total**     | **12 tasks** | **~20.5h (2-3 days)** |

---

## Completion Checklist

- [ ] All models defined and validated
- [ ] All indexes created
- [ ] All endpoints implemented
- [ ] All tests passing
- [ ] 9 quality aspects verified:
  - [ ] Security: Access control verified
  - [ ] Robustness: Error handling complete
  - [ ] Scalability: Stateless design
  - [ ] Accessibility: N/A (backend only)
  - [ ] Optimization: Indexes created
  - [ ] UI: N/A (backend only)
  - [ ] UX: Clear error messages
  - [ ] Reliability: Checksum dedup working
  - [ ] Efficiency: No duplicate queries
- [ ] Committed and pushed
- [ ] Ready for M2 (Ingestion Pipeline)
