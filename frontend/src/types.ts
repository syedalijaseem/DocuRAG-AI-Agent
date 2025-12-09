/**
 * TypeScript types for the RAG application.
 */

export interface Workspace {
  id: string;
  name: string;
  created_at: string;
}

export interface Document {
  source: string;
  chunks: number;
}

export interface ChatSession {
  id: string;
  workspace_id: string;
  title: string;
  created_at: string;
}

export interface Message {
  id: string;
  session_id: string;
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
  filename: string;
  path: string;
  workspace_id: string;
  status: string;
}
