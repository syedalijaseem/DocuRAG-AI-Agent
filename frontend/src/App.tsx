import { useState, useEffect } from "react";
import type { Workspace, ChatSession, Message, Document } from "./types";
import * as api from "./api";
import { Sidebar } from "./components/Sidebar";
import { ChatArea } from "./components/ChatArea";
import "./index.css";

function App() {
  // State
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(
    null
  );
  const [messages, setMessages] = useState<Message[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  // Initialize workspace on mount
  useEffect(() => {
    initWorkspace();
  }, []);

  // Load sessions when workspace changes
  useEffect(() => {
    if (workspace) {
      loadSessions();
      loadDocuments();
    }
  }, [workspace]);

  // Load messages when session changes
  useEffect(() => {
    if (currentSession) {
      loadMessages();
    }
  }, [currentSession]);

  async function initWorkspace() {
    try {
      const workspaces = await api.listWorkspaces();
      if (workspaces.length > 0) {
        setWorkspace(workspaces[0]);
      } else {
        const newWorkspace = await api.createWorkspace("My Workspace");
        setWorkspace(newWorkspace);
      }
    } catch (error) {
      console.error("Failed to init workspace:", error);
    }
  }

  async function loadSessions() {
    if (!workspace) return;
    try {
      const sessionList = await api.listSessions(workspace.id);
      setSessions(sessionList);
    } catch (error) {
      console.error("Failed to load sessions:", error);
    }
  }

  async function loadDocuments() {
    if (!workspace) return;
    try {
      const docs = await api.listDocuments(workspace.id);
      setDocuments(docs);
    } catch (error) {
      console.error("Failed to load documents:", error);
    }
  }

  async function loadMessages() {
    if (!currentSession) return;
    try {
      const msgs = await api.getMessages(currentSession.id);
      setMessages(msgs);
    } catch (error) {
      console.error("Failed to load messages:", error);
    }
  }

  async function handleNewChat() {
    if (!workspace) return;
    try {
      const session = await api.createSession(workspace.id);
      setSessions([session, ...sessions]);
      setCurrentSession(session);
      setMessages([]);
    } catch (error) {
      console.error("Failed to create session:", error);
    }
  }

  async function handleSelectSession(session: ChatSession) {
    setCurrentSession(session);
  }

  async function handleDeleteSession(sessionId: string) {
    try {
      await api.deleteSession(sessionId);
      setSessions(sessions.filter((s) => s.id !== sessionId));
      if (currentSession?.id === sessionId) {
        setCurrentSession(null);
        setMessages([]);
      }
    } catch (error) {
      console.error("Failed to delete session:", error);
    }
  }

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !workspace) return;

    setUploading(true);
    try {
      const result = await api.uploadDocument(workspace.id, file);
      const eventId = await api.sendIngestEvent(
        result.path,
        result.filename,
        workspace.id
      );
      await api.waitForRunOutput(eventId);
      await loadDocuments();
    } catch (error) {
      console.error("Upload failed:", error);
    } finally {
      setUploading(false);
    }
  }

  async function handleSendMessage() {
    if (!input.trim() || !workspace || !currentSession) return;

    const userMessage = input.trim();
    setInput("");
    setLoading(true);

    // Add user message immediately
    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      session_id: currentSession.id,
      role: "user",
      content: userMessage,
      timestamp: new Date().toISOString(),
      sources: [],
    };
    setMessages([...messages, tempUserMsg]);

    try {
      await api.saveMessage(currentSession.id, "user", userMessage);
      const history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));
      const eventId = await api.sendQueryEvent(
        userMessage,
        workspace.id,
        5,
        history
      );
      const result = await api.waitForRunOutput(eventId);

      const answer =
        (result as { answer?: string }).answer || "No answer received";
      const sources = (result as { sources?: string[] }).sources || [];

      await api.saveMessage(currentSession.id, "assistant", answer, sources);
      await loadMessages();
      await loadSessions(); // Reload to get updated title
    } catch (error) {
      console.error("Query failed:", error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-screen bg-zinc-950 text-white">
      <Sidebar
        documents={documents}
        sessions={sessions}
        currentSessionId={currentSession?.id || null}
        uploading={uploading}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
        onUpload={handleUpload}
      />
      <ChatArea
        messages={messages}
        loading={loading}
        hasDocuments={documents.length > 0}
        hasSession={!!currentSession}
        input={input}
        onInputChange={setInput}
        onSendMessage={handleSendMessage}
        onStartChat={handleNewChat}
      />
    </div>
  );
}

export default App;
