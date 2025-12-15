/**
 * Chat View Page - Conversation with document upload.
 */
import { useState, useRef, useEffect } from "react";
import { useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  useChat,
  useChatMessages,
  useChatDocuments,
  chatKeys,
  useUpdateChat,
} from "../hooks/useChats";
import { useUploadDocument } from "../hooks/useDocuments";
import { useAuth } from "../context/AuthContext";
import * as api from "../api";
import type { Message, AIModel, QualityPreset } from "../types";
import logo from "../assets/logo.png";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ModelSelector } from "../components/ModelSelector";
import { TokenLimitModal } from "../components/TokenLimitModal";
import {
  QualityPresetSelector,
  getChunkCount,
} from "../components/QualityPresetSelector";
import { TokenUsageBar } from "../components/TokenUsageBar";
import { LoadingStages } from "../components/LoadingStages";
import { TypewriterMessage } from "../components/TypewriterMessage";

export function ChatViewPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const [input, setInput] = useState("");
  const [showSettings, setShowSettings] = useState(false);
  const [sending, setSending] = useState(false);
  const [showLimitModal, setShowLimitModal] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: chat } = useChat(id || null);
  const { data: messages = [], isLoading: messagesLoading } = useChatMessages(
    id || null
  );
  const { data: documents = [] } = useChatDocuments(id || null);
  const uploadDocument = useUploadDocument();
  const updateChat = useUpdateChat();
  const { user, addTokensUsed } = useAuth();

  // Get user's subscription tier from their plan
  const userTier = user?.plan || "free";

  // Get current model from chat or default to deepseek-v3
  const currentModel: AIModel = (chat?.model as AIModel) || "deepseek-v3";

  // Get current quality preset from chat or default to standard
  const currentPreset: QualityPreset =
    (chat?.quality_preset as QualityPreset) || "standard";

  // Check if user is at token limit
  const isAtTokenLimit = user ? user.tokens_used >= user.token_limit : false;

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    if (!input.trim() || !id || sending) return;

    // Check token limit before sending
    if (user && user.tokens_used >= user.token_limit) {
      setShowLimitModal(true);
      return;
    }

    const userMessage = input.trim();
    setInput("");
    setSending(true);

    try {
      // Optimistic update for user message
      const tempUserMsg: Message = {
        id: `temp-${Date.now()}`,
        chat_id: id,
        role: "user",
        content: userMessage,
        timestamp: new Date().toISOString(),
        sources: [],
      };

      queryClient.setQueryData<Message[]>(chatKeys.messages(id), (old) =>
        old ? [...old, tempUserMsg] : [tempUserMsg]
      );

      // Save user message
      await api.saveMessage(id, "user", userMessage);

      // Send query event
      const scope = chat?.project_id
        ? { type: "project" as const, id: chat.project_id }
        : { type: "chat" as const, id };

      const eventIds = await api.sendQueryEvent(
        userMessage,
        id,
        scope.type,
        scope.id,
        currentModel,
        getChunkCount(currentPreset),
        messages.slice(-10).map((m) => ({ role: m.role, content: m.content }))
      );

      if (eventIds.length > 0) {
        const result = await api.waitForRunOutput(eventIds[0]);
        const answer =
          (result.answer as string) || "I couldn't find an answer.";
        const sources = (result.sources as string[]) || [];
        const tokensUsed = (result.tokens_used as number) || 0;

        // Save assistant message
        await api.saveMessage(id, "assistant", answer, sources);

        // Refetch messages
        queryClient.invalidateQueries({ queryKey: chatKeys.messages(id) });

        // Update token count locally (no extra API call)
        if (tokensUsed > 0) {
          addTokensUsed(tokensUsed);
        }
      }
    } catch (error: unknown) {
      console.error("Query failed:", error);
      // Check if it's a token limit error
      if (
        error &&
        typeof error === "object" &&
        "status" in error &&
        (error as { status: number }).status === 403
      ) {
        setShowLimitModal(true);
      } else {
        alert("Failed to get response");
      }
    } finally {
      setSending(false);
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0 || !id) return;

    // Convert FileList to array for parallel processing
    const fileArray = Array.from(files);

    try {
      // Upload all files in parallel
      const uploadPromises = fileArray.map((file) =>
        uploadDocument
          .mutateAsync({
            scopeType: "chat",
            scopeId: id,
            file,
          })
          .catch((error: Error & { status?: number }) => {
            console.error(`Upload failed for ${file.name}:`, error);
            return {
              error: true,
              filename: file.name,
              message: error.message,
              status: error.status,
            };
          })
      );

      const results = await Promise.all(uploadPromises);

      // Check for any errors
      const errors = results.filter(
        (
          r
        ): r is {
          error: boolean;
          filename: string;
          message: string;
          status?: number;
        } => r && typeof r === "object" && "error" in r
      );

      if (errors.length > 0) {
        // Check if it's a limit error (403)
        const limitError = errors.find((e) => e.status === 403);
        if (limitError) {
          setShowLimitModal(true);
        } else {
          const errorNames = errors.map((e) => e.filename).join(", ");
          alert(`Some uploads failed: ${errorNames}\n${errors[0].message}`);
        }
      }
    } catch (error) {
      console.error("Upload failed:", error);
      alert("Upload failed");
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  if (!id) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-[#a3a3a3]">Select or create a chat</div>
      </div>
    );
  }

  return (
    <>
      <div className="flex flex-col h-full">
        {/* Messages - Outer container handles scroll, inner is centered */}
        <div className="flex-1 overflow-auto">
          <div className="max-w-3xl mx-auto p-4 space-y-4">
            {messagesLoading ? (
              <>
                <LoadingSpinner size="md" />
                <div className="text-center text-[#a3a3a3]">
                  Loading messages...
                </div>
              </>
            ) : messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-teal-500 to-teal-700 flex items-center justify-center mb-4">
                  <img src={logo} alt="Querious" className="w-10 h-10" />
                </div>
                <h2 className="text-xl font-semibold mb-2">
                  Start your conversation
                </h2>
                <p className="text-[#a3a3a3] mb-4">
                  {documents.length === 0
                    ? "Upload a PDF to get started"
                    : "Ask a question about your documents"}
                </p>
              </div>
            ) : (
              messages.map((msg, index) => {
                // Typewriter effect for the most recent assistant message
                const isLastAssistantMessage =
                  msg.role === "assistant" && index === messages.length - 1;

                return (
                  <div
                    key={msg.id}
                    className={`max-w-[85%] p-4 rounded-2xl ${
                      msg.role === "user"
                        ? "ml-auto bg-gradient-to-br from-teal-600 to-teal-700 text-white"
                        : "mr-auto bg-[#f8f8f8] dark:bg-[#242424] border border-[#e8e8e8] dark:border-[#3a3a3a]"
                    }`}
                  >
                    {msg.role === "assistant" ? (
                      <TypewriterMessage
                        content={msg.content}
                        animate={isLastAssistantMessage}
                      />
                    ) : (
                      <div className="whitespace-pre-wrap">{msg.content}</div>
                    )}
                    {msg.sources.length > 0 && (
                      <details className="mt-3 text-sm">
                        <summary className="cursor-pointer text-zinc-300/80 hover:text-white">
                          📚 Sources ({msg.sources.length})
                        </summary>
                        <ul className="mt-2 pl-5 text-[#a0a0a0] list-disc">
                          {msg.sources.map((src, i) => (
                            <li key={i} className="text-xs">
                              {src}
                            </li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </div>
                );
              })
            )}

            {sending && (
              <div className="max-w-[85%] p-4 rounded-2xl mr-auto bg-[#f8f8f8] dark:bg-[#242424] border border-[#e8e8e8] dark:border-[#3a3a3a]">
                <LoadingStages />
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Floating Input Bubble - positioned at bottom without border-top */}
        <div className="pb-4 md:pb-6 px-4">
          <div className="max-w-3xl mx-auto">
            {/* Settings Panel - floating above input when open */}
            {showSettings && (
              <div className="mb-3 p-4 bg-[#ffffff] dark:bg-[#242424] border border-[#e8e8e8] dark:border-[#3a3a3a] rounded-2xl shadow-sm space-y-4">
                {/* Quality Preset Selector */}
                <QualityPresetSelector
                  value={currentPreset}
                  onChange={(preset) => {
                    if (id) {
                      updateChat.mutate({
                        id,
                        updates: { quality_preset: preset },
                      });
                    }
                  }}
                  userPlan={userTier}
                  disabled={sending}
                />

                {/* Token Usage Bar */}
                {user && (
                  <TokenUsageBar
                    tokensUsed={user.tokens_used}
                    tokenLimit={user.token_limit}
                    plan={userTier}
                  />
                )}

                <div className="border-t border-[#e8e8e8] dark:border-[#3a3a3a] mt-3 pt-3">
                  <span className="text-sm text-[#737373] dark:text-[#a0a0a0] block mb-2">
                    Attached Documents ({documents.length})
                  </span>
                  {documents.length === 0 ? (
                    <div className="text-sm text-[#a3a3a3] italic">
                      No documents attached
                    </div>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {documents.map((doc) => (
                        <span
                          key={doc.id}
                          className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-[#f0f0f0] dark:bg-[#1e1e1e] rounded-lg text-[#525252] dark:text-[#a0a0a0]"
                          title={doc.filename}
                        >
                          📄{" "}
                          {doc.filename.length > 20
                            ? doc.filename.slice(0, 20) + "..."
                            : doc.filename}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Model Selector - above input, opens upward */}
            <div className="mb-3">
              <ModelSelector
                value={currentModel}
                onChange={(model) => {
                  if (id) {
                    updateChat.mutate({ id, updates: { model } });
                  }
                }}
                userTier={userTier}
                disabled={sending}
              />
            </div>

            {/* Floating Bubble Input */}
            <div className="flex items-end gap-2 p-3 bg-[#ffffff] dark:bg-[#242424] border border-[#e8e8e8] dark:border-[#3a3a3a] focus-within:border-[#0d9488] dark:focus-within:border-[#2dd4bf] rounded-3xl shadow-[0_2px_12px_rgba(0,0,0,0.08)] dark:shadow-[0_2px_12px_rgba(0,0,0,0.25)] transition-colors">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                multiple
                onChange={handleFileUpload}
                className="hidden"
              />

              {/* Attach Button */}
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadDocument.isPending}
                className="p-2 rounded-full text-[#737373] dark:text-[#a0a0a0] hover:text-[#1a1a1a] dark:hover:text-white hover:bg-[#f0f0f0] dark:hover:bg-[#3a3a3a] transition-colors disabled:opacity-50 flex-shrink-0"
                title="Attach PDF"
              >
                {uploadDocument.isPending ? (
                  <span className="text-lg">⏳</span>
                ) : (
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
                    />
                  </svg>
                )}
              </button>

              {/* Settings Toggle - small icon */}
              <button
                onClick={() => setShowSettings(!showSettings)}
                className={`p-2 rounded-full transition-colors flex-shrink-0 ${
                  showSettings
                    ? "text-[#0d9488] dark:text-[#2dd4bf] bg-[#e6f7f5] dark:bg-[#0f2e2b]"
                    : "text-[#737373] dark:text-[#a0a0a0] hover:text-[#1a1a1a] dark:hover:text-white hover:bg-[#f0f0f0] dark:hover:bg-[#3a3a3a]"
                }`}
                title={`Settings (${documents.length} docs, ${currentPreset})`}
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
              </button>

              {/* Text Input - transparent, borderless */}
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    if (isAtTokenLimit) {
                      setShowLimitModal(true);
                    } else {
                      handleSend();
                    }
                  }
                }}
                onClick={() => isAtTokenLimit && setShowLimitModal(true)}
                placeholder={
                  isAtTokenLimit
                    ? "Token limit reached — upgrade to continue"
                    : documents.length > 0
                    ? "Message..."
                    : "Upload a document first..."
                }
                disabled={sending || documents.length === 0}
                className={`input-transparent flex-1 py-2 px-1 bg-transparent border-0 outline-0 ring-0 text-[#1a1a1a] dark:text-[#ececec] placeholder-[#a3a3a3] focus:outline-none focus:ring-0 disabled:opacity-50 min-w-0 ${
                  isAtTokenLimit ? "cursor-pointer" : ""
                }`}
              />

              {/* Send Button - circular */}
              <button
                onClick={handleSend}
                disabled={!input.trim() || sending || documents.length === 0}
                className={`p-2.5 rounded-full transition-all flex-shrink-0 ${
                  input.trim() && !sending && documents.length > 0
                    ? "bg-[#0d9488] hover:bg-[#0f766e] dark:bg-[#2dd4bf] dark:hover:bg-[#5eead4] text-white dark:text-[#0f2e2b] shadow-sm"
                    : "bg-[#e8e8e8] dark:bg-[#3a3a3a] text-[#a3a3a3] dark:text-[#6b6b6b] cursor-not-allowed"
                }`}
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Token Limit Modal */}
      <TokenLimitModal
        isOpen={showLimitModal}
        onClose={() => setShowLimitModal(false)}
        tokensUsed={user?.tokens_used || 0}
        tokenLimit={user?.token_limit || 5000}
        currentPlan={user?.plan || "free"}
      />
    </>
  );
}
