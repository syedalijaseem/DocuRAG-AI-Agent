/**
 * PlanCard - Reusable plan card for upgrade modal
 */

interface PlanFeature {
  text: string;
  included: boolean;
}

interface PlanCardProps {
  name: string;
  price: string;
  priceSubtext?: string;
  features: PlanFeature[];
  buttonText: string;
  buttonDisabled?: boolean;
  isCurrent?: boolean;
  isHighlighted?: boolean;
  highlightLabel?: string;
  onClick?: () => void;
}

export function PlanCard({
  name,
  price,
  priceSubtext = "/month",
  features,
  buttonText,
  buttonDisabled = false,
  isCurrent = false,
  isHighlighted = false,
  highlightLabel,
  onClick,
}: PlanCardProps) {
  return (
    <div
      className={`relative flex flex-col p-6 rounded-xl border transition-all ${
        isHighlighted
          ? "border-amber-400 dark:border-amber-500 bg-gradient-to-b from-amber-50/50 to-transparent dark:from-amber-900/10"
          : isCurrent
          ? "border-[#e8e8e8] dark:border-[#3a3a3a] bg-[#f8f8f8] dark:bg-[#1a1a1a]"
          : "border-[#e8e8e8] dark:border-[#3a3a3a] bg-white dark:bg-[#242424]"
      }`}
    >
      {/* Highlight badge */}
      {isHighlighted && highlightLabel && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-xs font-semibold rounded-full shadow-md">
          ⭐ {highlightLabel}
        </div>
      )}

      {/* Plan name */}
      <h3 className="text-lg font-semibold text-[#1a1a1a] dark:text-white mb-1">
        {name}
        {isCurrent && (
          <span className="ml-2 text-xs px-2 py-0.5 bg-[#e8e8e8] dark:bg-[#3a3a3a] text-[#737373] dark:text-[#808080] rounded">
            Current
          </span>
        )}
      </h3>

      {/* Price */}
      <div className="mb-4">
        <span className="text-3xl font-bold text-[#1a1a1a] dark:text-white">
          {price}
        </span>
        {price !== "Free" && (
          <span className="text-[#737373] dark:text-[#808080] text-sm">
            {priceSubtext}
          </span>
        )}
      </div>

      {/* Features */}
      <ul className="flex-1 space-y-2 mb-6">
        {features.map((feature, index) => (
          <li
            key={index}
            className={`flex items-start gap-2 text-sm ${
              feature.included
                ? "text-[#525252] dark:text-[#a0a0a0]"
                : "text-[#a3a3a3] dark:text-[#6b6b6b] line-through"
            }`}
          >
            <span
              className={`flex-shrink-0 ${
                feature.included ? "text-[#0d9488]" : "text-[#d4d4d4]"
              }`}
            >
              {feature.included ? "✓" : "×"}
            </span>
            {feature.text}
          </li>
        ))}
      </ul>

      {/* CTA Button */}
      <button
        onClick={onClick}
        disabled={buttonDisabled || isCurrent}
        className={`w-full py-3 px-4 rounded-lg font-medium text-sm transition-all ${
          isCurrent
            ? "bg-[#e8e8e8] dark:bg-[#3a3a3a] text-[#a3a3a3] dark:text-[#6b6b6b] cursor-not-allowed"
            : isHighlighted
            ? "bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white shadow-md"
            : "bg-[#0d9488] hover:bg-[#0f766e] dark:bg-[#2dd4bf] dark:hover:bg-[#5eead4] text-white dark:text-[#0f2e2b]"
        }`}
      >
        {buttonText}
      </button>
    </div>
  );
}
