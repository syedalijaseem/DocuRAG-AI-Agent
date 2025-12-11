/**
 * Custom hooks for Projects using TanStack Query.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as api from "../api";
import type { Project } from "../types";

export const projectKeys = {
  all: ["projects"] as const,
  detail: (id: string) => ["projects", id] as const,
};

export function useProjects() {
  return useQuery({
    queryKey: projectKeys.all,
    queryFn: api.listProjects,
  });
}

export function useProject(id: string) {
  return useQuery({
    queryKey: projectKeys.detail(id),
    queryFn: () => api.getProject(id),
    enabled: !!id,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (name: string) => api.createProject(name),
    onSuccess: (newProject) => {
      queryClient.setQueryData<Project[]>(projectKeys.all, (old) =>
        old ? [newProject, ...old] : [newProject]
      );
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.deleteProject(id),
    onSuccess: (_, id) => {
      queryClient.setQueryData<Project[]>(projectKeys.all, (old) =>
        old?.filter((p) => p.id !== id)
      );
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}
