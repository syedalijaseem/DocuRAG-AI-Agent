/**
 * Branded Loading Spinner - Logo centered inside a circular spinner
 */
import logo from "../assets/logo.png";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  text?: string;
  fullScreen?: boolean;
}

export function LoadingSpinner({
  size = "md",
  text,
  fullScreen = false,
}: LoadingSpinnerProps) {
  const sizes = {
    sm: { container: "w-12 h-12", logo: "w-6 h-6", spinner: "w-12 h-12" },
    md: { container: "w-20 h-20", logo: "w-10 h-10", spinner: "w-20 h-20" },
    lg: { container: "w-28 h-28", logo: "w-14 h-14", spinner: "w-28 h-28" },
  };

  const s = sizes[size];

  const spinner = (
    <div className="flex flex-col items-center gap-3">
      <div className={`relative ${s.container}`}>
        {/* Spinning ring */}
        <div
          className={`absolute inset-0 ${s.spinner} rounded-full border-4 border-transparent border-t-[#0d9488] dark:border-t-[#2dd4bf] animate-spin`}
        />
        {/* Logo centered */}
        <div className="absolute inset-0 flex items-center justify-center">
          <img
            src={logo}
            alt="Loading"
            className={`${s.logo} object-contain`}
          />
        </div>
      </div>
      {text && (
        <p className="text-sm text-[#a3a3a3] dark:text-[#737373] animate-pulse">
          {text}
        </p>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#f8f8f8] dark:bg-[#1a1a1a]">
        {spinner}
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center h-full">{spinner}</div>
  );
}
