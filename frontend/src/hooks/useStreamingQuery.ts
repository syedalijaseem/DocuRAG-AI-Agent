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
        let currentEvent = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              currentEvent = line.slice(7).trim();
              continue;
            }

            if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.slice(6));

                if (currentEvent === "status" || data.stage) {
                  setState((prev) => ({
                    ...prev,
                    stage: data.stage as StreamingStage,
                  }));
                }

                if (currentEvent === "sources" || data.sources) {
                  setState((prev) => ({
                    ...prev,
                    sources: data.sources || [],
                    scores: data.scores || [],
                    stage: "generating",
                  }));
                }

                if (currentEvent === "chunk" || data.content) {
                  setState((prev) => ({
                    ...prev,
                    content: prev.content + (data.content || ""),
                    stage: "streaming",
                  }));
                }

                if (currentEvent === "done" || data.full_response) {
                  setState((prev) => ({
                    ...prev,
                    stage: "done",
                    isLoading: false,
                    tokensUsed: data.tokens_used || 0,
                  }));
                }

                if (currentEvent === "error" || data.error) {
                  setState((prev) => ({
                    ...prev,
                    stage: "error",
                    error: data.error,
                    isLoading: false,
                  }));
                }
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
