/**
 * Chats Page - List of all chats.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  useStandaloneChats,
  useCreateChat,
  useDeleteChat,
  useUpdateChat,
} from "../hooks/useChats";

export function ChatsPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");

  const { data: chats = [], isLoading } = useStandaloneChats();
  const createChat = useCreateChat();
  const deleteChat = useDeleteChat();
  const updateChat = useUpdateChat();

  const filteredChats = chats.filter((chat) =>
    chat.title.toLowerCase().includes(search.toLowerCase())
  );

  async function handleNewChat() {
    try {
      const newChat = await createChat.mutateAsync({ title: "New Chat" });
      navigate(`/chat/${newChat.id}`);
    } catch (error) {
      console.error("Failed to create chat:", error);
    }
  }

  async function handleDeleteChat(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (confirm("Delete this chat?")) {
      deleteChat.mutate(id);
    }
  }

  async function handlePinChat(
    id: string,
    isPinned: boolean,
    e: React.MouseEvent
  ) {
    e.stopPropagation();
    updateChat.mutate({ id, updates: { is_pinned: !isPinned } });
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-[#a3a3a3]">Loading chats...</div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Chats</h1>
          <button
            onClick={handleNewChat}
            disabled={createChat.isPending}
            className="px-4 py-2 bg-gradient-to-r from-teal-600 to-teal-700 hover:from-teal-500 hover:to-teal-600 text-white rounded-xl font-medium transition-all disabled:opacity-50"
          >
            + New Chat
          </button>
        </div>

        {/* Search */}
        <div className="mb-6">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search your chats..."
            className="w-full px-4 py-3 bg-[#f8f8f8] dark:bg-[#242424] border border-zinc-300 dark:border-[#3a3a3a] rounded-xl text-[#1a1a1a] dark:text-[#ececec] placeholder-zinc-400 dark:placeholder-[#a3a3a3] focus:outline-none focus:border-[#0d9488]"
          />
        </div>

        {/* Chat Count */}
        <div className="text-sm text-[#a3a3a3] mb-4">
          {filteredChats.length} chat{filteredChats.length !== 1 ? "s" : ""}
        </div>

        {/* Chat List */}
        <div className="space-y-2">
          {filteredChats.length === 0 ? (
            <div className="text-center py-12 text-[#a3a3a3]">
              {search
                ? "No chats match your search"
                : "No chats yet. Start a new one!"}
            </div>
          ) : (
            filteredChats.map((chat) => (
              <div
                key={chat.id}
                onClick={() => navigate(`/chat/${chat.id}`)}
                className="group flex items-center justify-between p-4 bg-[#f8f8f8] dark:bg-[#242424] hover:bg-zinc-50 dark:hover:bg-neutral-800 border border-[#e8e8e8] dark:border-[#3a3a3a] rounded-xl cursor-pointer transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    {chat.is_pinned && (
                      <span className="text-yellow-500">📌</span>
                    )}
                    <h3 className="font-medium truncate">{chat.title}</h3>
                  </div>
                  <p className="text-sm text-[#a3a3a3] mt-1">
                    {new Date(chat.updated_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={(e) => handlePinChat(chat.id, chat.is_pinned, e)}
                    className="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
                    title={chat.is_pinned ? "Unpin" : "Pin"}
                  >
                    {chat.is_pinned ? "📌" : "📍"}
                  </button>
                  <button
                    onClick={(e) => handleDeleteChat(chat.id, e)}
                    className="p-2 hover:bg-red-100 dark:hover:bg-red-900/50 text-red-500 dark:text-red-400 rounded-lg transition-colors"
                    title="Delete"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
