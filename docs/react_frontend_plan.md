# React Frontend Migration

Migrate from Streamlit to React + TypeScript + Vite with chat session persistence.

## User Review Required

> [!IMPORTANT]
> This is a significant architecture change. The Streamlit app will remain as a fallback until React is complete.

## Proposed Changes

### Backend (FastAPI)

#### [NEW] [api_routes.py](file:///home/syedalijaseem/Projects/DocuRAG-AI-Agent/api_routes.py)

REST API endpoints for React frontend:

- `POST/GET /api/workspaces` - workspace management
- `GET /api/workspaces/{id}/documents` - list documents
- `POST/GET/DELETE /api/sessions` - chat session CRUD
- `POST/GET /api/messages` - message persistence
- `POST /api/workspaces/{id}/upload` - file upload

#### [MODIFY] [main.py](file:///home/syedalijaseem/Projects/DocuRAG-AI-Agent/main.py)

- Add CORS for React dev server (port 5173)
- Include API router

---

### Frontend (React + Vite)

#### [NEW] frontend/src/types.ts

TypeScript interfaces matching Pydantic models

#### [NEW] frontend/src/api.ts

API client with fetch helpers for all endpoints

#### [NEW] frontend/src/App.tsx

Main app with:

- Sidebar: workspace selector, document list, session list
- Main area: chat interface with message history

#### [NEW] frontend/src/components/

- `Sidebar.tsx` - workspace/session navigation
- `ChatArea.tsx` - message display and input
- `FileUpload.tsx` - PDF upload component

---

### MongoDB Collections

New collections for persistence:

- `workspaces` - workspace metadata
- `chat_sessions` - session metadata
- `messages` - chat message history

## Verification Plan

### Manual Testing

1. Start FastAPI: `uv run uvicorn main:app --reload`
2. Start React: `cd frontend && npm run dev`
3. Test: Create workspace → Upload PDF → Chat → New Chat → Switch sessions
