/**
 * Model Selector - Tiered dropdown for AI model selection (Free/Pro/Premium)
 */
import { Lock, ChevronDown, Check, Crown, Sparkles } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import type { AIModel } from "../types";
import { useToast } from "./Toast";

type ModelTier = "free" | "pro" | "premium";

interface ModelOption {
  id: AIModel;
  name: string;
  description: string;
  tier: ModelTier;
}

const MODELS: ModelOption[] = [
  // Free tier
  {
    id: "deepseek-v3",
    name: "DeepSeek V3.2",
    description: "Fast & efficient",
    tier: "free",
  },
  // Pro tier
  {
    id: "gemini-2.5-pro",
    name: "Gemini 2.5 Pro",
    description: "Advanced reasoning",
    tier: "pro",
  },
  {
    id: "gpt-4o",
    name: "GPT-4o",
    description: "OpenAI flagship",
    tier: "pro",
  },
  {
    id: "claude-opus-4",
    name: "Claude Opus 4.5",
    description: "Anthropic's best",
    tier: "pro",
  },
  // Premium tier
  {
    id: "gemini-3-pro",
    name: "Gemini 3 Pro",
    description: "Google's best",
    tier: "premium",
  },
  {
    id: "claude-thinking",
    name: "Claude Thinking 32k",
    description: "Extended reasoning",
    tier: "premium",
  },
  {
    id: "gpt-5.1-high",
    name: "GPT-5.1 High",
    description: "Most capable",
    tier: "premium",
  },
];

interface ModelSelectorProps {
  value: AIModel;
  onChange: (model: AIModel) => void;
  userTier: "free" | "pro" | "premium"; // User's subscription tier
  disabled?: boolean;
}

export function ModelSelector({
  value,
  onChange,
  userTier,
  disabled = false,
}: ModelSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { showToast } = useToast();

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const selectedModel = MODELS.find((m) => m.id === value) || MODELS[0];

  // Check if user can access a model based on tier
  function canAccess(modelTier: ModelTier): boolean {
    if (modelTier === "free") return true;
    if (modelTier === "pro")
      return userTier === "pro" || userTier === "premium";
    if (modelTier === "premium") return userTier === "premium";
    return false;
  }

  function handleSelect(model: ModelOption) {
    if (!canAccess(model.tier)) {
      const toastType =
        model.tier === "premium" ? "upgrade-premium" : "upgrade-pro";
      const message =
        model.tier === "premium"
          ? `${model.name} requires Premium`
          : `${model.name} requires Pro`;
      showToast(message, toastType);
      return;
    }
    onChange(model.id);
    setIsOpen(false);
  }

  // Get tier badge
  function TierBadge({ tier }: { tier: ModelTier }) {
    if (tier === "free") return null;
    if (tier === "pro") {
      return (
        <span className="inline-flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded font-medium">
          <Sparkles className="w-2.5 h-2.5" />
          PRO
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 rounded font-medium">
        <Crown className="w-2.5 h-2.5" />
        PREMIUM
      </span>
    );
  }

  // Group models by tier
  const freeModels = MODELS.filter((m) => m.tier === "free");
  const proModels = MODELS.filter((m) => m.tier === "pro");
  const premiumModels = MODELS.filter((m) => m.tier === "premium");

  return (
    <div className="relative inline-block" ref={dropdownRef}>
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-[#525252] dark:text-[#a0a0a0] hover:text-[#1a1a1a] dark:hover:text-white hover:bg-[#f0f0f0] dark:hover:bg-[#3a3a3a] rounded-lg transition-colors disabled:opacity-50"
      >
        <span className="font-medium">{selectedModel.name}</span>
        <ChevronDown
          className={`w-3.5 h-3.5 transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Dropdown menu - opens upward */}
      {isOpen && (
        <div className="absolute bottom-full left-0 mb-2 w-72 max-h-96 overflow-y-auto bg-white dark:bg-[#2a2a2a] border border-[#e8e8e8] dark:border-[#3a3a3a] rounded-xl shadow-xl z-[100]">
          {/* Free tier */}
          <div className="p-1">
            <div className="px-3 py-1.5 text-xs font-medium text-[#737373] dark:text-[#808080] uppercase tracking-wider">
              Free
            </div>
            {freeModels.map((model) => (
              <ModelRow key={model.id} model={model} />
            ))}
          </div>

          <div className="border-t border-[#e8e8e8] dark:border-[#3a3a3a]" />

          {/* Pro tier */}
          <div className="p-1">
            <div className="px-3 py-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 uppercase tracking-wider flex items-center gap-1">
              <Sparkles className="w-3 h-3" /> Pro
            </div>
            {proModels.map((model) => (
              <ModelRow key={model.id} model={model} />
            ))}
          </div>

          <div className="border-t border-[#e8e8e8] dark:border-[#3a3a3a]" />

          {/* Premium tier */}
          <div className="p-1">
            <div className="px-3 py-1.5 text-xs font-medium text-amber-600 dark:text-amber-400 uppercase tracking-wider flex items-center gap-1">
              <Crown className="w-3 h-3" /> Premium
            </div>
            {premiumModels.map((model) => (
              <ModelRow key={model.id} model={model} />
            ))}
          </div>
        </div>
      )}
    </div>
  );

  function ModelRow({ model }: { model: ModelOption }) {
    const isLocked = !canAccess(model.tier);
    const isSelected = model.id === value;

    return (
      <button
        type="button"
        onClick={() => handleSelect(model)}
        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
          isSelected
            ? "bg-[#f0f0f0] dark:bg-[#3a3a3a]"
            : "hover:bg-[#f8f8f8] dark:hover:bg-[#333333]"
        } ${isLocked ? "opacity-50" : ""}`}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={`font-medium text-sm ${
                isSelected
                  ? "text-[#0d9488] dark:text-[#2dd4bf]"
                  : "text-[#1a1a1a] dark:text-[#ececec]"
              }`}
            >
              {model.name}
            </span>
            {isLocked && <TierBadge tier={model.tier} />}
          </div>
          <span className="text-xs text-[#737373] dark:text-[#808080]">
            {model.description}
          </span>
        </div>
        {isLocked ? (
          <Lock className="w-4 h-4 text-[#737373] dark:text-[#808080] flex-shrink-0" />
        ) : isSelected ? (
          <Check className="w-4 h-4 text-[#0d9488] dark:text-[#2dd4bf] flex-shrink-0" />
        ) : null}
      </button>
    );
  }
}
