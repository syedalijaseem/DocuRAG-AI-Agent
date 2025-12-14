/**
 * UI Context for application-wide UI state.
 * Includes responsive breakpoint tracking and sidebar state.
 */
import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from "react";
import { useBreakpoint, type Breakpoint } from "../hooks/useBreakpoint";

interface UIContextType {
  // Sidebar state
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;

  // Tablet hover expansion
  sidebarExpanded: boolean;
  setSidebarExpanded: (expanded: boolean) => void;

  // Responsive breakpoint
  breakpoint: Breakpoint;
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
}

const UIContext = createContext<UIContextType | undefined>(undefined);

export function UIProvider({ children }: { children: ReactNode }) {
  const breakpoint = useBreakpoint();
  const isMobile = breakpoint === "mobile";
  const isTablet = breakpoint === "tablet";
  const isDesktop = breakpoint === "desktop" || breakpoint === "large";

  const [sidebarOpen, setSidebarOpen] = useState(() => {
    // Default: only open on desktop
    if (typeof window !== "undefined") {
      return window.innerWidth >= 1024;
    }
    return true;
  });

  const [sidebarExpanded, setSidebarExpanded] = useState(false);

  // Auto-close sidebar when switching to mobile
  useEffect(() => {
    if (isMobile) {
      setSidebarOpen(false);
    } else if (isDesktop) {
      setSidebarOpen(true);
    }
  }, [isMobile, isDesktop]);

  // Keyboard shortcut for sidebar toggle (Ctrl+B)
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "b") {
        e.preventDefault();
        setSidebarOpen((prev) => !prev);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  function toggleSidebar() {
    setSidebarOpen((prev) => !prev);
  }

  return (
    <UIContext.Provider
      value={{
        sidebarOpen,
        setSidebarOpen,
        toggleSidebar,
        sidebarExpanded,
        setSidebarExpanded,
        breakpoint,
        isMobile,
        isTablet,
        isDesktop,
      }}
    >
      {children}
    </UIContext.Provider>
  );
}

export function useUI() {
  const context = useContext(UIContext);
  if (!context) {
    throw new Error("useUI must be used within UIProvider");
  }
  return context;
}
