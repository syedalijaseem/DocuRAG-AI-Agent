/**
 * Toast notification component for modern alerts
 */
import {
  useState,
  useEffect,
  createContext,
  useContext,
  type ReactNode,
} from "react";
import { X, Sparkles, Crown, AlertCircle, CheckCircle } from "lucide-react";

type ToastType =
  | "info"
  | "success"
  | "warning"
  | "upgrade-pro"
  | "upgrade-premium";

interface Toast {
  id: string;
  message: string;
  type: ToastType;
  duration?: number;
}

interface ToastContextType {
  showToast: (message: string, type?: ToastType, duration?: number) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return context;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  function showToast(
    message: string,
    type: ToastType = "info",
    duration = 4000
  ) {
    const id = `toast-${Date.now()}`;
    setToasts((prev) => [...prev, { id, message, type, duration }]);
  }

  function removeToast(id: string) {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {/* Toast container */}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[200] flex flex-col gap-2">
        {toasts.map((toast) => (
          <ToastItem
            key={toast.id}
            toast={toast}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  useEffect(() => {
    if (toast.duration) {
      const timer = setTimeout(onClose, toast.duration);
      return () => clearTimeout(timer);
    }
  }, [toast.duration, onClose]);

  const styles = {
    info: {
      bg: "bg-[#1a1a1a] dark:bg-[#2a2a2a]",
      border: "border-[#3a3a3a]",
      icon: <AlertCircle className="w-5 h-5 text-blue-400" />,
    },
    success: {
      bg: "bg-[#1a1a1a] dark:bg-[#2a2a2a]",
      border: "border-[#3a3a3a]",
      icon: <CheckCircle className="w-5 h-5 text-green-400" />,
    },
    warning: {
      bg: "bg-[#1a1a1a] dark:bg-[#2a2a2a]",
      border: "border-amber-500/30",
      icon: <AlertCircle className="w-5 h-5 text-amber-400" />,
    },
    "upgrade-pro": {
      bg: "bg-gradient-to-r from-blue-600/90 to-indigo-600/90 backdrop-blur-sm",
      border: "border-blue-400/30",
      icon: <Sparkles className="w-5 h-5 text-white" />,
    },
    "upgrade-premium": {
      bg: "bg-gradient-to-r from-amber-500/90 to-orange-600/90 backdrop-blur-sm",
      border: "border-amber-300/30",
      icon: <Crown className="w-5 h-5 text-white" />,
    },
  };

  const style = styles[toast.type];
  const isUpgrade = toast.type.startsWith("upgrade");

  return (
    <div
      className={`flex items-center gap-3 px-4 py-3 rounded-xl border shadow-2xl animate-in slide-in-from-bottom-4 fade-in duration-300 ${style.bg} ${style.border}`}
    >
      {style.icon}
      <span
        className={`text-sm font-medium ${
          isUpgrade ? "text-white" : "text-white"
        }`}
      >
        {toast.message}
      </span>
      {isUpgrade && (
        <button className="ml-2 px-3 py-1 text-xs font-semibold bg-white/20 hover:bg-white/30 rounded-lg text-white transition-colors">
          Upgrade
        </button>
      )}
      <button
        onClick={onClose}
        className={`ml-2 p-1 rounded-lg transition-colors ${
          isUpgrade
            ? "hover:bg-white/20 text-white/80"
            : "hover:bg-white/10 text-gray-400"
        }`}
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
