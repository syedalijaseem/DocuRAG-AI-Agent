/**
 * Chats Page - List of all chats with modern styling and Lucide icons.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { formatRelativeTime } from "../utils/formatTime";
import {
  MessageSquare,
  Plus,
  Search,
  Pin,
  Trash2,
  MessageSquarePlus,
} from "lucide-react";
import {
  useStandaloneChats,
  useCreateChat,
  useDeleteChat,
  useUpdateChat,
} from "../hooks/useChats";
import { useAuth } from "../context/AuthContext";
import { LimitModal } from "../components/LimitModal";

export function ChatsPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [showLimitModal, setShowLimitModal] = useState(false);
  const { user } = useAuth();

  const { data: chats = [], isLoading } = useStandaloneChats();
  const createChat = useCreateChat();
  const deleteChat = useDeleteChat();
  const updateChat = useUpdateChat();

  const filteredChats = chats.filter((chat) =>
    chat.title.toLowerCase().includes(search.toLowerCase())
  );

  // Sort: pinned first, then by date (fallback to created_at)
  const sortedChats = [...filteredChats].sort((a, b) => {
    if (a.is_pinned && !b.is_pinned) return -1;
    if (!a.is_pinned && b.is_pinned) return 1;
    return (
      new Date(b.updated_at || b.created_at).getTime() -
      new Date(a.updated_at || a.created_at).getTime()
    );
  });

  async function handleNewChat() {
    try {
      const newChat = await createChat.mutateAsync({ title: "New Chat" });
      navigate(`/chat/${newChat.id}`);
    } catch (error: unknown) {
      // Check for limit error
      if (
        error &&
        typeof error === "object" &&
        "status" in error &&
        (error as { status: number }).status === 403
      ) {
        setShowLimitModal(true);
      } else {
        console.error("Failed to create chat:", error);
      }
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

  // Format relative date - use utility function
  function formatDate(dateStr: string) {
    const formatted = formatRelativeTime(dateStr);
    return formatted || "Unknown";
  }

  if (isLoading) {
    return (
      <div className="h-full overflow-auto">
        <div className="max-w-3xl mx-auto p-6">
          {/* Loading Skeleton */}
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-[#e8e8e8] dark:bg-[#2a2a2a] rounded w-32" />
            <div className="h-12 bg-[#e8e8e8] dark:bg-[#2a2a2a] rounded-xl" />
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="flex gap-3 p-4 bg-[#f0f0f0] dark:bg-[#1e1e1e] rounded-xl"
              >
                <div className="w-10 h-10 bg-[#e8e8e8] dark:bg-[#2a2a2a] rounded-lg" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-[#e8e8e8] dark:bg-[#2a2a2a] rounded w-3/4" />
                  <div className="h-3 bg-[#e8e8e8] dark:bg-[#2a2a2a] rounded w-1/4" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="h-full overflow-auto">
        <div className="max-w-3xl mx-auto p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold text-[#1a1a1a] dark:text-[#ececec]">
              Chats
            </h1>
            <button
              onClick={handleNewChat}
              disabled={createChat.isPending}
              className="flex items-center gap-2 px-4 py-2.5 bg-[#0d9488] hover:bg-[#0f766e] dark:bg-[#2dd4bf] dark:hover:bg-[#5eead4] text-white dark:text-[#0f2e2b] rounded-xl font-medium transition-all disabled:opacity-50"
            >
              <Plus className="w-5 h-5" />
              <span>New Chat</span>
            </button>
          </div>

          {/* Search */}
          <div className="relative mb-6">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#a3a3a3]" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search your chats..."
              className="w-full pl-12 pr-4 py-3 bg-[#ffffff] dark:bg-[#242424] border border-[#e8e8e8] dark:border-[#3a3a3a] rounded-xl text-[#1a1a1a] dark:text-[#ececec] placeholder-[#a3a3a3] focus:outline-none focus:border-[#0d9488] dark:focus:border-[#2dd4bf] transition-colors"
            />
          </div>

          {/* Chat Count */}
          <div className="text-sm text-[#737373] dark:text-[#a0a0a0] mb-4">
            {sortedChats.length} chat{sortedChats.length !== 1 ? "s" : ""}
          </div>

          {/* Chat List */}
          <div className="space-y-2">
            {sortedChats.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="w-16 h-16 flex items-center justify-center bg-[#f0f0f0] dark:bg-[#242424] rounded-2xl mb-4">
                  <MessageSquarePlus className="w-8 h-8 text-[#a3a3a3] dark:text-[#6b6b6b]" />
                </div>
                <h3 className="text-lg font-semibold text-[#1a1a1a] dark:text-[#ececec] mb-2">
                  {search ? "No chats found" : "No chats yet"}
                </h3>
                <p className="text-sm text-[#737373] dark:text-[#a0a0a0] max-w-xs">
                  {search
                    ? "Try a different search term"
                    : "Start a conversation by creating a new chat"}
                </p>
              </div>
            ) : (
              sortedChats.map((chat) => (
                <div
                  key={chat.id}
                  onClick={() => navigate(`/chat/${chat.id}`)}
                  className="group relative flex items-center gap-3 p-3 hover:bg-[#f0f0f0] dark:hover:bg-[#2a2a2a] rounded-xl cursor-pointer transition-all"
                >
                  {/* Icon */}
                  <div className="w-10 h-10 flex items-center justify-center bg-[#f0f0f0] dark:bg-[#242424] group-hover:bg-[#e6f7f5] dark:group-hover:bg-[#0f2e2b] rounded-lg transition-colors">
                    <MessageSquare className="w-5 h-5 text-[#737373] dark:text-[#a0a0a0] group-hover:text-[#0d9488] dark:group-hover:text-[#2dd4bf] transition-colors" />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      {chat.is_pinned && (
                        <Pin className="w-3.5 h-3.5 text-[#0d9488] dark:text-[#2dd4bf] fill-current" />
                      )}
                      <h3 className="font-medium text-[#1a1a1a] dark:text-[#ececec] truncate">
                        {chat.title}
                      </h3>
                    </div>
                    <p className="text-sm text-[#a3a3a3] dark:text-[#6b6b6b] mt-0.5">
                      {formatDate(chat.updated_at || chat.created_at)}
                    </p>
                  </div>

                  {/* Actions (show on hover) */}
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => handlePinChat(chat.id, chat.is_pinned, e)}
                      className={`p-2 rounded-lg transition-colors ${
                        chat.is_pinned
                          ? "bg-[#e6f7f5] dark:bg-[#0f2e2b] text-[#0d9488] dark:text-[#2dd4bf]"
                          : "hover:bg-[#e8e8e8] dark:hover:bg-[#3a3a3a] text-[#737373] dark:text-[#a0a0a0]"
                      }`}
                      title={chat.is_pinned ? "Unpin" : "Pin"}
                    >
                      <Pin className="w-4 h-4" />
                    </button>
                    <button
                      onClick={(e) => handleDeleteChat(chat.id, e)}
                      className="p-2 hover:bg-[#fdeaea] dark:hover:bg-[#2e1616] text-[#737373] dark:text-[#a0a0a0] hover:text-[#dc2626] dark:hover:text-[#f87171] rounded-lg transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Limit Modal */}
      <LimitModal
        isOpen={showLimitModal}
        onClose={() => setShowLimitModal(false)}
        limitType="chats"
        currentPlan={user?.plan || "free"}
      />
    </>
  );
}
