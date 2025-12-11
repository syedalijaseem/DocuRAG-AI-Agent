/**
 * Custom hooks for document upload and management.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as api from "../api";
import type { ScopeType } from "../types";
import { chatKeys } from "./useChats";

export const documentKeys = {
  all: ["documents"] as const,
  byScope: (scopeType: ScopeType, scopeId: string) =>
    ["documents", scopeType, scopeId] as const,
};

export function useDocuments(scopeType: ScopeType, scopeId: string | null) {
  return useQuery({
    queryKey: scopeId
      ? documentKeys.byScope(scopeType, scopeId)
      : ["documents", "none"],
    queryFn: () =>
      scopeId ? api.listDocuments(scopeType, scopeId) : Promise.resolve([]),
    enabled: !!scopeId,
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      scopeType,
      scopeId,
      file,
    }: {
      scopeType: ScopeType;
      scopeId: string;
      file: File;
    }) => {
      // Upload document
      const result = await api.uploadDocument(scopeType, scopeId, file);

      // Trigger ingestion (non-blocking)
      try {
        const eventIds = await api.sendIngestEvent(
          result.document.s3_key,
          result.document.filename,
          scopeType,
          scopeId,
          result.document.id
        );

        // Wait for ingestion in background
        if (eventIds.length > 0) {
          api.waitForRunOutput(eventIds[0]).catch((err) => {
            console.warn("Ingestion still processing:", err);
          });
        }
      } catch (err) {
        console.error("Failed to trigger ingestion:", err);
        // We don't throw here so the document still shows as uploaded
      }

      return result;
    },
    onSuccess: (_, { scopeType, scopeId }) => {
      // Invalidate documents for this scope
      if (scopeType === "chat") {
        queryClient.invalidateQueries({
          queryKey: chatKeys.documents(scopeId),
        });
      }
      // Also invalidate general document list for this scope
      queryClient.invalidateQueries({
        queryKey: documentKeys.byScope(scopeType, scopeId),
      });
    },
  });
}
