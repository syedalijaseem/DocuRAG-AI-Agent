/**
 * Main layout with responsive sidebar:
 * - Mobile: Slide-over drawer with backdrop (hidden by default)
 * - Tablet: Collapsed (64px icons) with hover expand to 256px
 * - Desktop: Full 256px, can be toggled closed with Ctrl+B
 */
import { useEffect, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  MessageSquare,
  Folder,
  Plus,
  Settings,
  LogOut,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useUI } from "../context/UIContext";
import logo from "../assets/logo.png";

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const {
    sidebarOpen,
    setSidebarOpen,
    sidebarExpanded,
    setSidebarExpanded,
    isMobile,
    isTablet,
    isDesktop,
  } = useUI();

  // Close sidebar on mobile after navigation
  useEffect(() => {
    if (isMobile && sidebarOpen) {
      setSidebarOpen(false);
    }
  }, [location.pathname]);

  const navItems = [
    { path: "/", label: "Chats", icon: MessageSquare },
    { path: "/projects", label: "Projects", icon: Folder },
  ];

  // Sidebar visibility and width logic
  const isSidebarVisible = isMobile ? sidebarOpen : true; // Always visible on tablet/desktop
  // On desktop: sidebarOpen controls expanded/collapsed
  // On tablet: sidebarExpanded (hover) controls it
  const isCollapsed = isTablet
    ? !sidebarExpanded
    : isDesktop
    ? !sidebarOpen
    : false;
  const sidebarWidth = isCollapsed ? "w-16" : "w-64";
  const showLabels = !isCollapsed;

  return (
    <div className="flex h-dvh bg-[#f8f8f8] dark:bg-[#1a1a1a] text-[#1a1a1a] dark:text-[#ececec] overflow-hidden">
      {/* Mobile backdrop */}
      {isMobile && sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      {isSidebarVisible && (
        <aside
          onMouseEnter={() => isTablet && setSidebarExpanded(true)}
          onMouseLeave={() => isTablet && setSidebarExpanded(false)}
          className={`
            ${
              isMobile
                ? "fixed inset-y-0 left-0 z-50 w-[280px]"
                : `relative flex-shrink-0 ${sidebarWidth}`
            }
            bg-[#f0f0f0] dark:bg-[#1e1e1e] 
            border-r border-[#e8e8e8] dark:border-[#2e2e2e]
            flex flex-col
            transition-all duration-200 ease-out
          `}
        >
          {/* Sidebar Header */}
          <div
            className={`h-14 md:h-16 flex items-center border-b border-[#e8e8e8] dark:border-[#2e2e2e] flex-shrink-0 ${
              showLabels ? "justify-between px-4" : "justify-center px-2"
            }`}
          >
            {/* Logo - always shown on tablet, shown on desktop when expanded */}
            {showLabels && (
              <div className="flex items-center gap-2.5">
                <img
                  src={logo}
                  alt="Querious"
                  className="w-7 h-7 object-contain mt-0.5"
                />
                <h1 className="text-xl font-bold text-[#1a1a1a] dark:text-[#ececec] whitespace-nowrap leading-none">
                  Querious
                </h1>
              </div>
            )}
            {/* Collapsed state: Logo with hover to show expand button */}
            {!showLabels && (
              <button
                onClick={() => isDesktop && setSidebarOpen(true)}
                className="group p-2 rounded-lg hover:bg-[#e8e8e8] dark:hover:bg-[#2a2a2a] transition-colors"
                title={isDesktop ? "Expand sidebar (Ctrl+B)" : ""}
              >
                {/* Logo - visible by default */}
                <img
                  src={logo}
                  alt="Querious"
                  className="w-6 h-6 group-hover:hidden"
                />
                {/* Expand icon - visible on hover (desktop only) */}
                {isDesktop && (
                  <ChevronsRight className="w-5 h-5 hidden group-hover:block" />
                )}
              </button>
            )}
            {/* Mobile close button */}
            {isMobile && (
              <button
                onClick={() => setSidebarOpen(false)}
                className="p-2 rounded-lg hover:bg-[#e8e8e8] dark:hover:bg-[#2a2a2a] transition-colors"
                title="Close sidebar"
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
            )}
            {/* Desktop collapse button (when expanded) */}
            {isDesktop && showLabels && (
              <button
                onClick={() => setSidebarOpen(false)}
                className="p-2 rounded-lg hover:bg-[#e8e8e8] dark:hover:bg-[#2a2a2a] transition-colors"
                title="Collapse sidebar (Ctrl+B)"
              >
                <ChevronsLeft className="w-5 h-5" />
              </button>
            )}
          </div>

          {/* New Chat Button */}
          <div className="p-3 flex-shrink-0">
            <button
              onClick={() => {
                navigate("/");
                if (isMobile) setSidebarOpen(false);
              }}
              className={`
                ${showLabels ? "w-full px-4" : "w-10 mx-auto justify-center"} 
                py-2.5 flex items-center gap-2
                bg-[#0d9488] hover:bg-[#0f766e] dark:bg-[#2dd4bf] dark:hover:bg-[#5eead4] 
                text-white dark:text-[#0f2e2b] 
                rounded-xl font-medium transition-all
              `}
            >
              <Plus className="w-5 h-5" />
              {showLabels && <span>New Chat</span>}
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
            {navItems.map((item) => (
              <button
                key={item.path}
                onClick={() => {
                  navigate(item.path);
                  if (isMobile) setSidebarOpen(false);
                }}
                className={`
                  ${showLabels ? "w-full px-3" : "w-10 mx-auto justify-center"}
                  flex items-center gap-3 py-2.5 rounded-xl text-sm font-medium transition-colors
                  ${
                    location.pathname === item.path
                      ? "bg-[#e6f7f5] dark:bg-[#0f2e2b] text-[#0f766e] dark:text-[#2dd4bf]"
                      : "text-[#525252] dark:text-[#a0a0a0] hover:bg-[#e8e8e8] dark:hover:bg-[#2a2a2a] hover:text-[#1a1a1a] dark:hover:text-[#ececec]"
                  }
                `}
                title={!showLabels ? item.label : undefined}
              >
                <item.icon className="w-5 h-5" />
                {showLabels && <span>{item.label}</span>}
              </button>
            ))}
          </nav>

          {/* User Section - min-h matches chat input footer */}
          {user && (
            <div className="p-4 border-t border-[#e8e8e8] dark:border-[#2e2e2e] flex-shrink-0">
              <div
                className={`flex items-center ${
                  showLabels ? "gap-3 p-2" : "justify-center p-1"
                }`}
              >
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#0d9488] to-[#0f766e] dark:from-[#2dd4bf] dark:to-[#5eead4] flex items-center justify-center text-white dark:text-[#0f2e2b] text-sm font-medium flex-shrink-0">
                  {user.name?.charAt(0).toUpperCase() ||
                    user.email.charAt(0).toUpperCase()}
                </div>
                {showLabels && (
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[#1a1a1a] dark:text-[#ececec] truncate">
                      {user.name || "User"}
                    </p>
                    <p className="text-xs text-[#a3a3a3] dark:text-[#6b6b6b] truncate">
                      {user.email}
                    </p>
                  </div>
                )}
              </div>
              {showLabels && (
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={() => {
                      navigate("/settings");
                      if (isMobile) setSidebarOpen(false);
                    }}
                    className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs text-[#525252] dark:text-[#a0a0a0] hover:text-[#1a1a1a] dark:hover:text-[#ececec] hover:bg-[#e8e8e8] dark:hover:bg-[#2a2a2a] rounded-lg transition-colors"
                  >
                    <Settings className="w-3.5 h-3.5" />
                    <span>Settings</span>
                  </button>
                  <button
                    onClick={logout}
                    className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs text-[#525252] dark:text-[#a0a0a0] hover:text-[#dc2626] dark:hover:text-[#f87171] hover:bg-[#fdeaea] dark:hover:bg-[#2e1616] rounded-lg transition-colors"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>Logout</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </aside>
      )}

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header - only on mobile, or when sidebar closed on mobile */}
        {isMobile && !sidebarOpen && (
          <header className="h-14 flex items-center gap-3 px-4 bg-[#f8f8f8] dark:bg-[#1a1a1a] border-b border-[#e8e8e8] dark:border-[#2e2e2e] flex-shrink-0">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 -ml-2 rounded-lg hover:bg-[#e8e8e8] dark:hover:bg-[#2a2a2a] transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
              title="Open sidebar"
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
            <div className="flex items-center gap-2">
              <img src={logo} alt="Querious" className="w-6 h-6" />
              <h1 className="text-lg font-semibold">Querious</h1>
            </div>
          </header>
        )}

        {/* Page Content */}
        <div className="flex-1 overflow-hidden">{children}</div>
      </main>
    </div>
  );
}
