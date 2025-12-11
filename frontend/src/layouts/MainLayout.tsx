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
    <div className="flex h-screen bg-[#f8f8f8] dark:bg-[#1a1a1a] text-[#1a1a1a] dark:text-[#ececec] overflow-hidden transition-colors">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-50 w-64 bg-[#f0f0f0] dark:bg-[#1e1e1e] border-r border-[#e8e8e8] dark:border-[#2e2e2e]
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
          <div className="p-4 border-b border-[#e8e8e8] dark:border-[#2e2e2e] flex items-center justify-between">
            <h1 className="text-lg font-semibold text-[#1a1a1a] dark:text-[#ececec]">
              📚 DocuRAG
            </h1>
            <button
              onClick={() => setSidebarOpen(false)}
              className="p-1.5 rounded-lg hover:bg-[#e8e8e8] dark:hover:bg-[#2a2a2a] transition-colors"
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
              className="w-full px-4 py-2.5 bg-[#0d9488] hover:bg-[#0f766e] dark:bg-[#2dd4bf] dark:hover:bg-[#5eead4] text-white dark:text-[#0f2e2b] rounded-xl font-medium transition-all"
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
                      ? "bg-[#e6f7f5] dark:bg-[#0f2e2b] text-[#0f766e] dark:text-[#2dd4bf]"
                      : "text-[#525252] dark:text-[#a0a0a0] hover:bg-[#e8e8e8] dark:hover:bg-[#2a2a2a] hover:text-[#1a1a1a] dark:hover:text-[#ececec]"
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
            <div className="p-3 border-t border-[#e8e8e8] dark:border-[#2e2e2e]">
              <div className="flex items-center gap-3 p-2">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#0d9488] to-[#0f766e] dark:from-[#2dd4bf] dark:to-[#5eead4] flex items-center justify-center text-white dark:text-[#0f2e2b] text-sm font-medium">
                  {user.name?.charAt(0).toUpperCase() ||
                    user.email.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[#1a1a1a] dark:text-[#ececec] truncate">
                    {user.name || "User"}
                  </p>
                  <p className="text-xs text-[#a3a3a3] dark:text-[#6b6b6b] truncate">
                    {user.email}
                  </p>
                </div>
              </div>
              <div className="flex gap-2 mt-2">
                <button
                  onClick={() => navigate("/settings")}
                  className="flex-1 px-3 py-1.5 text-xs text-[#525252] dark:text-[#a0a0a0] hover:text-[#1a1a1a] dark:hover:text-[#ececec] hover:bg-[#e8e8e8] dark:hover:bg-[#2a2a2a] rounded-lg transition-colors"
                >
                  ⚙️ Settings
                </button>
                <button
                  onClick={logout}
                  className="flex-1 px-3 py-1.5 text-xs text-[#525252] dark:text-[#a0a0a0] hover:text-[#dc2626] dark:hover:text-[#f87171] hover:bg-[#fdeaea] dark:hover:bg-[#2e1616] rounded-lg transition-colors"
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
          <header className="flex items-center gap-3 px-4 py-3 bg-[#f0f0f0]/90 dark:bg-[#1e1e1e]/90 backdrop-blur-md border-b border-[#e8e8e8] dark:border-[#2e2e2e]">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 rounded-lg hover:bg-[#e8e8e8] dark:hover:bg-[#2a2a2a] transition-colors"
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
