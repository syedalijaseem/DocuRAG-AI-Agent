/**
 * TokenLimitModal - Upgrade modal shown when token limit is reached
 */
import { useEffect, useCallback } from "react";
import { X, AlertTriangle } from "lucide-react";
import { PlanCard } from "./PlanCard";

interface TokenLimitModalProps {
  isOpen: boolean;
  onClose: () => void;
  tokensUsed: number;
  tokenLimit: number;
  currentPlan: "free" | "pro" | "premium";
}

export function TokenLimitModal({
  isOpen,
  onClose,
  tokensUsed,
  tokenLimit,
  currentPlan,
}: TokenLimitModalProps) {
  // Handle Escape key
  const handleEscape = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose]
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "";
    };
  }, [isOpen, handleEscape]);

  if (!isOpen) return null;

  function handleUpgrade(plan: "pro" | "premium") {
    // Redirect to checkout page
    window.location.href = `/checkout?plan=${plan}`;
  }

  const freePlanFeatures = [
    { text: "5,000 tokens (one-time)", included: true },
    { text: "3 chats", included: true },
    { text: "1 project", included: true },
    { text: "3 documents", included: true },
    { text: "DeepSeek only", included: true },
  ];

  const proPlanFeatures = [
    { text: "500,000 tokens/month", included: true },
    { text: "Unlimited chats", included: true },
    { text: "5 projects", included: true },
    { text: "25 documents", included: true },
    { text: "Gemini 2.5 Pro", included: true },
    { text: "GPT-4o", included: true },
    { text: "Claude Opus 4", included: true },
  ];

  const premiumPlanFeatures = [
    { text: "2,000,000 tokens/month", included: true },
    { text: "Unlimited everything", included: true },
    { text: "GPT-5.2", included: true },
    { text: "Gemini 3.0", included: true },
    { text: "Claude Opus 4.5", included: true },
    { text: "All Pro models included", included: true },
  ];

  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />

      {/* Modal */}
      <div className="relative w-full max-w-4xl bg-white dark:bg-[#1a1a1a] rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-lg text-[#737373] hover:text-[#1a1a1a] dark:text-[#808080] dark:hover:text-white hover:bg-[#f0f0f0] dark:hover:bg-[#3a3a3a] transition-colors z-10"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Content */}
        <div className="p-8 pt-12">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-amber-100 dark:bg-amber-900/30 rounded-full mb-4">
              <AlertTriangle className="w-8 h-8 text-amber-600 dark:text-amber-400" />
            </div>
            <h2 className="text-2xl font-bold text-[#1a1a1a] dark:text-white mb-2">
              You've reached your token limit
            </h2>
            <p className="text-[#737373] dark:text-[#a0a0a0]">
              You've used {tokensUsed.toLocaleString()} of{" "}
              {tokenLimit.toLocaleString()} tokens on the{" "}
              {currentPlan.charAt(0).toUpperCase() + currentPlan.slice(1)} Plan.
              <br />
              Upgrade to continue chatting with your documents.
            </p>
          </div>

          {/* Plan cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <PlanCard
              name="Free"
              price="Free"
              priceSubtext=""
              features={freePlanFeatures}
              buttonText="Current Plan"
              isCurrent={currentPlan === "free"}
            />
            <PlanCard
              name="Pro"
              price="$10"
              features={proPlanFeatures}
              buttonText="Upgrade to Pro"
              isCurrent={currentPlan === "pro"}
              onClick={() => handleUpgrade("pro")}
            />
            <PlanCard
              name="Premium"
              price="$25"
              features={premiumPlanFeatures}
              buttonText="Upgrade to Premium"
              isCurrent={currentPlan === "premium"}
              isHighlighted
              highlightLabel="Best Value"
              onClick={() => handleUpgrade("premium")}
            />
          </div>

          {/* Trust signals */}
          <p className="text-center text-xs text-[#a3a3a3] dark:text-[#6b6b6b]">
            Cancel anytime • Secure payment • Instant access
          </p>
        </div>
      </div>
    </div>
  );
}
