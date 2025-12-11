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
    const file = e.target.files?.[0];
    if (!file || !id) return;

    try {
      await uploadDocument.mutateAsync({
        scopeType: "chat",
        scopeId: id,
        file,
      });
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
        <div className="text-zinc-500">Select or create a chat</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {messagesLoading ? (
          <div className="text-center text-zinc-500">Loading messages...</div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center mb-4">
              <span className="text-3xl">📚</span>
            </div>
            <h2 className="text-xl font-semibold mb-2">
              Start your conversation
            </h2>
            <p className="text-zinc-500 mb-4">
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
                  ? "ml-auto bg-gradient-to-br from-indigo-600 to-violet-600 text-white"
                  : "mr-auto bg-zinc-800 border border-zinc-700"
              }`}
            >
              <div className="whitespace-pre-wrap">{msg.content}</div>
              {msg.sources.length > 0 && (
                <details className="mt-3 text-sm">
                  <summary className="cursor-pointer text-zinc-300/80 hover:text-white">
                    📚 Sources ({msg.sources.length})
                  </summary>
                  <ul className="mt-2 pl-5 text-zinc-400 list-disc">
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
          <div className="max-w-[85%] p-4 rounded-2xl mr-auto bg-zinc-800 border border-zinc-700">
            <div className="flex items-center gap-2">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" />
                <span
                  className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce"
                  style={{ animationDelay: "0.15s" }}
                />
                <span
                  className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce"
                  style={{ animationDelay: "0.3s" }}
                />
              </div>
              <span className="text-zinc-400 text-sm">Thinking...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-zinc-800 bg-zinc-900">
        {/* Settings Toggle */}
        <div className="flex items-center justify-between mb-3">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="text-sm text-zinc-500 hover:text-white flex items-center gap-1"
          >
            ⚙️ Settings {showSettings ? "▲" : "▼"}
          </button>
          <span className="text-xs text-zinc-600">
            {documents.length} document{documents.length !== 1 ? "s" : ""} • Top{" "}
            {topK}
          </span>
        </div>

        {/* Settings Panel */}
        {showSettings && (
          <div className="mb-4 p-4 bg-zinc-800 rounded-xl space-y-4">
            <label className="flex items-center justify-between text-sm">
              <span className="text-zinc-400">Chunks (top_k):</span>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="1"
                  max="20"
                  value={topK}
                  onChange={(e) => setTopK(parseInt(e.target.value))}
                  className="w-24 accent-indigo-500"
                />
                <span className="text-white w-6 text-center">{topK}</span>
              </div>
            </label>

            <div className="border-t border-zinc-700 pt-3">
              <span className="text-sm text-zinc-400 block mb-2">
                Attached Documents
              </span>
              {documents.length === 0 ? (
                <div className="text-sm text-zinc-500 italic">
                  No documents attached
                </div>
              ) : (
                <div className="space-y-2">
                  {documents.map((doc) => (
                    <div
                      key={doc.id}
                      className="flex items-center justify-between text-sm bg-zinc-900 p-2 rounded-lg"
                    >
                      <span
                        className="truncate text-zinc-300 max-w-[200px]"
                        title={doc.filename}
                      >
                        {doc.filename}
                      </span>
                      <span className="text-xs text-zinc-500">
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
            onChange={handleFileUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadDocument.isPending}
            className="p-3 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-white transition-colors disabled:opacity-50"
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
            className="flex-1 px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
          />

          <button
            onClick={handleSend}
            disabled={!input.trim() || sending || documents.length === 0}
            className="p-3 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:opacity-50 text-white rounded-xl transition-all"
          >
            ➤
          </button>
        </div>
      </div>
    </div>
  );
}
