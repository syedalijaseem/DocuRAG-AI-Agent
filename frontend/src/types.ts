/**
 * TypeScript types for the enhanced RAG application.
 */

// Scope types for document ownership
export type ScopeType = "chat" | "project";

export interface Project {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface Chat {
  id: string;
  project_id: string | null; // null = standalone chat
  title: string;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
}

// Document type matching backend M1 model
export interface Document {
  id: string;
  filename: string;
  s3_key: string;
  checksum: string;
  size_bytes: number;
  status: "pending" | "ready" | "failed";
  uploaded_at: string;
}

// Upload response from backend
export interface UploadResponse {
  document: Document;
  s3_url?: string; // Optional - not present when linked
  status: "uploaded" | "linked";
  message?: string;
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

// --- Auth Types ---

export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  email_verified: boolean;
  created_at: string;
  last_login: string | null;
}

export interface AuthResponse {
  user: User;
  is_new: boolean;
}

export interface Session {
  id: string;
  device_info: string | null;
  created_at: string;
  expires_at: string;
  is_current: boolean;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}
