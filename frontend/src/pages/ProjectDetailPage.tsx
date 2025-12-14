/**
 * Project Detail Page - Shows project chats and files.
 */
import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useProject } from "../hooks/useProjects";
import { useProjectChats, useCreateChat } from "../hooks/useChats";
import { useUploadDocument, useDocuments } from "../hooks/useDocuments";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { formatRelativeTime } from "../utils/formatTime";

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [replyInput, setReplyInput] = useState("");
  const [showMobileFiles, setShowMobileFiles] = useState(false);

  const { data: project, isLoading: projectLoading } = useProject(id || "");
  const { data: chats = [], isLoading: chatsLoading } = useProjectChats(
    id || null
  );

  const createChat = useCreateChat();
  const uploadDocument = useUploadDocument();

  // Fetch project documents
  const { data: documents = [], isLoading: documentsLoading } = useDocuments(
    "project",
    id || null
  );

  async function handleStartChat() {
    if (!id || !replyInput.trim()) return;

    // Check if project has documents
    if (documents.length === 0) {
      alert("Please upload files to this project before starting a new chat.");
      return;
    }

    try {
      const newChat = await createChat.mutateAsync({
        projectId: id,
        title: replyInput.trim().slice(0, 50),
      });
      navigate(`/chat/${newChat.id}`);
    } catch (error) {
      console.error("Failed to create chat:", error);
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0 || !id) return;

    // Convert FileList to array for parallel processing
    const fileArray = Array.from(files);

    try {
      // Upload all files in parallel
      const uploadPromises = fileArray.map((file) =>
        uploadDocument
          .mutateAsync({
            scopeType: "project",
            scopeId: id,
            file,
          })
          .catch((error) => {
            console.error(`Upload failed for ${file.name}:`, error);
            return { error: true, filename: file.name, message: error.message };
          })
      );

      const results = await Promise.all(uploadPromises);

      // Check for any errors
      const errors = results.filter(
        (r): r is { error: boolean; filename: string; message: string } =>
          r && typeof r === "object" && "error" in r
      );

      if (errors.length > 0) {
        const errorNames = errors.map((e) => e.filename).join(", ");
        alert(`Some uploads failed: ${errorNames}\n${errors[0].message}`);
      }
    } catch (error) {
      console.error("Upload failed:", error);
      alert("Upload failed");
    }
  }

  if (projectLoading || chatsLoading) {
    return <LoadingSpinner size="lg" text="Loading project..." />;
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-[#a3a3a3]">Project not found</div>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header - matches sidebar h-14 md:h-16 */}
        <header className="h-14 md:h-16 px-4 border-b border-[#e8e8e8] dark:border-[#3a3a3a] flex items-center justify-between">
          <div>
            <button
              onClick={() => navigate("/projects")}
              className="text-xs text-[#a3a3a3] hover:text-[#1a1a1a] dark:hover:text-white flex items-center gap-1"
            >
              ← All projects
            </button>
            <h1 className="text-lg font-bold">{project.name}</h1>
          </div>

          {/* Files button - visible on mobile/tablet when Files panel is hidden */}
          <button
            onClick={() => setShowMobileFiles(!showMobileFiles)}
            className={`lg:hidden p-2 rounded-lg transition-colors flex items-center gap-2 text-sm ${
              showMobileFiles
                ? "bg-[#e6f7f5] dark:bg-[#0f2e2b] text-[#0d9488] dark:text-[#2dd4bf]"
                : "hover:bg-neutral-100 dark:hover:bg-neutral-800 text-[#0d9488] dark:text-[#2dd4bf]"
            }`}
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <span>Files ({documents.length})</span>
          </button>
        </header>

        {/* Mobile Files Panel - collapsible */}
        {showMobileFiles && (
          <div className="lg:hidden border-b border-[#e8e8e8] dark:border-[#3a3a3a] bg-[#f8f8f8] dark:bg-[#1e1e1e] p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-[#a3a3a3]">
                Project Files
              </span>
              <label className="cursor-pointer px-3 py-1.5 bg-[#0d9488] hover:bg-[#0f766e] dark:bg-[#2dd4bf] dark:hover:bg-[#5eead4] text-white dark:text-[#0f2e2b] rounded-lg text-sm transition-colors">
                + Upload
                <input
                  type="file"
                  accept=".pdf"
                  multiple
                  onChange={handleFileUpload}
                  disabled={uploadDocument.isPending}
                  className="hidden"
                />
              </label>
            </div>
            {uploadDocument.isPending && (
              <div className="text-sm text-[#a3a3a3] mb-2 animate-pulse">
                Uploading...
              </div>
            )}
            {documents.length === 0 ? (
              <div className="text-sm text-[#a3a3a3] text-center py-4">
                No files uploaded yet
              </div>
            ) : (
              <div className="space-y-2 max-h-48 overflow-auto">
                {documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="p-2 bg-[#ffffff] dark:bg-[#242424] border border-[#e8e8e8] dark:border-[#3a3a3a] rounded-lg text-sm"
                  >
                    <div className="font-medium truncate" title={doc.filename}>
                      📄 {doc.filename}
                    </div>
                    <div className="text-xs text-[#a3a3a3] mt-0.5">
                      {new Date(doc.uploaded_at).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* New Chat Input */}
        <div className="p-4 border-b border-[#e8e8e8] dark:border-[#3a3a3a]">
          <div className="flex gap-2">
            <input
              type="text"
              value={replyInput}
              onChange={(e) => setReplyInput(e.target.value)}
              placeholder={
                documents.length === 0
                  ? "Upload files first..."
                  : "Start a new chat..."
              }
              disabled={documents.length === 0}
              className="flex-1 px-4 py-3 bg-neutral-100 dark:bg-[#242424] border border-zinc-300 dark:border-[#3a3a3a] rounded-xl text-[#1a1a1a] dark:text-[#ececec] placeholder-zinc-400 dark:placeholder-[#a3a3a3] focus:outline-none focus:border-[#0d9488] disabled:opacity-50 disabled:cursor-not-allowed"
              onKeyDown={(e) => e.key === "Enter" && handleStartChat()}
            />
            <button
              onClick={handleStartChat}
              disabled={
                !replyInput.trim() ||
                createChat.isPending ||
                documents.length === 0
              }
              className="px-4 py-3 bg-[#0d9488] hover:bg-[#14b8a6] disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl transition-colors"
            >
              ➤
            </button>
          </div>
        </div>

        {/* Chats List */}
        <div className="flex-1 overflow-auto p-4">
          {chats.length === 0 ? (
            <div className="text-center py-12 text-[#a3a3a3]">
              No chats in this project yet. Start a conversation above!
            </div>
          ) : (
            <div className="space-y-2">
              {chats.map((chat) => (
                <div
                  key={chat.id}
                  onClick={() => navigate(`/chat/${chat.id}`)}
                  className="p-4 bg-[#f8f8f8] dark:bg-[#242424] hover:bg-zinc-50 dark:hover:bg-neutral-800 border border-[#e8e8e8] dark:border-[#3a3a3a] rounded-xl cursor-pointer transition-colors"
                >
                  <h3 className="font-medium">{chat.title}</h3>
                  <p className="text-sm text-[#a3a3a3] mt-1">
                    {formatRelativeTime(chat.updated_at || chat.created_at) ||
                      "No messages yet"}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Files Panel */}
      <aside className="w-72 border-l border-[#e8e8e8] dark:border-[#3a3a3a] hidden lg:flex flex-col">
        <div className="h-14 md:h-16 px-4 border-b border-[#e8e8e8] dark:border-[#3a3a3a] flex items-center justify-between flex-shrink-0">
          <h2 className="font-semibold">Files</h2>
          <label className="cursor-pointer p-2 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-lg transition-colors">
            <span className="text-[#0d9488] dark:text-[#2dd4bf]">+</span>
            <input
              type="file"
              accept=".pdf"
              multiple
              onChange={handleFileUpload}
              disabled={uploadDocument.isPending}
              className="hidden"
            />
          </label>
        </div>

        <div className="flex-1 overflow-auto p-4">
          {uploadDocument.isPending && (
            <div className="text-sm text-[#a3a3a3] mb-4 animate-pulse">
              Uploading...
            </div>
          )}

          {documentsLoading ? (
            <div className="text-sm text-[#a3a3a3] text-center py-4">
              Loading files...
            </div>
          ) : documents.length === 0 ? (
            <div className="text-sm text-[#a3a3a3] text-center py-8">
              Upload PDFs to make them available in all project chats
            </div>
          ) : (
            <div className="space-y-3">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="p-3 bg-[#ffffff] dark:bg-[#2a2a2a] border border-[#e8e8e8] dark:border-[#3a3a3a] rounded-lg text-sm"
                >
                  <div
                    className="font-medium truncate text-[#1a1a1a] dark:text-[#ececec]"
                    title={doc.filename}
                  >
                    {doc.filename}
                  </div>
                  <div className="text-xs text-[#a3a3a3] mt-1 flex justify-between">
                    <span>
                      {new Date(doc.uploaded_at).toLocaleDateString()}
                    </span>
                    {/* Size bytes format could be added here */}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
