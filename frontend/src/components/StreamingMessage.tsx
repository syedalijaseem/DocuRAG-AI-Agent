/**
 * StreamingMessage - Displays streaming response with stages
 */
import { Search, FileText, Sparkles } from "lucide-react";
import { MessageSkeleton } from "./MessageSkeleton";
import type { StreamingStage } from "../hooks/useStreamingQuery";

interface Props {
  stage: StreamingStage;
  content: string;
  sources: string[];
  error: string | null;
}

export function StreamingMessage({ stage, content, sources, error }: Props) {
  if (stage === "idle") return null;

  if (stage === "error") {
    return (
      <div className="max-w-[85%] p-4 rounded-2xl mr-auto bg-red-500/10 border border-red-500/20 text-red-400">
        Error: {error}
      </div>
    );
  }

  return (
    <div className="max-w-[85%] p-4 rounded-2xl mr-auto bg-[#f8f8f8] dark:bg-[#242424] border border-[#e8e8e8] dark:border-[#3a3a3a]">
      {/* Stage indicator */}
      {stage === "searching" && (
        <div className="flex items-center gap-3 text-[#737373] dark:text-[#a0a0a0] mb-4">
          <Search size={18} className="animate-pulse" />
          <span>Searching your documents...</span>
        </div>
      )}

      {stage === "generating" && !content && (
        <div className="flex items-center gap-3 text-[#737373] dark:text-[#a0a0a0] mb-4">
          <FileText size={18} className="animate-pulse" />
          <span>Analyzing {sources.length} passages...</span>
        </div>
      )}

      {/* Sources badges - show as soon as available */}
      {sources.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          <span className="text-[#737373] dark:text-[#a0a0a0] text-xs">
            Sources:
          </span>
          {sources.slice(0, 5).map((source, i) => (
            <span
              key={i}
              className="text-xs px-2 py-1 bg-[#e8e8e8] dark:bg-[#3a3a3a] rounded-full text-[#525252] dark:text-[#a0a0a0]"
            >
              {source}
            </span>
          ))}
          {sources.length > 5 && (
            <span className="text-xs text-[#737373] dark:text-[#a0a0a0]">
              +{sources.length - 5} more
            </span>
          )}
        </div>
      )}

      {/* Content area */}
      {(stage === "searching" || (stage === "generating" && !content)) && (
        <MessageSkeleton />
      )}

      {content && (
        <div className="whitespace-pre-wrap">
          {content}
          {stage === "streaming" && (
            <span className="inline-block w-2 h-4 ml-1 bg-[#14b8a6] animate-pulse" />
          )}
        </div>
      )}

      {stage === "done" && content && (
        <div className="mt-3 pt-3 border-t border-[#e8e8e8] dark:border-[#3a3a3a]">
          <div className="flex items-center gap-2 text-xs text-[#737373] dark:text-[#a0a0a0]">
            <Sparkles size={12} />
            <span>Response complete</span>
          </div>
        </div>
      )}
    </div>
  );
}
