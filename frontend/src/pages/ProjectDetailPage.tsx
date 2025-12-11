/**
 * Project Detail Page - Shows project chats and files.
 */
import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useProject } from "../hooks/useProjects";
import { useProjectChats, useCreateChat } from "../hooks/useChats";
import { useUploadDocument, useDocuments } from "../hooks/useDocuments";

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [replyInput, setReplyInput] = useState("");

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
    try {
      const newChat = await createChat.mutateAsync({
        projectId: id,
        title: replyInput.trim().slice(0, 50),
      });
      navigate(`/chat/${newChat.id}?message=${encodeURIComponent(replyInput)}`);
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
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-zinc-500">Loading project...</div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-zinc-500">Project not found</div>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="p-4 border-b border-zinc-800">
          <button
            onClick={() => navigate("/projects")}
            className="text-sm text-zinc-500 hover:text-white mb-2 flex items-center gap-1"
          >
            ← All projects
          </button>
          <h1 className="text-xl font-bold">{project.name}</h1>
        </header>

        {/* Reply Input */}
        <div className="p-4 border-b border-zinc-800">
          <div className="flex gap-2">
            <input
              type="text"
              value={replyInput}
              onChange={(e) => setReplyInput(e.target.value)}
              placeholder="Reply..."
              className="flex-1 px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
              onKeyDown={(e) => e.key === "Enter" && handleStartChat()}
            />
            <button
              onClick={handleStartChat}
              disabled={!replyInput.trim() || createChat.isPending}
              className="px-4 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl transition-colors"
            >
              ➤
            </button>
          </div>
        </div>

        {/* Chats List */}
        <div className="flex-1 overflow-auto p-4">
          {chats.length === 0 ? (
            <div className="text-center py-12 text-zinc-500">
              No chats in this project yet. Start a conversation above!
            </div>
          ) : (
            <div className="space-y-2">
              {chats.map((chat) => (
                <div
                  key={chat.id}
                  onClick={() => navigate(`/chat/${chat.id}`)}
                  className="p-4 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded-xl cursor-pointer transition-colors"
                >
                  <h3 className="font-medium">{chat.title}</h3>
                  <p className="text-sm text-zinc-500 mt-1">
                    Last message{" "}
                    {new Date(chat.updated_at).toLocaleDateString()}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Files Panel */}
      <aside className="w-72 border-l border-zinc-800 hidden lg:flex flex-col">
        <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
          <h2 className="font-semibold">Files</h2>
          <label className="cursor-pointer p-2 hover:bg-zinc-800 rounded-lg transition-colors">
            <span className="text-indigo-400">+</span>
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
            <div className="text-sm text-zinc-500 mb-4 animate-pulse">
              Uploading...
            </div>
          )}

          {documentsLoading ? (
            <div className="text-sm text-zinc-500 text-center py-4">
              Loading files...
            </div>
          ) : documents.length === 0 ? (
            <div className="text-sm text-zinc-500 text-center py-8">
              Upload PDFs to make them available in all project chats
            </div>
          ) : (
            <div className="space-y-3">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="p-3 bg-zinc-900 border border-zinc-700/50 rounded-lg text-sm"
                >
                  <div className="font-medium truncate" title={doc.filename}>
                    {doc.filename}
                  </div>
                  <div className="text-xs text-zinc-500 mt-1 flex justify-between">
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
