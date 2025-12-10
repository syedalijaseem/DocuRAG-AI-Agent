import { useState, useEffect } from "react";
import type { Project, Chat, Message, Document, ScopeType } from "./types";
import * as api from "./api";
import { Sidebar } from "./components/Sidebar";
import { ChatArea } from "./components/ChatArea";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { SettingsPage } from "./pages/SettingsPage";
import { VerifyEmailPage } from "./pages/VerifyEmailPage";
import "./index.css";

// Auth view states
type AuthView = "login" | "register" | "settings" | null;

// Get verification token from URL
function getVerifyToken(): string | null {
  const params = new URLSearchParams(window.location.search);
  if (window.location.pathname === "/verify-email") {
    return params.get("token");
  }
  return null;
}

function AppContent() {
  const { user, loading: authLoading, logout } = useAuth();
  const [authView, setAuthView] = useState<AuthView>(null);
  const [verifyToken, setVerifyToken] = useState<string | null>(getVerifyToken);

  // State
  const [projects, setProjects] = useState<Project[]>([]);
  const [standaloneChats, setStandaloneChats] = useState<Chat[]>([]);
  const [projectChats, setProjectChats] = useState<Chat[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [currentChat, setCurrentChat] = useState<Chat | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [input, setInput] = useState("");
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  // Initialize on mount
  useEffect(() => {
    loadProjects();
    loadStandaloneChats();
  }, []);

  // Load project chats when project changes
  useEffect(() => {
    if (currentProject) {
      loadProjectChats(currentProject.id);
    } else {
      setProjectChats([]);
    }
  }, [currentProject]);

  // Load messages and documents when chat changes
  useEffect(() => {
    if (currentChat) {
      loadMessages();
      loadDocuments();
    }
  }, [currentChat]);

  async function loadProjects() {
    try {
      const projectList = await api.listProjects();
      setProjects(projectList);
    } catch (error) {
      console.error("Failed to load projects:", error);
    }
  }

  async function loadStandaloneChats() {
    try {
      const chats = await api.listChats(undefined, true);
      setStandaloneChats(chats);
    } catch (error) {
      console.error("Failed to load chats:", error);
    }
  }

  async function loadProjectChats(projectId: string) {
    try {
      const chats = await api.listChats(projectId);
      setProjectChats(chats);
    } catch (error) {
      console.error("Failed to load project chats:", error);
    }
  }

  async function loadDocuments() {
    if (!currentChat) return;
    try {
      const docs = await api.getChatDocuments(currentChat.id);
      setDocuments(docs);
    } catch (error) {
      console.error("Failed to load documents:", error);
    }
  }

  async function loadMessages() {
    if (!currentChat) return;
    try {
      const msgs = await api.getMessages(currentChat.id);
      setMessages(msgs);
    } catch (error) {
      console.error("Failed to load messages:", error);
    }
  }

  // Determine current scope
  function getCurrentScope(): { type: ScopeType; id: string } {
    if (currentChat?.project_id) {
      return { type: "project", id: currentChat.project_id };
    }
    if (currentChat) {
      return { type: "chat", id: currentChat.id };
    }
    if (currentProject) {
      return { type: "project", id: currentProject.id };
    }
    return { type: "chat", id: "" };
  }

  async function handleNewChat() {
    try {
      const chat = await api.createChat(currentProject?.id || null);
      if (currentProject) {
        setProjectChats([chat, ...projectChats]);
      } else {
        setStandaloneChats([chat, ...standaloneChats]);
      }
      setCurrentChat(chat);
      setMessages([]);
    } catch (error) {
      console.error("Failed to create chat:", error);
    }
  }

  async function handleNewProject() {
    const name = prompt("Project name:");
    if (!name) return;
    try {
      const project = await api.createProject(name);
      setProjects([project, ...projects]);
      setCurrentProject(project);
    } catch (error) {
      console.error("Failed to create project:", error);
    }
  }

  function handleSelectChat(chat: Chat) {
    setCurrentChat(chat);
    if (chat.project_id) {
      const project = projects.find((p) => p.id === chat.project_id);
      if (project) setCurrentProject(project);
    }
  }

  function handleSelectProject(project: Project) {
    setCurrentProject(project);
    setCurrentChat(null);
    setMessages([]);
    setDocuments([]);
  }

  async function handleDeleteChat(chatId: string) {
    try {
      await api.deleteChat(chatId);
      setStandaloneChats(standaloneChats.filter((c) => c.id !== chatId));
      setProjectChats(projectChats.filter((c) => c.id !== chatId));
      if (currentChat?.id === chatId) {
        setCurrentChat(null);
        setMessages([]);
      }
    } catch (error) {
      console.error("Failed to delete chat:", error);
    }
  }

  async function handlePinChat(chatId: string, isPinned: boolean) {
    try {
      const updated = await api.updateChat(chatId, { is_pinned: isPinned });
      setStandaloneChats(
        standaloneChats.map((c) => (c.id === chatId ? updated : c))
      );
      setProjectChats(projectChats.map((c) => (c.id === chatId ? updated : c)));
    } catch (error) {
      console.error("Failed to pin chat:", error);
    }
  }

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    const scope = getCurrentScope();
    if (!scope.id) {
      alert("Please select or create a chat first.");
      return;
    }

    setUploading(true);
    try {
      const result = await api.uploadDocument(scope.type, scope.id, file);

      const eventIds = await api.sendIngestEvent(
        result.document.s3_key,
        result.document.filename,
        scope.type,
        scope.id
      );

      if (eventIds.length > 0) {
        await api.waitForRunOutput(eventIds[0]);
      }

      await loadDocuments();
    } catch (error) {
      console.error("Upload failed:", error);
      alert(
        `Upload failed: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function handleSendMessage() {
    if (!input.trim() || !currentChat) return;

    const scope = getCurrentScope();
    const userMessage = input.trim();
    setInput("");
    setLoading(true);

    // Add user message immediately
    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      chat_id: currentChat.id,
      role: "user",
      content: userMessage,
      timestamp: new Date().toISOString(),
      sources: [],
    };
    setMessages([...messages, tempUserMsg]);

    try {
      await api.saveMessage(currentChat.id, "user", userMessage);
      const history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const eventIds = await api.sendQueryEvent(
        userMessage,
        currentChat.id,
        scope.type,
        scope.id,
        topK,
        history
      );

      if (eventIds.length === 0) {
        throw new Error("No event ID returned");
      }

      const result = await api.waitForRunOutput(eventIds[0]);

      const answer =
        (result as { answer?: string }).answer || "No answer received";
      const sources = (result as { sources?: string[] }).sources || [];

      await api.saveMessage(currentChat.id, "assistant", answer, sources);
      await loadMessages();
      await loadStandaloneChats();
      if (currentProject) {
        await loadProjectChats(currentProject.id);
      }
    } catch (error) {
      console.error("Query failed:", error);
    } finally {
      setLoading(false);
    }
  }

  // Show loading spinner during auth check
  if (authLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-zinc-950">
        <div className="text-white">Loading...</div>
      </div>
    );
  }

  // Handle email verification from link
  if (verifyToken) {
    const handleVerifyComplete = () => {
      setVerifyToken(null);
      window.history.replaceState({}, "", "/");
      setAuthView("login");
    };
    return (
      <VerifyEmailPage
        token={verifyToken}
        onSuccess={handleVerifyComplete}
        onError={handleVerifyComplete}
      />
    );
  }

  // Show login/register if not authenticated
  if (!user) {
    if (authView === "register") {
      return (
        <RegisterPage
          onSwitchToLogin={() => setAuthView("login")}
          onSuccess={() => setAuthView("login")}
        />
      );
    }
    return (
      <LoginPage
        onSwitchToRegister={() => setAuthView("register")}
        onForgotPassword={() =>
          alert("Password reset: Check console for token")
        }
        onSuccess={() => setAuthView(null)}
      />
    );
  }

  // Show settings modal if open
  if (authView === "settings") {
    return (
      <div className="flex h-screen bg-zinc-950">
        <SettingsPage onClose={() => setAuthView(null)} />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-zinc-950 text-white">
      <Sidebar
        projects={projects}
        standaloneChats={standaloneChats}
        projectChats={projectChats}
        documents={documents}
        currentChatId={currentChat?.id || null}
        currentProjectId={currentProject?.id || null}
        uploading={uploading}
        user={user}
        onNewChat={handleNewChat}
        onNewProject={handleNewProject}
        onSelectChat={handleSelectChat}
        onSelectProject={handleSelectProject}
        onDeleteChat={handleDeleteChat}
        onPinChat={handlePinChat}
        onUpload={handleUpload}
        onLogout={logout}
        onSettings={() => setAuthView("settings")}
      />
      <ChatArea
        messages={messages}
        loading={loading}
        hasDocuments={documents.length > 0}
        hasChat={!!currentChat}
        input={input}
        topK={topK}
        onInputChange={setInput}
        onTopKChange={setTopK}
        onSendMessage={handleSendMessage}
        onStartChat={handleNewChat}
      />
    </div>
  );
}

// Main App wrapper with Theme and Auth providers
function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
