# Document API Reference

## Overview

The Document API provides endpoints for uploading, retrieving, and deleting documents within scopes (chats or projects). Documents are stored globally and linked to scopes via `DocumentScope` records, enabling deduplication and multi-scope sharing.

---

## Base URL

```
http://localhost:8000/api
```

---

## Authentication

All endpoints require authentication via HTTP-only cookies (`access_token`).

---

## Endpoints

### Upload Document

**Upload a PDF document to a scope.**

```http
POST /api/upload?scope_type={type}&scope_id={id}
Content-Type: multipart/form-data
```

#### Query Parameters

| Parameter    | Type   | Required | Description               |
| ------------ | ------ | -------- | ------------------------- |
| `scope_type` | string | ✅       | `chat` or `project`       |
| `scope_id`   | string | ✅       | ID of the chat or project |

#### Request Body

| Field  | Type | Required | Description         |
| ------ | ---- | -------- | ------------------- |
| `file` | File | ✅       | PDF file (max 50MB) |

#### Response (201 Created)

```json
{
  "document_id": "doc_abc123",
  "filename": "research_paper.pdf",
  "size_bytes": 1048576,
  "status": "pending",
  "checksum": "sha256:...",
  "is_new": true
}
```

#### Error Responses

| Status | Description                    |
| ------ | ------------------------------ |
| 400    | Invalid file type (not PDF)    |
| 403    | Not authorized to access scope |
| 404    | Scope not found                |
| 413    | File too large (> 50MB)        |

#### Behavior

1. Validates user owns the scope
2. Validates file is PDF (extension + magic bytes)
3. Calculates SHA-256 checksum
4. **Deduplication**: If document with same checksum exists, reuses it
5. Creates `DocumentScope` link
6. Queues ingestion job (for new documents)

---

### Get Chat Documents

**Retrieve documents linked to a chat.**

```http
GET /api/chats/{chat_id}/documents?include_project={bool}
```

#### Path Parameters

| Parameter | Type   | Description    |
| --------- | ------ | -------------- |
| `chat_id` | string | ID of the chat |

#### Query Parameters

| Parameter         | Type    | Default | Description                     |
| ----------------- | ------- | ------- | ------------------------------- |
| `include_project` | boolean | `false` | Include project-level documents |

#### Response (200 OK)

```json
{
  "documents": [
    {
      "id": "doc_abc123",
      "filename": "chat_file.pdf",
      "size_bytes": 1048576,
      "status": "ready",
      "checksum": "sha256:...",
      "uploaded_at": "2025-12-10T01:00:00Z"
    }
  ],
  "project_documents": [
    {
      "id": "doc_xyz789",
      "filename": "project_file.pdf",
      "size_bytes": 2097152,
      "status": "ready",
      "uploaded_at": "2025-12-09T12:00:00Z"
    }
  ]
}
```

> Note: `project_documents` only included when `include_project=true` and chat has a `project_id`.

#### Error Responses

| Status | Description                   |
| ------ | ----------------------------- |
| 403    | Not authorized to access chat |
| 404    | Chat not found                |

---

### Get Project Documents

**Retrieve documents linked to a project.**

```http
GET /api/projects/{project_id}/documents
```

#### Path Parameters

| Parameter    | Type   | Description       |
| ------------ | ------ | ----------------- |
| `project_id` | string | ID of the project |

#### Response (200 OK)

```json
{
  "documents": [
    {
      "id": "doc_abc123",
      "filename": "project_file.pdf",
      "size_bytes": 1048576,
      "status": "ready",
      "uploaded_at": "2025-12-10T01:00:00Z"
    }
  ]
}
```

#### Error Responses

| Status | Description                      |
| ------ | -------------------------------- |
| 403    | Not authorized to access project |
| 404    | Project not found                |

---

### Delete Document

**Unlink or delete a document.**

```http
DELETE /api/documents/{document_id}?scope_type={type}&scope_id={id}
```

#### Path Parameters

| Parameter     | Type   | Description        |
| ------------- | ------ | ------------------ |
| `document_id` | string | ID of the document |

#### Query Parameters (Optional)

| Parameter    | Type   | Description                                      |
| ------------ | ------ | ------------------------------------------------ |
| `scope_type` | string | `chat` or `project` (unlink from specific scope) |
| `scope_id`   | string | ID of the scope to unlink from                   |

#### Behavior

**With scope params:** Unlinks document from the specified scope only.

**Without scope params:** Unlinks document from ALL of the user's scopes.

**Orphan cleanup:** If document has no remaining links after unlinking, it is:

1. Marked with `status: "deleting"`
2. S3 file is deleted
3. Chunks are deleted
4. Document record is deleted

#### Response (200 OK)

```json
{
  "status": "unlinked",
  "message": "Document unlinked from scope"
}
```

Or if fully deleted:

```json
{
  "status": "deleted",
  "message": "Document deleted completely"
}
```

#### Error Responses

| Status | Description                               |
| ------ | ----------------------------------------- |
| 403    | Not authorized to access scope            |
| 404    | Document not found or not linked to scope |

---

## Data Models

### Document

| Field         | Type     | Description                       |
| ------------- | -------- | --------------------------------- |
| `id`          | string   | Unique identifier (`doc_*`)       |
| `filename`    | string   | Original filename                 |
| `s3_key`      | string   | S3 object key                     |
| `checksum`    | string   | SHA-256 hash (`sha256:...`)       |
| `size_bytes`  | integer  | File size in bytes                |
| `status`      | string   | `pending`, `ready`, or `deleting` |
| `uploaded_at` | datetime | Upload timestamp (UTC)            |

### DocumentScope

| Field         | Type     | Description                |
| ------------- | -------- | -------------------------- |
| `id`          | string   | Unique identifier (`ds_*`) |
| `document_id` | string   | Reference to Document      |
| `scope_type`  | string   | `chat` or `project`        |
| `scope_id`    | string   | ID of the scope            |
| `linked_at`   | datetime | Link timestamp (UTC)       |

### Document Status

| Value      | Description                              |
| ---------- | ---------------------------------------- |
| `pending`  | Uploaded, ingestion in progress          |
| `ready`    | Fully ingested, searchable               |
| `deleting` | Marked for deletion, hidden from queries |

---

## Deduplication

Documents are deduplicated using SHA-256 checksums:

1. When uploading, checksum is calculated
2. If a document with the same checksum exists, it is reused
3. A new `DocumentScope` link is created pointing to the existing document
4. This saves storage and avoids re-ingesting identical files

---

## Security

- **Scope Ownership**: All operations validate user owns the target scope
- **File Validation**: PDF files only (extension + magic bytes check)
- **Size Limit**: Maximum 50MB per file
- **Path Sanitization**: Filenames are sanitized to prevent path traversal
