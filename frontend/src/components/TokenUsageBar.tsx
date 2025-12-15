/**
 * TokenUsageBar - Displays token usage as a progress bar
 */
import { Zap } from "lucide-react";

interface TokenUsageBarProps {
  tokensUsed: number;
  tokenLimit: number;
  plan: "free" | "pro" | "premium";
}

export function TokenUsageBar({
  tokensUsed,
  tokenLimit,
  plan,
}: TokenUsageBarProps) {
  const percentage = Math.min((tokensUsed / tokenLimit) * 100, 100);
  const isNearLimit = percentage >= 80;
  const isAtLimit = percentage >= 100;

  // Format numbers with K/M suffix
  function formatTokens(n: number): string {
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
    if (n >= 1000) return `${(n / 1000).toFixed(0)}K`;
    return n.toString();
  }

  // Plan colors
  const planColors = {
    free: "bg-gray-500",
    pro: "bg-teal-500",
    premium: "bg-amber-500",
  };

  // Progress bar color based on usage
  const progressColor = isAtLimit
    ? "bg-red-500"
    : isNearLimit
    ? "bg-amber-500"
    : planColors[plan];

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-1.5 text-[#737373] dark:text-[#808080]">
          <Zap className="w-3.5 h-3.5" />
          <span>Token Usage</span>
        </div>
        <span
          className={`font-medium ${
            isAtLimit
              ? "text-red-500"
              : isNearLimit
              ? "text-amber-500"
              : "text-[#525252] dark:text-[#a0a0a0]"
          }`}
        >
          {formatTokens(tokensUsed)} / {formatTokens(tokenLimit)}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-[#e5e5e5] dark:bg-[#3a3a3a] rounded-full overflow-hidden">
        <div
          className={`h-full ${progressColor} transition-all duration-300 rounded-full`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* Warning message */}
      {isAtLimit && (
        <p className="text-xs text-red-500 font-medium">
          Token limit reached! Upgrade to continue.
        </p>
      )}
      {isNearLimit && !isAtLimit && (
        <p className="text-xs text-amber-500">
          {Math.round(100 - percentage)}% remaining
        </p>
      )}
    </div>
  );
}
