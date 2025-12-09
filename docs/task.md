# Migrate from Qdrant to MongoDB Atlas

## Tasks

- [x] Planning: Create migration plan
- [x] Create git branch for migration
- [ ] User provides MongoDB Atlas connection string
- [x] Replace `qdrant-client` with `pymongo` in dependencies
- [x] Rewrite `vector_db.py` to use MongoDB Atlas Vector Search
- [x] Update `main.py` if needed
- [x] Create `.env.example` template
- [x] User adds MongoDB connection string to `.env`
- [x] Test the PDF upload and query flow
- [ ] Clean up: Remove old Qdrant files

## Source-Based Filtering

- [x] Design efficient pre-filtering architecture
- [x] Update MongoDB vector search index with filter fields
- [x] Modify `vector_db.py` search to accept source filter
- [x] Update `main.py` to pass source_id to search
- [x] Update Streamlit to track current document source
- [x] Test filtering works correctly

## Document Upload Bugs & Multi-Doc Support

- [x] Plan: Fix upload bugs and add multi-document support
- [x] Decided on proper workspace/session architecture

## Workspace & Session Architecture

### Phase 1: Backend Data Model

- [/] Add `workspace_id` to documents on upsert
- [ ] Create `chat_sessions` collection
- [ ] Update vector search to filter by workspace_id

### Phase 2: API Endpoints

- [ ] `POST /workspaces` - create workspace
- [ ] `GET /workspaces/{id}/documents` - list docs
- [ ] `POST /sessions` - create chat session
- [ ] `GET /sessions/{id}/messages` - load history

### Phase 3: Streamlit UI

- [ ] Workspace selector (sidebar)
- [ ] Document list with upload
- [ ] "New Chat" button
- [ ] Session list/switcher
