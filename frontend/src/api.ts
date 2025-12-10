/**
 * API client for the enhanced RAG application.
 */
import type {
  Project,
  Chat,
  Document,
  Message,
  UploadResponse,
  ScopeType,
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
    credentials: "include", // Include cookies for auth
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

// --- Project API ---

export async function createProject(name: string): Promise<Project> {
  return fetchApi("/projects", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function listProjects(): Promise<Project[]> {
  return fetchApi("/projects");
}

export async function getProject(projectId: string): Promise<Project> {
  return fetchApi(`/projects/${projectId}`);
}

export async function deleteProject(projectId: string): Promise<void> {
  await fetchApi(`/projects/${projectId}`, { method: "DELETE" });
}

// --- Chat API ---

export async function createChat(
  projectId: string | null = null,
  title: string = "New Chat"
): Promise<Chat> {
  return fetchApi("/chats", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId, title }),
  });
}

export async function listChats(
  projectId?: string,
  standalone: boolean = false
): Promise<Chat[]> {
  let endpoint = "/chats";
  if (standalone) {
    endpoint += "?standalone=true";
  } else if (projectId) {
    endpoint += `?project_id=${projectId}`;
  }
  return fetchApi(endpoint);
}

export async function getChat(chatId: string): Promise<Chat> {
  return fetchApi(`/chats/${chatId}`);
}

export async function updateChat(
  chatId: string,
  updates: { title?: string; is_pinned?: boolean }
): Promise<Chat> {
  return fetchApi(`/chats/${chatId}`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export async function deleteChat(chatId: string): Promise<void> {
  await fetchApi(`/chats/${chatId}`, { method: "DELETE" });
}

// --- Document API ---

export async function listDocuments(
  scopeType: ScopeType,
  scopeId: string
): Promise<Document[]> {
  return fetchApi(`/documents?scope_type=${scopeType}&scope_id=${scopeId}`);
}

export async function getChatDocuments(
  chatId: string,
  includeProject: boolean = true
): Promise<Document[]> {
  return fetchApi(
    `/chats/${chatId}/documents?include_project=${includeProject}`
  );
}

export async function uploadDocument(
  scopeType: ScopeType,
  scopeId: string,
  file: File
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    `${API_BASE}/upload?scope_type=${scopeType}&scope_id=${scopeId}`,
    {
      method: "POST",
      body: formData,
    }
  );

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Upload failed" }));
    throw new Error(error.detail);
  }

  return response.json();
}

// --- Message API ---

export async function saveMessage(
  chatId: string,
  role: "user" | "assistant",
  content: string,
  sources: string[] = []
): Promise<Message> {
  return fetchApi("/messages", {
    method: "POST",
    body: JSON.stringify({ chat_id: chatId, role, content, sources }),
  });
}

export async function getMessages(chatId: string): Promise<Message[]> {
  return fetchApi(`/chats/${chatId}/messages`);
}

// --- Inngest Events ---

export async function sendIngestEvent(
  pdfPath: string,
  filename: string,
  scopeType: ScopeType,
  scopeId: string
): Promise<string[]> {
  const result = await fetchApi<{ event_ids: string[] }>("/events/ingest", {
    method: "POST",
    body: JSON.stringify({
      pdf_path: pdfPath,
      filename,
      scope_type: scopeType,
      scope_id: scopeId,
    }),
  });
  return result.event_ids;
}

export async function sendQueryEvent(
  question: string,
  chatId: string,
  scopeType: ScopeType,
  scopeId: string,
  topK: number = 5,
  history: Array<{ role: string; content: string }> = []
): Promise<string[]> {
  const result = await fetchApi<{ event_ids: string[] }>("/events/query", {
    method: "POST",
    body: JSON.stringify({
      question,
      chat_id: chatId,
      scope_type: scopeType,
      scope_id: scopeId,
      top_k: topK,
      history,
    }),
  });
  return result.event_ids;
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

// --- Auth API ---

import type {
  User,
  AuthResponse,
  Session,
  RegisterRequest,
  LoginRequest,
} from "./types";

export async function register(
  data: RegisterRequest
): Promise<{ message: string }> {
  return fetchApi("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function login(data: LoginRequest): Promise<AuthResponse> {
  return fetchApi("/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function logout(): Promise<{ message: string }> {
  return fetchApi("/auth/logout", { method: "POST" });
}

export async function logoutAll(): Promise<{ message: string }> {
  return fetchApi("/auth/logout-all", { method: "POST" });
}

export async function getCurrentUser(): Promise<{
  user: User;
  providers: string[];
}> {
  return fetchApi("/auth/me");
}

export async function updateProfile(data: {
  name?: string;
  avatar_url?: string;
}): Promise<{ user: User }> {
  return fetchApi("/auth/me", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function refreshTokens(): Promise<{ message: string }> {
  return fetchApi("/auth/refresh", { method: "POST" });
}

export async function forgotPassword(
  email: string
): Promise<{ message: string }> {
  return fetchApi("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function resetPassword(
  token: string,
  newPassword: string
): Promise<{ message: string }> {
  return fetchApi("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}

export async function changePassword(
  currentPassword: string,
  newPassword: string
): Promise<{ message: string }> {
  return fetchApi("/auth/password", {
    method: "PATCH",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}

export async function changeEmail(
  newEmail: string,
  password: string
): Promise<{ message: string }> {
  return fetchApi("/auth/email", {
    method: "PATCH",
    body: JSON.stringify({ new_email: newEmail, password }),
  });
}

export async function getSessions(): Promise<{ sessions: Session[] }> {
  return fetchApi("/auth/sessions");
}

export async function revokeSession(
  sessionId: string
): Promise<{ message: string }> {
  return fetchApi(`/auth/sessions/${sessionId}`, { method: "DELETE" });
}

export async function deleteAccount(
  password: string
): Promise<{ message: string }> {
  return fetchApi(`/auth/account?password=${encodeURIComponent(password)}`, {
    method: "DELETE",
  });
}
