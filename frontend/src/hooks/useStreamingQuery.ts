/**
 * useStreamingQuery - Hook for streaming LLM responses via SSE
 */
import { useState, useCallback } from "react";

export type StreamingStage =
  | "idle"
  | "searching"
  | "generating"
  | "streaming"
  | "done"
  | "error";

interface StreamingState {
  isLoading: boolean;
  stage: StreamingStage;
  sources: string[];
  scores: number[];
  content: string;
  error: string | null;
  tokensUsed: number;
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export function useStreamingQuery(chatId: string) {
  const [state, setState] = useState<StreamingState>({
    isLoading: false,
    stage: "idle",
    sources: [],
    scores: [],
    content: "",
    error: null,
    tokensUsed: 0,
  });

  const sendMessage = useCallback(
    async (
      question: string,
      history: Array<{ role: string; content: string }>,
      topK: number = 10
    ) => {
      setState((prev) => ({
        ...prev,
        isLoading: true,
        stage: "searching",
        content: "",
        sources: [],
        scores: [],
        error: null,
      }));

      try {
        const response = await fetch(`${API_BASE}/chat/${chatId}/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ question, history, top_k: topK }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || "Stream request failed");
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) throw new Error("No reader available");

        let buffer = "";
        let currentEvent = "chunk"; // Default to chunk for backward compat

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || ""; // Keep last incomplete line

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue; // Skip empty lines

            if (trimmed.startsWith("event:")) {
              currentEvent = trimmed.slice(6).trim();
            } else if (trimmed.startsWith("data:")) {
              const dataStr = trimmed.slice(5).trim();
              if (!dataStr) continue;

              try {
                const data = JSON.parse(dataStr);

                // Handle based on event type
                switch (currentEvent) {
                  case "status":
                    if (data.stage) {
                      setState((prev) => ({
                        ...prev,
                        stage: data.stage as StreamingStage,
                      }));
                    }
                    break;

                  case "sources":
                    setState((prev) => ({
                      ...prev,
                      sources: data.sources || [],
                      scores: data.scores || [],
                      stage: "generating",
                    }));
                    break;

                  case "chunk":
                    if (data.content !== undefined && data.content !== null) {
                      setState((prev) => ({
                        ...prev,
                        content: prev.content + data.content,
                        stage: "streaming",
                      }));
                    }
                    break;

                  case "done":
                    // Use full_response from backend if available, otherwise keep accumulated
                    setState((prev) => ({
                      ...prev,
                      content: data.full_response || prev.content,
                      stage: "done",
                      isLoading: false,
                      tokensUsed: data.tokens_used || 0,
                    }));
                    break;

                  case "error":
                    setState((prev) => ({
                      ...prev,
                      stage: "error",
                      error: data.error || "Unknown error",
                      isLoading: false,
                    }));
                    break;
                }

                // Reset to default after processing
                currentEvent = "chunk";
              } catch {
                // Ignore JSON parse errors
              }
            }
          }
        }
      } catch (error) {
        setState((prev) => ({
          ...prev,
          stage: "error",
          error: error instanceof Error ? error.message : "Unknown error",
          isLoading: false,
        }));
      }
    },
    [chatId]
  );

  const reset = useCallback(() => {
    setState({
      isLoading: false,
      stage: "idle",
      sources: [],
      scores: [],
      content: "",
      error: null,
      tokensUsed: 0,
    });
  }, []);

  return { ...state, sendMessage, reset };
}
