/**
 * Custom hooks for Chats using TanStack Query.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as api from "../api";
import type { Chat, AIModel, QualityPreset } from "../types";

export const chatKeys = {
  all: ["chats"] as const,
  standalone: ["chats", "standalone"] as const,
  byProject: (projectId: string) => ["chats", "project", projectId] as const,
  detail: (id: string) => ["chats", id] as const,
  messages: (id: string) => ["chats", id, "messages"] as const,
  documents: (id: string) => ["chats", id, "documents"] as const,
};

export function useStandaloneChats() {
  return useQuery({
    queryKey: chatKeys.standalone,
    queryFn: () => api.listChats(undefined, true),
  });
}

export function useProjectChats(projectId: string | null) {
  return useQuery({
    queryKey: projectId ? chatKeys.byProject(projectId) : chatKeys.all,
    queryFn: () => (projectId ? api.listChats(projectId) : api.listChats()),
    enabled: !!projectId,
  });
}

export function useChat(id: string | null) {
  return useQuery({
    queryKey: id ? chatKeys.detail(id) : ["chats", "none"],
    queryFn: () => (id ? api.getChat(id) : null),
    enabled: !!id,
  });
}

export function useChatMessages(chatId: string | null) {
  return useQuery({
    queryKey: chatId ? chatKeys.messages(chatId) : ["messages", "none"],
    queryFn: () => (chatId ? api.getMessages(chatId) : []),
    enabled: !!chatId,
  });
}

export function useChatDocuments(chatId: string | null, includeProject = true) {
  return useQuery({
    queryKey: chatId ? chatKeys.documents(chatId) : ["documents", "none"],
    queryFn: () => (chatId ? api.getChatDocuments(chatId, includeProject) : []),
    enabled: !!chatId,
  });
}

export function useCreateChat() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      title,
    }: {
      projectId?: string | null;
      title?: string;
    }) => api.createChat(projectId || null, title),
    onSuccess: (newChat, { projectId }) => {
      if (projectId) {
        queryClient.invalidateQueries({
          queryKey: chatKeys.byProject(projectId),
        });
      } else {
        queryClient.setQueryData<Chat[]>(chatKeys.standalone, (old) =>
          old ? [newChat, ...old] : [newChat]
        );
      }
    },
  });
}

export function useUpdateChat() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      updates,
    }: {
      id: string;
      updates: {
        title?: string;
        is_pinned?: boolean;
        model?: AIModel;
        quality_preset?: QualityPreset;
      };
    }) => api.updateChat(id, updates),
    onSuccess: (updatedChat) => {
      queryClient.setQueryData<Chat>(
        chatKeys.detail(updatedChat.id),
        updatedChat
      );
      queryClient.invalidateQueries({ queryKey: chatKeys.standalone });
    },
  });
}

export function useDeleteChat() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.deleteChat(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: chatKeys.all });
      queryClient.removeQueries({ queryKey: chatKeys.detail(id) });
    },
  });
}
