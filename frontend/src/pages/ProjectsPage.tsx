/**
 * Projects Page - Grid of projects.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  useProjects,
  useCreateProject,
  useDeleteProject,
} from "../hooks/useProjects";

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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-[#a3a3a3]">Loading projects...</div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-6xl mx-auto p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Projects</h1>
          <button
            onClick={() => setShowNewModal(true)}
            className="px-4 py-2 bg-gradient-to-r from-teal-600 to-teal-700 hover:from-teal-500 hover:to-teal-600 text-white rounded-xl font-medium transition-all"
          >
            + New Project
          </button>
        </div>

        {/* Search */}
        <div className="mb-6">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search projects..."
            className="w-full px-4 py-3 bg-[#f8f8f8] dark:bg-[#242424] border border-zinc-300 dark:border-[#3a3a3a] rounded-xl text-[#1a1a1a] dark:text-[#ececec] placeholder-zinc-400 dark:placeholder-[#a3a3a3] focus:outline-none focus:border-[#0d9488]"
          />
        </div>

        {/* Projects Grid */}
        {filteredProjects.length === 0 ? (
          <div className="text-center py-12 text-[#a3a3a3]">
            {search
              ? "No projects match your search"
              : "No projects yet. Create one!"}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredProjects.map((project) => (
              <div
                key={project.id}
                onClick={() => navigate(`/projects/${project.id}`)}
                className="group relative p-5 bg-[#f8f8f8] dark:bg-[#242424] hover:bg-zinc-50 dark:hover:bg-neutral-800 border border-[#e8e8e8] dark:border-[#3a3a3a] rounded-2xl cursor-pointer transition-all"
              >
                <h3 className="font-semibold text-lg mb-2">{project.name}</h3>
                <p className="text-sm text-[#a3a3a3]">
                  Updated {new Date(project.updated_at).toLocaleDateString()}
                </p>

                {/* Delete button */}
                <button
                  onClick={(e) => handleDeleteProject(project.id, e)}
                  className="absolute top-3 right-3 p-2 opacity-0 group-hover:opacity-100 hover:bg-red-100 dark:hover:bg-red-900/50 text-red-500 dark:text-red-400 rounded-lg transition-all"
                  title="Delete project"
                >
                  🗑️
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* New Project Modal */}
      {showNewModal && (
        <div className="fixed inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-[#f8f8f8] dark:bg-[#242424] border border-[#e8e8e8] dark:border-[#3a3a3a] rounded-2xl p-6 w-full max-w-md mx-4">
            <h2 className="text-xl font-semibold mb-4 text-[#1a1a1a] dark:text-[#ececec]">
              New Project
            </h2>
            <input
              type="text"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              placeholder="Project name"
              autoFocus
              className="w-full px-4 py-3 bg-neutral-100 dark:bg-[#242424] border border-zinc-300 dark:border-[#3a3a3a] rounded-xl text-[#1a1a1a] dark:text-[#ececec] placeholder-zinc-400 dark:placeholder-[#a3a3a3] focus:outline-none focus:border-[#0d9488] mb-4"
              onKeyDown={(e) => e.key === "Enter" && handleCreateProject()}
            />
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowNewModal(false)}
                className="px-4 py-2 text-zinc-600 dark:text-[#a0a0a0] hover:text-[#1a1a1a] dark:hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateProject}
                disabled={!newProjectName.trim() || createProject.isPending}
                className="px-4 py-2 bg-[#0d9488] hover:bg-[#14b8a6] text-white rounded-xl font-medium transition-colors disabled:opacity-50"
              >
                {createProject.isPending ? "Creating..." : "Create"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
