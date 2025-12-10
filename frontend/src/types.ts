/**
 * TypeScript types for the enhanced RAG application.
 */

// Scope types for document ownership
export type ScopeType = "chat" | "project";

export interface Project {
  id: string;
  name: string;
  created_at: string;
}

export interface Chat {
  id: string;
  project_id: string | null; // null = standalone chat
  title: string;
  is_pinned: boolean;
  created_at: string;
}

export interface Document {
  id: string;
  filename: string;
  s3_key: string;
  scope_type: ScopeType;
  scope_id: string;
  chunk_count: number;
  uploaded_at: string;
}

export interface Message {
  id: string;
  chat_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  sources: string[];
}

export interface QueryResponse {
  answer: string;
  sources: string[];
  num_contexts: number;
  history: Array<{ role: string; content: string }>;
  avg_confidence: number;
}

export interface UploadResponse {
  document: Document;
  s3_url: string;
  status: string;
}

// Legacy types (for backward compatibility)
export interface Workspace {
  id: string;
  name: string;
  created_at: string;
}

export interface ChatSession {
  id: string;
  workspace_id: string;
  title: string;
  created_at: string;
}
