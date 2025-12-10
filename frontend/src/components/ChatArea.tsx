import { useRef, useEffect, useState } from "react";
import type { Message } from "../types";

interface ChatAreaProps {
  messages: Message[];
  loading: boolean;
  hasDocuments: boolean;
  hasChat: boolean;
  input: string;
  topK: number;
  onInputChange: (value: string) => void;
  onTopKChange: (value: number) => void;
  onSendMessage: () => void;
  onStartChat: () => void;
}

export function ChatArea({
  messages,
  loading,
  hasDocuments,
  hasChat,
  input,
  topK,
  onInputChange,
  onTopKChange,
  onSendMessage,
  onStartChat,
}: ChatAreaProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (!hasChat) {
    return (
      <main className="flex-1 flex flex-col items-center justify-center text-center text-zinc-500">
        <h2 className="text-2xl font-semibold text-white mb-2">
          Welcome to DocuRAG
        </h2>
        <p className="mb-4">Upload PDFs and ask questions about them.</p>
        {!hasDocuments ? (
          <p>👈 Start by uploading a PDF in the sidebar</p>
        ) : (
          <button
            onClick={onStartChat}
            className="mt-4 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors"
          >
            Start a new chat
          </button>
        )}
      </main>
    );
  }

  return (
    <main className="flex-1 flex flex-col bg-zinc-950">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`max-w-[80%] p-4 rounded-xl animate-fade-in ${
              msg.role === "user"
                ? "ml-auto bg-indigo-600 text-white rounded-br-sm"
                : "mr-auto bg-zinc-800 border border-zinc-700 rounded-bl-sm"
            }`}
          >
            <div className="whitespace-pre-wrap break-words">{msg.content}</div>
            {msg.sources.length > 0 && (
              <details className="mt-3 text-sm">
                <summary className="cursor-pointer text-zinc-400">
                  📚 Sources ({msg.sources.length})
                </summary>
                <ul className="mt-2 pl-5 text-zinc-400 list-disc">
                  {msg.sources.map((src, i) => (
                    <li key={i}>{src}</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        ))}

        {loading && (
          <div className="max-w-[80%] mr-auto p-4 bg-zinc-800 border border-zinc-700 rounded-xl rounded-bl-sm">
            <span className="text-zinc-400 italic">Thinking...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-zinc-900 border-t border-zinc-800">
        {/* Settings Toggle */}
        <div className="mb-3 flex items-center justify-between">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="text-sm text-zinc-500 hover:text-zinc-300 flex items-center gap-1"
          >
            ⚙️ Settings {showSettings ? "▲" : "▼"}
          </button>
          {hasDocuments && (
            <span className="text-xs text-zinc-600">
              Searching top {topK} chunks
            </span>
          )}
        </div>

        {/* Settings Panel */}
        {showSettings && (
          <div className="mb-4 p-3 bg-zinc-800 rounded-lg">
            <label className="flex items-center justify-between text-sm">
              <span className="text-zinc-400">Chunks (top_k):</span>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="1"
                  max="20"
                  value={topK}
                  onChange={(e) => onTopKChange(parseInt(e.target.value))}
                  className="w-24 accent-indigo-600"
                />
                <span className="text-white w-6 text-center">{topK}</span>
              </div>
            </label>
          </div>
        )}

        {/* Message Input */}
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onSendMessage()}
            placeholder="Ask a question about your documents..."
            disabled={loading || !hasDocuments}
            className="flex-1 px-4 py-3 bg-zinc-950 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
          />
          <button
            onClick={onSendMessage}
            disabled={loading || !input.trim()}
            className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-600/50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </main>
  );
}
