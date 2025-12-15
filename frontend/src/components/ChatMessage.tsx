/**
 * ChatMessage - Modern chat message with markdown rendering
 */
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { User, FileText, ChevronDown, ChevronUp } from "lucide-react";
import logo from "../assets/logo.png";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
}

export function ChatMessage({ role, content, sources }: ChatMessageProps) {
  const isUser = role === "user";
  const [showAllSources, setShowAllSources] = useState(false);

  const visibleSources = showAllSources ? sources : sources?.slice(0, 4);
  const hasMoreSources = sources && sources.length > 4;

  return (
    <div
      className={`py-6 ${
        isUser ? "bg-transparent" : "bg-[#f5f5f5] dark:bg-[#1e1e1e]"
      }`}
    >
      <div className="max-w-3xl mx-auto px-4">
        <div className="flex gap-4">
          {/* Avatar */}
          <div
            className={`
              w-8 h-8 rounded-full flex items-center justify-center shrink-0
              ${
                isUser
                  ? "bg-gradient-to-br from-teal-500 to-teal-600"
                  : "bg-[#e8e8e8] dark:bg-[#2a2a2a]"
              }
            `}
          >
            {isUser ? (
              <User size={16} className="text-white" />
            ) : (
              <img
                src={logo}
                alt="Querious"
                className="w-5 h-5 object-contain"
              />
            )}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Role label */}
            <p className="text-sm font-semibold text-[#171717] dark:text-[#fafafa] mb-2">
              {isUser ? "You" : "Querious"}
            </p>

            {/* Message content with markdown */}
            <div
              className="prose prose-sm dark:prose-invert max-w-none
                prose-p:text-[#525252] dark:prose-p:text-[#d4d4d4] prose-p:leading-relaxed prose-p:my-2
                prose-strong:text-[#171717] dark:prose-strong:text-[#fafafa] prose-strong:font-semibold
                prose-ul:text-[#525252] dark:prose-ul:text-[#d4d4d4] prose-ul:my-2
                prose-ol:text-[#525252] dark:prose-ol:text-[#d4d4d4] prose-ol:my-2
                prose-li:text-[#525252] dark:prose-li:text-[#d4d4d4] prose-li:my-0.5
                prose-headings:text-[#171717] dark:prose-headings:text-[#fafafa] prose-headings:mt-4 prose-headings:mb-2
                prose-code:text-[#14b8a6] prose-code:bg-[#e8e8e8] dark:prose-code:bg-[#2a2a2a] prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-sm
                prose-pre:bg-[#1e1e1e] prose-pre:text-[#d4d4d4] prose-pre:rounded-lg prose-pre:my-3
                prose-a:text-[#14b8a6] prose-a:no-underline hover:prose-a:underline
                prose-blockquote:border-l-[#14b8a6] prose-blockquote:text-[#737373] dark:prose-blockquote:text-[#a0a0a0]
              "
            >
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>

            {/* Sources */}
            {sources && sources.length > 0 && (
              <div className="mt-4">
                <div className="flex flex-wrap items-center gap-2">
                  <FileText
                    size={14}
                    className="text-[#737373] dark:text-[#a0a0a0]"
                  />
                  <span className="text-xs text-[#737373] dark:text-[#a0a0a0]">
                    {sources.length} source{sources.length > 1 ? "s" : ""}:
                  </span>
                  {visibleSources?.map((source, i) => (
                    <span
                      key={i}
                      className="text-xs px-2 py-1 bg-[#e8e8e8] dark:bg-[#2a2a2a] rounded-full
                        text-[#525252] dark:text-[#d4d4d4]
                        hover:bg-[#d4d4d4] dark:hover:bg-[#3a3a3a] transition-colors cursor-default"
                      title={source}
                    >
                      {source.length > 25
                        ? source.substring(0, 25) + "..."
                        : source}
                    </span>
                  ))}
                  {hasMoreSources && (
                    <button
                      onClick={() => setShowAllSources(!showAllSources)}
                      className="text-xs text-[#14b8a6] hover:text-[#0d9488] transition-colors
                        flex items-center gap-1 cursor-pointer"
                    >
                      {showAllSources ? (
                        <>
                          <ChevronUp size={12} />
                          Show less
                        </>
                      ) : (
                        <>
                          <ChevronDown size={12} />+{sources.length - 4} more
                        </>
                      )}
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
