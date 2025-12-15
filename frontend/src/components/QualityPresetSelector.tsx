/**
 * QualityPresetSelector - Segmented toggle for answer quality presets
 */
import { useState } from "react";
import { Lock, Info } from "lucide-react";
import type { QualityPreset, SubscriptionPlan } from "../types";
import { LimitModal } from "./LimitModal";

interface PresetOption {
  id: QualityPreset;
  label: string;
  chunks: number;
  description: string;
  tokenEstimate: string;
  minPlan: SubscriptionPlan;
}

const PRESETS: PresetOption[] = [
  {
    id: "quick",
    label: "Quick",
    chunks: 5,
    description: "Fast answers, minimal context",
    tokenEstimate: "~1.5k",
    minPlan: "free",
  },
  {
    id: "standard",
    label: "Standard",
    chunks: 10,
    description: "Balanced speed & quality",
    tokenEstimate: "~3k",
    minPlan: "free",
  },
  {
    id: "thorough",
    label: "Thorough",
    chunks: 20,
    description: "Deeper search, better accuracy",
    tokenEstimate: "~6k",
    minPlan: "pro",
  },
  {
    id: "deep",
    label: "Deep",
    chunks: 35,
    description: "Comprehensive answers",
    tokenEstimate: "~10.5k",
    minPlan: "premium",
  },
  {
    id: "max",
    label: "Max",
    chunks: 50,
    description: "Maximum context",
    tokenEstimate: "~15k",
    minPlan: "premium",
  },
];

const PLAN_HIERARCHY: Record<SubscriptionPlan, number> = {
  free: 0,
  pro: 1,
  premium: 2,
};

interface QualityPresetSelectorProps {
  value: QualityPreset;
  onChange: (preset: QualityPreset) => void;
  userPlan: SubscriptionPlan;
  disabled?: boolean;
}

export function QualityPresetSelector({
  value,
  onChange,
  userPlan,
  disabled = false,
}: QualityPresetSelectorProps) {
  const [showModal, setShowModal] = useState(false);
  const [hoveredPreset, setHoveredPreset] = useState<QualityPreset | null>(
    null
  );

  function canAccess(preset: PresetOption): boolean {
    return PLAN_HIERARCHY[userPlan] >= PLAN_HIERARCHY[preset.minPlan];
  }

  function handleClick(preset: PresetOption) {
    if (disabled) return;

    if (!canAccess(preset)) {
      setShowModal(true);
      return;
    }

    onChange(preset.id);
  }

  const hoveredOption = hoveredPreset
    ? PRESETS.find((p) => p.id === hoveredPreset)
    : null;

  return (
    <>
      <div className="flex flex-col gap-1">
        {/* Label */}
        <div className="flex items-center gap-1.5 text-xs text-[#737373] dark:text-[#808080]">
          <span>Answer quality</span>
          <div className="relative group">
            <Info className="w-3.5 h-3.5 cursor-help" />
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-[#1a1a1a] dark:bg-[#2a2a2a] text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
              Higher quality searches more of your documents
            </div>
          </div>
        </div>

        {/* Segmented Toggle */}
        <div className="flex rounded-lg bg-[#f0f0f0] dark:bg-[#2a2a2a] p-1 gap-0.5">
          {PRESETS.map((preset) => {
            const isActive = value === preset.id;
            const isLocked = !canAccess(preset);

            return (
              <button
                key={preset.id}
                onClick={() => handleClick(preset)}
                onMouseEnter={() => setHoveredPreset(preset.id)}
                onMouseLeave={() => setHoveredPreset(null)}
                disabled={disabled}
                className={`
                  relative flex items-center justify-center gap-1 px-3 py-1.5 text-xs font-medium rounded-md transition-all
                  ${
                    isActive
                      ? "bg-white dark:bg-[#3a3a3a] text-[#0d9488] dark:text-[#2dd4bf] shadow-sm"
                      : isLocked
                      ? "text-[#a3a3a3] dark:text-[#6b6b6b] cursor-pointer hover:bg-[#e8e8e8] dark:hover:bg-[#333333]"
                      : "text-[#525252] dark:text-[#a0a0a0] hover:bg-[#e8e8e8] dark:hover:bg-[#333333]"
                  }
                  ${disabled ? "opacity-50 cursor-not-allowed" : ""}
                `}
              >
                {isLocked && <Lock className="w-3 h-3" />}
                <span>{preset.label}</span>
              </button>
            );
          })}
        </div>

        {/* Hover tooltip */}
        {hoveredOption && (
          <div className="text-xs text-[#737373] dark:text-[#808080] flex items-center gap-2 mt-0.5">
            <span>{hoveredOption.description}</span>
            <span className="text-[#a3a3a3] dark:text-[#6b6b6b]">
              {hoveredOption.tokenEstimate} tokens
            </span>
          </div>
        )}
      </div>

      {/* Upgrade Modal */}
      <LimitModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        limitType="tokens"
        currentPlan={userPlan}
      />
    </>
  );
}

// Helper to get chunk count from preset
export function getChunkCount(preset: QualityPreset): number {
  const found = PRESETS.find((p) => p.id === preset);
  return found?.chunks || 10;
}

// Helper to check if preset is accessible
export function canUsePreset(
  preset: QualityPreset,
  plan: SubscriptionPlan
): boolean {
  const option = PRESETS.find((p) => p.id === preset);
  if (!option) return false;
  return PLAN_HIERARCHY[plan] >= PLAN_HIERARCHY[option.minPlan];
}
