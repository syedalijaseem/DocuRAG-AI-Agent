/**
 * Sidebar component with projects and chats.
 */
import type { Project, Chat, Document, User } from "../types";

interface SidebarProps {
  projects: Project[];
  standaloneChats: Chat[];
  projectChats: Chat[];
  documents: Document[];
  currentChatId: string | null;
  currentProjectId: string | null;
  uploading: boolean;
  user: User | null;
  onNewChat: () => void;
  onNewProject: () => void;
  onSelectChat: (chat: Chat) => void;
  onSelectProject: (project: Project) => void;
  onDeleteChat: (chatId: string) => void;
  onPinChat: (chatId: string, isPinned: boolean) => void;
  onUpload: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onLogout: () => void;
  onSettings: () => void;
}

export function Sidebar({
  projects,
  standaloneChats,
  projectChats,
  documents,
  currentChatId,
  currentProjectId,
  uploading,
  user,
  onNewChat,
  onNewProject,
  onSelectChat,
  onSelectProject,
  onDeleteChat,
  onPinChat,
  onUpload,
  onLogout,
  onSettings,
}: SidebarProps) {
  // Separate pinned and unpinned chats
  const pinnedChats = standaloneChats.filter((c) => c.is_pinned);
  const unpinnedChats = standaloneChats.filter((c) => !c.is_pinned);

  return (
    <aside className="w-72 bg-zinc-900 border-r border-zinc-800 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-5 border-b border-zinc-800">
        <h1 className="text-xl font-semibold">📚 DocuRAG</h1>
      </div>

      {/* New Chat Button */}
      <button
        onClick={onNewChat}
        className="mx-4 my-3 px-4 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors"
      >
        + New Chat
      </button>

      {/* Projects Section */}
      <div className="p-4 border-b border-zinc-800">
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
            📁 Projects
          </h3>
          <button
            onClick={onNewProject}
            className="text-xs text-indigo-400 hover:text-indigo-300"
          >
            + New
          </button>
        </div>
        <ul className="space-y-1">
          {projects.map((project) => (
            <li
              key={project.id}
              onClick={() => onSelectProject(project)}
              className={`
                group flex justify-between items-center px-3 py-2 rounded-lg cursor-pointer transition-colors
                ${
                  currentProjectId === project.id
                    ? "bg-zinc-800 border-l-2 border-indigo-500"
                    : "hover:bg-zinc-800/50"
                }
              `}
            >
              <span className="text-sm truncate">{project.name}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Documents Section (context-aware) */}
      <div className="p-4 border-b border-zinc-800">
        <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">
          📄 Documents
        </h3>
        <label className="block p-3 bg-zinc-800/50 border border-dashed border-zinc-700 rounded-md text-sm text-zinc-400 cursor-pointer text-center hover:border-indigo-500 hover:text-indigo-400 transition-colors">
          {uploading ? "Uploading..." : "+ Upload PDF"}
          <input
            type="file"
            accept=".pdf"
            onChange={onUpload}
            disabled={uploading}
            className="hidden"
          />
        </label>
        <ul className="mt-2 space-y-1 max-h-24 overflow-y-auto">
          {documents.map((doc, index) => {
            // Fallback for documents without filename
            const displayName =
              doc.filename ||
              (doc.s3_key
                ? doc.s3_key.split("/").pop()
                : `Document ${index + 1}`);
            return (
              <li
                key={doc.id || `doc-${index}`}
                className="px-2 py-1.5 text-sm text-zinc-400 rounded flex items-center"
              >
                <span
                  className={`w-2 h-2 rounded-full mr-2 flex-shrink-0 ${
                    doc.scope_type === "project"
                      ? "bg-blue-500"
                      : "bg-green-500"
                  }`}
                ></span>
                <span className="truncate flex-1" title={displayName}>
                  {displayName}
                </span>
              </li>
            );
          })}
        </ul>
      </div>

      {/* Chats Section */}
      <div className="flex-1 p-4 overflow-y-auto">
        <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">
          💬 Chats
        </h3>

        {/* Pinned Chats */}
        {pinnedChats.length > 0 && (
          <div className="mb-3">
            <div className="text-xs text-zinc-600 mb-1">📌 Pinned</div>
            <ul className="space-y-1">
              {pinnedChats.map((chat) => (
                <ChatItem
                  key={chat.id}
                  chat={chat}
                  isActive={currentChatId === chat.id}
                  onSelect={() => onSelectChat(chat)}
                  onDelete={() => onDeleteChat(chat.id)}
                  onPin={() => onPinChat(chat.id, false)}
                />
              ))}
            </ul>
          </div>
        )}

        {/* Project Chats (if project selected) */}
        {currentProjectId && projectChats.length > 0 && (
          <div className="mb-3">
            <div className="text-xs text-zinc-600 mb-1">Project Chats</div>
            <ul className="space-y-1">
              {projectChats.map((chat) => (
                <ChatItem
                  key={chat.id}
                  chat={chat}
                  isActive={currentChatId === chat.id}
                  onSelect={() => onSelectChat(chat)}
                  onDelete={() => onDeleteChat(chat.id)}
                  onPin={() => onPinChat(chat.id, !chat.is_pinned)}
                />
              ))}
            </ul>
          </div>
        )}

        {/* Unpinned Standalone Chats */}
        <ul className="space-y-1">
          {unpinnedChats.map((chat) => (
            <ChatItem
              key={chat.id}
              chat={chat}
              isActive={currentChatId === chat.id}
              onSelect={() => onSelectChat(chat)}
              onDelete={() => onDeleteChat(chat.id)}
              onPin={() => onPinChat(chat.id, true)}
            />
          ))}
        </ul>
      </div>

      {/* User Section */}
      {user && (
        <div className="p-4 border-t border-zinc-800 mt-auto">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-orange-500 to-pink-500 flex items-center justify-center text-white text-sm font-medium">
              {user.name?.charAt(0).toUpperCase() ||
                user.email.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {user.name || "User"}
              </p>
              <p className="text-xs text-zinc-500 truncate">{user.email}</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={onSettings}
              className="flex-1 px-3 py-1.5 text-xs text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors"
            >
              ⚙️ Settings
            </button>
            <button
              onClick={onLogout}
              className="flex-1 px-3 py-1.5 text-xs text-zinc-400 hover:text-red-400 hover:bg-zinc-800 rounded-lg transition-colors"
            >
              🚪 Logout
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}

interface ChatItemProps {
  chat: Chat;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onPin: () => void;
}

function ChatItem({
  chat,
  isActive,
  onSelect,
  onDelete,
  onPin,
}: ChatItemProps) {
  return (
    <li
      onClick={onSelect}
      className={`
        group flex justify-between items-center px-3 py-2.5 rounded-lg cursor-pointer transition-colors
        ${
          isActive
            ? "bg-zinc-800 border-l-2 border-indigo-500"
            : "hover:bg-zinc-800/50"
        }
      `}
    >
      <span className="text-sm truncate flex-1">{chat.title}</span>
      <div className="flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onPin();
          }}
          className="text-zinc-500 hover:text-yellow-400 text-sm px-1"
          title={chat.is_pinned ? "Unpin" : "Pin"}
        >
          {chat.is_pinned ? "📌" : "📍"}
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="text-zinc-500 hover:text-red-400 text-lg px-1"
        >
          ×
        </button>
      </div>
    </li>
  );
}
