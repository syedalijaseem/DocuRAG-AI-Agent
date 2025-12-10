# M3: Query Integration - Requirements Specification

## Overview

M3 adds project-inherited search functionality, enabling chat queries to include documents uploaded to the parent project.

**Duration:** 1 day  
**Dependencies:** M2 (Ingestion Pipeline) - Complete ✅

---

## Functional Requirements

### FR-1: Project-Inherited Search

**Description:** When querying a chat that belongs to a project, search results include documents from both the chat and the project.

**Implementation:**

- Look up chat's `project_id` before search
- Pass `include_project=True` and `project_id` to `search_for_scope()`

**Acceptance Criteria:**

- [x] Chat query includes project documents when chat has project_id
- [x] Chat query excludes project documents when chat has no project
- [x] Project query searches only project documents

---

### FR-2: Scope Isolation Preserved

**Description:** Queries still respect scope boundaries - chat A cannot see chat B's documents.

**Acceptance Criteria:**

- [x] Cross-chat document access prevented
- [x] Only linked scopes are searched

---

## Non-Functional Requirements

### NFR-1: Query Performance

**Category:** Speed

**Target:** Query response < 20 seconds (p95)

---

### NFR-2: Backward Compatibility

**Category:** Reliability

**Description:** Chats without projects work unchanged.

---

## Acceptance Tests

| ID    | Test                 | Pass Criteria         |
| ----- | -------------------- | --------------------- |
| M3-T1 | Chat with project    | Includes project docs |
| M3-T2 | Chat without project | Only chat docs        |
| M3-T3 | Project scope        | Only project docs     |
| M3-T4 | Cross-chat isolation | Forbidden             |
