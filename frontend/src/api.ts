/**
 * API client for communicating with the FastAPI backend.
 */
import type {
  Workspace,
  Document,
  ChatSession,
  Message,
  UploadResponse,
} from "./types";

const API_BASE = "http://localhost:8000/api";

/**
 * Generic fetch wrapper with error handling.
 */
async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// --- Workspace API ---

export async function createWorkspace(name: string): Promise<Workspace> {
  return fetchApi("/workspaces", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function listWorkspaces(): Promise<Workspace[]> {
  return fetchApi("/workspaces");
}

export async function getWorkspace(workspaceId: string): Promise<Workspace> {
  return fetchApi(`/workspaces/${workspaceId}`);
}

// --- Document API ---

export async function listDocuments(workspaceId: string): Promise<Document[]> {
  return fetchApi(`/workspaces/${workspaceId}/documents`);
}

export async function uploadDocument(
  workspaceId: string,
  file: File
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/workspaces/${workspaceId}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Upload failed" }));
    throw new Error(error.detail);
  }

  return response.json();
}

// --- Session API ---

export async function createSession(
  workspaceId: string,
  title: string = "New Chat"
): Promise<ChatSession> {
  return fetchApi("/sessions", {
    method: "POST",
    body: JSON.stringify({ workspace_id: workspaceId, title }),
  });
}

export async function listSessions(
  workspaceId: string
): Promise<ChatSession[]> {
  return fetchApi(`/workspaces/${workspaceId}/sessions`);
}

export async function getSession(
  sessionId: string
): Promise<ChatSession & { messages: Message[] }> {
  return fetchApi(`/sessions/${sessionId}`);
}

export async function deleteSession(sessionId: string): Promise<void> {
  await fetchApi(`/sessions/${sessionId}`, { method: "DELETE" });
}

// --- Message API ---

export async function saveMessage(
  sessionId: string,
  role: "user" | "assistant",
  content: string,
  sources: string[] = []
): Promise<Message> {
  return fetchApi("/messages", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, role, content, sources }),
  });
}

export async function getMessages(sessionId: string): Promise<Message[]> {
  return fetchApi(`/sessions/${sessionId}/messages`);
}

// --- Inngest Events (via Inngest API) ---

const INNGEST_API = "http://localhost:8288/e";

export async function sendIngestEvent(
  pdfPath: string,
  sourceId: string,
  workspaceId: string
): Promise<string> {
  const response = await fetch(INNGEST_API, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: "rag/ingest_pdf",
      data: {
        pdf_path: pdfPath,
        source_id: sourceId,
        workspace_id: workspaceId,
      },
    }),
  });
  const result = await response.json();
  return result.ids?.[0] || "";
}

export async function sendQueryEvent(
  question: string,
  workspaceId: string,
  topK: number = 5,
  history: Array<{ role: string; content: string }> = []
): Promise<string> {
  const response = await fetch(INNGEST_API, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: "rag/query_pdf_ai",
      data: { question, workspace_id: workspaceId, top_k: topK, history },
    }),
  });
  const result = await response.json();
  return result.ids?.[0] || "";
}

// --- Inngest Run Polling ---

const INNGEST_RUNS_API = "http://localhost:8288/v1";

export async function waitForRunOutput(
  eventId: string,
  timeoutMs: number = 120000
): Promise<Record<string, unknown>> {
  const startTime = Date.now();
  const pollInterval = 500;

  while (Date.now() - startTime < timeoutMs) {
    const response = await fetch(`${INNGEST_RUNS_API}/events/${eventId}/runs`);
    const data = await response.json();
    const runs = data.data || [];

    if (runs.length > 0) {
      const run = runs[0];
      const status = run.status;

      if (["Completed", "Succeeded", "Success", "Finished"].includes(status)) {
        return run.output || {};
      }
      if (["Failed", "Cancelled"].includes(status)) {
        throw new Error(`Run ${status}`);
      }
    }

    await new Promise((resolve) => setTimeout(resolve, pollInterval));
  }

  throw new Error("Timeout waiting for run output");
}
