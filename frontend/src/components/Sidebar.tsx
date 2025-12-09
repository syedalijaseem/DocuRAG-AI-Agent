/**
 * Sidebar component with workspace documents and chat sessions.
 */
import type { ChatSession, Document } from "../types";

interface SidebarProps {
  documents: Document[];
  sessions: ChatSession[];
  currentSessionId: string | null;
  uploading: boolean;
  onNewChat: () => void;
  onSelectSession: (session: ChatSession) => void;
  onDeleteSession: (sessionId: string) => void;
  onUpload: (event: React.ChangeEvent<HTMLInputElement>) => void;
}

export function Sidebar({
  documents,
  sessions,
  currentSessionId,
  uploading,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onUpload,
}: SidebarProps) {
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

      {/* Documents Section */}
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
        <ul className="mt-2 space-y-1">
          {documents.map((doc) => (
            <li
              key={doc.source}
              className="px-2 py-1.5 text-sm text-zinc-400 rounded"
            >
              {doc.source} <span className="text-zinc-600">({doc.chunks})</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Sessions Section */}
      <div className="flex-1 p-4 overflow-y-auto">
        <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">
          💬 Chats
        </h3>
        <ul className="space-y-1">
          {sessions.map((session) => (
            <li
              key={session.id}
              onClick={() => onSelectSession(session)}
              className={`
                group flex justify-between items-center px-3 py-2.5 rounded-lg cursor-pointer transition-colors
                ${
                  currentSessionId === session.id
                    ? "bg-zinc-800 border-l-3 border-indigo-500"
                    : "hover:bg-zinc-800/50"
                }
              `}
            >
              <span className="text-sm truncate flex-1">{session.title}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteSession(session.id);
                }}
                className="opacity-0 group-hover:opacity-100 text-zinc-500 hover:text-red-400 text-lg px-1 transition-opacity"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
