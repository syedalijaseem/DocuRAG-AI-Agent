/**
 * Projects Page - Grid of projects with modern styling and Lucide icons.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Folder, FolderPlus, Plus, Search, Trash2, X } from "lucide-react";
import {
  useProjects,
  useCreateProject,
  useDeleteProject,
} from "../hooks/useProjects";
import { formatRelativeTime } from "../utils/formatTime";

export function ProjectsPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [showNewModal, setShowNewModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");

  const { data: projects = [], isLoading } = useProjects();
  const createProject = useCreateProject();
  const deleteProject = useDeleteProject();

  const filteredProjects = projects.filter((project) =>
    project.name.toLowerCase().includes(search.toLowerCase())
  );

  // Sort by updated date
  const sortedProjects = [...filteredProjects].sort(
    (a, b) =>
      new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  );

  async function handleCreateProject() {
    if (!newProjectName.trim()) return;
    try {
      const newProject = await createProject.mutateAsync(newProjectName.trim());
      setNewProjectName("");
      setShowNewModal(false);
      navigate(`/projects/${newProject.id}`);
    } catch (error) {
      console.error("Failed to create project:", error);
    }
  }

  async function handleDeleteProject(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (confirm("Delete this project and all its chats?")) {
      deleteProject.mutate(id);
    }
  }

  // Format relative date - use utility function
  function formatDate(dateStr: string | undefined) {
    if (!dateStr) return "Unknown";
    const formatted = formatRelativeTime(dateStr);
    return formatted || "Unknown";
  }

  if (isLoading) {
    return (
      <div className="h-full overflow-auto">
        <div className="max-w-5xl mx-auto p-6">
          {/* Loading Skeleton */}
          <div className="animate-pulse space-y-6">
            <div className="flex justify-between">
              <div className="h-8 bg-[#e8e8e8] dark:bg-[#2a2a2a] rounded w-32" />
              <div className="h-10 bg-[#e8e8e8] dark:bg-[#2a2a2a] rounded-xl w-36" />
            </div>
            <div className="h-12 bg-[#e8e8e8] dark:bg-[#2a2a2a] rounded-xl" />
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div
                  key={i}
                  className="p-5 bg-[#f0f0f0] dark:bg-[#1e1e1e] rounded-2xl"
                >
                  <div className="flex gap-4">
                    <div className="w-12 h-12 bg-[#e8e8e8] dark:bg-[#2a2a2a] rounded-xl" />
                    <div className="flex-1 space-y-2">
                      <div className="h-5 bg-[#e8e8e8] dark:bg-[#2a2a2a] rounded w-3/4" />
                      <div className="h-4 bg-[#e8e8e8] dark:bg-[#2a2a2a] rounded w-1/2" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-5xl mx-auto p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-[#1a1a1a] dark:text-[#ececec]">
            Projects
          </h1>
          <button
            onClick={() => setShowNewModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-[#0d9488] hover:bg-[#0f766e] dark:bg-[#2dd4bf] dark:hover:bg-[#5eead4] text-white dark:text-[#0f2e2b] rounded-xl font-medium transition-all"
          >
            <Plus className="w-5 h-5" />
            <span>New Project</span>
          </button>
        </div>

        {/* Search */}
        <div className="relative mb-6">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#a3a3a3]" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search projects..."
            className="w-full pl-12 pr-4 py-3 bg-[#ffffff] dark:bg-[#242424] border border-[#e8e8e8] dark:border-[#3a3a3a] rounded-xl text-[#1a1a1a] dark:text-[#ececec] placeholder-[#a3a3a3] focus:outline-none focus:border-[#0d9488] dark:focus:border-[#2dd4bf] transition-colors"
          />
        </div>

        {/* Project Count */}
        <div className="text-sm text-[#737373] dark:text-[#a0a0a0] mb-4">
          {sortedProjects.length} project
          {sortedProjects.length !== 1 ? "s" : ""}
        </div>

        {/* Projects Grid */}
        {sortedProjects.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-16 h-16 flex items-center justify-center bg-[#f0f0f0] dark:bg-[#242424] rounded-2xl mb-4">
              <FolderPlus className="w-8 h-8 text-[#a3a3a3] dark:text-[#6b6b6b]" />
            </div>
            <h3 className="text-lg font-semibold text-[#1a1a1a] dark:text-[#ececec] mb-2">
              {search ? "No projects found" : "No projects yet"}
            </h3>
            <p className="text-sm text-[#737373] dark:text-[#a0a0a0] max-w-xs">
              {search
                ? "Try a different search term"
                : "Create a project to organize your chats and documents"}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sortedProjects.map((project) => (
              <div
                key={project.id}
                onClick={() => navigate(`/projects/${project.id}`)}
                className="group relative flex gap-4 p-4 bg-[#ffffff] dark:bg-[#1e1e1e] hover:bg-[#f8f8f8] dark:hover:bg-[#242424] border border-[#e8e8e8] dark:border-[#3a3a3a] hover:border-[#0d9488] dark:hover:border-[#2dd4bf]/40 rounded-2xl cursor-pointer transition-all"
              >
                {/* Icon with gradient */}
                <div className="w-12 h-12 flex items-center justify-center bg-gradient-to-br from-[#e6f7f5] to-[#f0f0f0] dark:from-[#0f2e2b] dark:to-[#1e1e1e] rounded-xl flex-shrink-0">
                  <Folder className="w-6 h-6 text-[#0d9488] dark:text-[#2dd4bf]" />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-[#1a1a1a] dark:text-[#ececec] truncate mb-1">
                    {project.name}
                  </h3>
                  <p className="text-sm text-[#737373] dark:text-[#a0a0a0]">
                    {formatDate(project.updated_at || project.created_at)}
                  </p>
                </div>

                {/* Delete button */}
                <button
                  onClick={(e) => handleDeleteProject(project.id, e)}
                  className="absolute top-3 right-3 p-2 opacity-0 group-hover:opacity-100 hover:bg-[#fdeaea] dark:hover:bg-[#2e1616] text-[#737373] dark:text-[#a0a0a0] hover:text-[#dc2626] dark:hover:text-[#f87171] rounded-lg transition-all"
                  title="Delete project"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* New Project Modal */}
      {showNewModal && (
        <div className="fixed inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-[#ffffff] dark:bg-[#1e1e1e] border border-[#e8e8e8] dark:border-[#3a3a3a] rounded-2xl p-6 w-full max-w-md mx-4 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-[#1a1a1a] dark:text-[#ececec]">
                New Project
              </h2>
              <button
                onClick={() => setShowNewModal(false)}
                className="p-2 hover:bg-[#f0f0f0] dark:hover:bg-[#2a2a2a] rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-[#737373] dark:text-[#a0a0a0]" />
              </button>
            </div>
            <input
              type="text"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              placeholder="Project name"
              autoFocus
              className="w-full px-4 py-3 bg-[#f8f8f8] dark:bg-[#242424] border border-[#e8e8e8] dark:border-[#3a3a3a] rounded-xl text-[#1a1a1a] dark:text-[#ececec] placeholder-[#a3a3a3] focus:outline-none focus:border-[#0d9488] dark:focus:border-[#2dd4bf] mb-4 transition-colors"
              onKeyDown={(e) => e.key === "Enter" && handleCreateProject()}
            />
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowNewModal(false)}
                className="px-4 py-2.5 text-[#737373] dark:text-[#a0a0a0] hover:text-[#1a1a1a] dark:hover:text-white hover:bg-[#f0f0f0] dark:hover:bg-[#2a2a2a] rounded-xl transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateProject}
                disabled={!newProjectName.trim() || createProject.isPending}
                className="flex items-center gap-2 px-4 py-2.5 bg-[#0d9488] hover:bg-[#0f766e] dark:bg-[#2dd4bf] dark:hover:bg-[#5eead4] text-white dark:text-[#0f2e2b] rounded-xl font-medium transition-colors disabled:opacity-50"
              >
                {createProject.isPending ? (
                  "Creating..."
                ) : (
                  <>
                    <FolderPlus className="w-4 h-4" />
                    <span>Create</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
