import { useState, useEffect, useRef } from "react";
import type { Workspace, ChatSession, Message, Document } from "./types";
import * as api from "./api";
import "./App.css";

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
  const messagesEndRef = useRef<HTMLDivElement>(null);

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

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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

      // Trigger ingestion via Inngest
      const eventId = await api.sendIngestEvent(
        result.path,
        result.filename,
        workspace.id
      );

      // Wait for ingestion
      await api.waitForRunOutput(eventId);

      // Reload documents
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
      // Save user message
      await api.saveMessage(currentSession.id, "user", userMessage);

      // Build history from messages
      const history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      // Send query via Inngest
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

      // Save assistant message
      await api.saveMessage(currentSession.id, "assistant", answer, sources);

      // Reload messages
      await loadMessages();
    } catch (error) {
      console.error("Query failed:", error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>📚 DocuRAG</h1>
        </div>

        <button className="new-chat-btn" onClick={handleNewChat}>
          + New Chat
        </button>

        {/* Documents Section */}
        <div className="sidebar-section">
          <h3>📄 Documents</h3>
          <label className="upload-btn">
            {uploading ? "Uploading..." : "+ Upload PDF"}
            <input
              type="file"
              accept=".pdf"
              onChange={handleUpload}
              disabled={uploading}
              hidden
            />
          </label>
          <ul className="doc-list">
            {documents.map((doc) => (
              <li key={doc.source} className="doc-item">
                {doc.source} ({doc.chunks} chunks)
              </li>
            ))}
          </ul>
        </div>

        {/* Sessions Section */}
        <div className="sidebar-section">
          <h3>💬 Chats</h3>
          <ul className="session-list">
            {sessions.map((session) => (
              <li
                key={session.id}
                className={`session-item ${
                  currentSession?.id === session.id ? "active" : ""
                }`}
                onClick={() => handleSelectSession(session)}
              >
                <span className="session-title">{session.title}</span>
                <button
                  className="delete-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteSession(session.id);
                  }}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="chat-area">
        {currentSession ? (
          <>
            <div className="messages">
              {messages.map((msg) => (
                <div key={msg.id} className={`message ${msg.role}`}>
                  <div className="message-content">{msg.content}</div>
                  {msg.sources.length > 0 && (
                    <div className="message-sources">
                      <details>
                        <summary>📚 Sources ({msg.sources.length})</summary>
                        <ul>
                          {msg.sources.map((src, i) => (
                            <li key={i}>{src}</li>
                          ))}
                        </ul>
                      </details>
                    </div>
                  )}
                </div>
              ))}
              {loading && (
                <div className="message assistant">
                  <div className="message-content loading">Thinking...</div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="input-area">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
                placeholder="Ask a question about your documents..."
                disabled={loading || documents.length === 0}
              />
              <button
                onClick={handleSendMessage}
                disabled={loading || !input.trim()}
              >
                Send
              </button>
            </div>
          </>
        ) : (
          <div className="no-session">
            <h2>Welcome to DocuRAG</h2>
            <p>Upload PDFs and ask questions about them.</p>
            {documents.length === 0 ? (
              <p>👈 Start by uploading a PDF in the sidebar</p>
            ) : (
              <button onClick={handleNewChat} className="start-chat-btn">
                Start a new chat
              </button>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
