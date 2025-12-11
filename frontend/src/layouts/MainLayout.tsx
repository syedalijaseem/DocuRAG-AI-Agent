/**
 * Main layout with collapsible sidebar.
 */
import { useEffect, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useUI } from "../context/UIContext";

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const { sidebarOpen, setSidebarOpen } = useUI();

  // Close sidebar on mobile after navigation
  useEffect(() => {
    if (window.matchMedia("(max-width: 1023px)").matches) {
      setSidebarOpen(false);
    }
  }, [location.pathname, setSidebarOpen]);

  const navItems = [
    { path: "/", label: "Chats", icon: "💬" },
    { path: "/projects", label: "Projects", icon: "📁" },
  ];

  return (
    <div className="flex h-screen bg-zinc-950 text-white overflow-hidden">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-50 w-64 bg-zinc-900 border-r border-zinc-800
          transform transition-transform duration-300 ease-in-out
          ${
            sidebarOpen
              ? "translate-x-0 lg:relative"
              : "-translate-x-full lg:absolute"
          }
        `}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
            <h1 className="text-lg font-semibold">📚 DocuRAG</h1>
            <button
              onClick={() => setSidebarOpen(false)}
              className="p-1.5 rounded-lg hover:bg-zinc-800 transition-colors"
              title="Close sidebar (Ctrl+B)"
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
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* New Chat Button */}
          <div className="p-3">
            <button
              onClick={() => navigate("/")}
              className="w-full px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-xl font-medium transition-all shadow-lg shadow-indigo-500/25"
            >
              + New Chat
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-2 space-y-1">
            {navItems.map((item) => (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`
                  w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors
                  ${
                    location.pathname === item.path
                      ? "bg-zinc-800 text-white"
                      : "text-zinc-400 hover:bg-zinc-800/50 hover:text-white"
                  }
                `}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            ))}
          </nav>

          {/* User Section */}
          {user && (
            <div className="p-3 border-t border-zinc-800">
              <div className="flex items-center gap-3 p-2">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-orange-500 to-pink-500 flex items-center justify-center text-white text-sm font-medium">
                  {user.name?.charAt(0).toUpperCase() ||
                    user.email.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">
                    {user.name || "User"}
                  </p>
                  <p className="text-xs text-zinc-500 truncate">{user.email}</p>
                </div>
              </div>
              <div className="flex gap-2 mt-2">
                <button
                  onClick={() => navigate("/settings")}
                  className="flex-1 px-3 py-1.5 text-xs text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors"
                >
                  ⚙️ Settings
                </button>
                <button
                  onClick={logout}
                  className="flex-1 px-3 py-1.5 text-xs text-zinc-400 hover:text-red-400 hover:bg-zinc-800 rounded-lg transition-colors"
                >
                  🚪 Logout
                </button>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Header (when sidebar closed) */}
        {!sidebarOpen && (
          <header className="flex items-center gap-3 px-4 py-3 bg-zinc-900/80 backdrop-blur-md border-b border-zinc-800">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 rounded-lg hover:bg-zinc-800 transition-colors"
              title="Open sidebar (Ctrl+B)"
            >
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            </button>
            <h1 className="text-lg font-semibold">📚 DocuRAG</h1>
          </header>
        )}

        {/* Page Content */}
        <div className="flex-1 overflow-hidden">{children}</div>
      </main>
    </div>
  );
}
