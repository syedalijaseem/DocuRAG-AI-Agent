/**
 * Chat View Page - Conversation with document upload.
 */
import { useState, useRef, useEffect } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  useChat,
  useChatMessages,
  useChatDocuments,
  chatKeys,
} from "../hooks/useChats";
import { useUploadDocument } from "../hooks/useDocuments";
import * as api from "../api";
import type { Message } from "../types";

export function ChatViewPage() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();

  const [input, setInput] = useState("");
  const [topK, setTopK] = useState(5);
  const [showSettings, setShowSettings] = useState(false);
  const [sending, setSending] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: chat } = useChat(id || null);
  const { data: messages = [], isLoading: messagesLoading } = useChatMessages(
    id || null
  );
  const { data: documents = [] } = useChatDocuments(id || null);
  const uploadDocument = useUploadDocument();

  // Send initial message from URL param
  useEffect(() => {
    const initialMessage = searchParams.get("message");
    if (initialMessage && id && !sending) {
      setInput(initialMessage);
      // Clear the param
      window.history.replaceState({}, "", `/chat/${id}`);
    }
  }, [searchParams, id, sending]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    if (!input.trim() || !id || sending) return;

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
        topK,
        messages.slice(-10).map((m) => ({ role: m.role, content: m.content }))
      );

      if (eventIds.length > 0) {
        const result = await api.waitForRunOutput(eventIds[0]);
        const answer =
          (result.answer as string) || "I couldn't find an answer.";
        const sources = (result.sources as string[]) || [];

        // Save assistant message
        await api.saveMessage(id, "assistant", answer, sources);

        // Refetch messages
        queryClient.invalidateQueries({ queryKey: chatKeys.messages(id) });
      }
    } catch (error) {
      console.error("Query failed:", error);
      alert("Failed to get response");
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
          .catch((error) => {
            console.error(`Upload failed for ${file.name}:`, error);
            return { error: true, filename: file.name, message: error.message };
          })
      );

      const results = await Promise.all(uploadPromises);

      // Check for any errors
      const errors = results.filter(
        (r): r is { error: boolean; filename: string; message: string } =>
          r && typeof r === "object" && "error" in r
      );

      if (errors.length > 0) {
        const errorNames = errors.map((e) => e.filename).join(", ");
        alert(`Some uploads failed: ${errorNames}\n${errors[0].message}`);
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
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {messagesLoading ? (
          <div className="text-center text-[#a3a3a3]">Loading messages...</div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-teal-500 to-teal-700 flex items-center justify-center mb-4">
              <span className="text-3xl">📚</span>
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
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`max-w-[85%] p-4 rounded-2xl ${
                msg.role === "user"
                  ? "ml-auto bg-gradient-to-br from-teal-600 to-teal-700 text-white"
                  : "mr-auto bg-[#f8f8f8] dark:bg-[#242424] border border-[#e8e8e8] dark:border-[#3a3a3a]"
              }`}
            >
              <div className="whitespace-pre-wrap">{msg.content}</div>
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
          ))
        )}

        {sending && (
          <div className="max-w-[85%] p-4 rounded-2xl mr-auto bg-[#f8f8f8] dark:bg-[#242424] border border-[#e8e8e8] dark:border-[#3a3a3a]">
            <div className="flex items-center gap-2">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-[#14b8a6] rounded-full animate-bounce" />
                <span
                  className="w-2 h-2 bg-[#14b8a6] rounded-full animate-bounce"
                  style={{ animationDelay: "0.15s" }}
                />
                <span
                  className="w-2 h-2 bg-[#14b8a6] rounded-full animate-bounce"
                  style={{ animationDelay: "0.3s" }}
                />
              </div>
              <span className="text-[#a0a0a0] text-sm">Thinking...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-[#e8e8e8] dark:border-[#3a3a3a] bg-[#f8f8f8] dark:bg-[#242424]">
        {/* Settings Toggle */}
        <div className="flex items-center justify-between mb-3">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="text-sm text-[#a3a3a3] hover:text-[#1a1a1a] dark:hover:text-white flex items-center gap-1"
          >
            ⚙️ Settings {showSettings ? "▲" : "▼"}
          </button>
          <span className="text-xs text-[#a3a3a3] dark:text-zinc-600">
            {documents.length} document{documents.length !== 1 ? "s" : ""} • Top{" "}
            {topK}
          </span>
        </div>

        {/* Settings Panel */}
        {showSettings && (
          <div className="mb-4 p-4 bg-neutral-100 dark:bg-[#242424] rounded-xl space-y-4">
            <label className="flex items-center justify-between text-sm">
              <span className="text-[#a0a0a0]">Chunks (top_k):</span>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="1"
                  max="20"
                  value={topK}
                  onChange={(e) => setTopK(parseInt(e.target.value))}
                  className="w-24 accent-teal-500"
                />
                <span className="text-white w-6 text-center">{topK}</span>
              </div>
            </label>

            <div className="border-t border-[#e8e8e8] dark:border-[#3a3a3a] pt-3">
              <span className="text-sm text-[#a0a0a0] block mb-2">
                Attached Documents
              </span>
              {documents.length === 0 ? (
                <div className="text-sm text-[#a3a3a3] italic">
                  No documents attached
                </div>
              ) : (
                <div className="space-y-2">
                  {documents.map((doc) => (
                    <div
                      key={doc.id}
                      className="flex items-center justify-between text-sm bg-[#f8f8f8] dark:bg-[#242424] p-2 rounded-lg"
                    >
                      <span
                        className="truncate text-zinc-300 max-w-[200px]"
                        title={doc.filename}
                      >
                        {doc.filename}
                      </span>
                      <span className="text-xs text-[#a3a3a3]">
                        {new Date(doc.uploaded_at).toLocaleDateString()}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Input */}
        <div className="flex items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            multiple
            onChange={handleFileUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadDocument.isPending}
            className="p-3 rounded-xl bg-neutral-100 dark:bg-[#242424] hover:bg-neutral-200 dark:hover:bg-neutral-700 text-zinc-600 dark:text-[#a0a0a0] hover:text-[#1a1a1a] dark:hover:text-white transition-colors disabled:opacity-50"
            title="Attach PDF"
          >
            {uploadDocument.isPending ? "⏳" : "📎"}
          </button>

          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder={
              documents.length > 0
                ? "Ask a question..."
                : "Upload a document first..."
            }
            disabled={sending || documents.length === 0}
            className="flex-1 px-4 py-3 bg-neutral-100 dark:bg-[#242424] border border-zinc-300 dark:border-[#3a3a3a] rounded-xl text-[#1a1a1a] dark:text-[#ececec] placeholder-zinc-400 dark:placeholder-[#a3a3a3] focus:outline-none focus:border-[#0d9488] disabled:opacity-50"
          />

          <button
            onClick={handleSend}
            disabled={!input.trim() || sending || documents.length === 0}
            className="p-3 bg-gradient-to-r from-teal-600 to-teal-700 hover:from-teal-500 hover:to-teal-600 disabled:opacity-50 text-white rounded-xl transition-all"
          >
            ➤
          </button>
        </div>
      </div>
    </div>
  );
}
