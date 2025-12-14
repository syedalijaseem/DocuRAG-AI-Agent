/**
 * useBreakpoint - Hook for responsive state management
 * Returns the current breakpoint based on window width
 */
import { useState, useEffect } from "react";

export type Breakpoint = "mobile" | "tablet" | "desktop" | "large";

export function useBreakpoint(): Breakpoint {
  const [breakpoint, setBreakpoint] = useState<Breakpoint>("mobile");

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      if (width >= 1280) {
        setBreakpoint("large");
      } else if (width >= 1024) {
        setBreakpoint("desktop");
      } else if (width >= 768) {
        setBreakpoint("tablet");
      } else {
        setBreakpoint("mobile");
      }
    };

    // Set initial value
    handleResize();

    // Add listener
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return breakpoint;
}

// Helper hooks for common checks
export function useIsMobile(): boolean {
  const breakpoint = useBreakpoint();
  return breakpoint === "mobile";
}

export function useIsDesktop(): boolean {
  const breakpoint = useBreakpoint();
  return breakpoint === "desktop" || breakpoint === "large";
}
