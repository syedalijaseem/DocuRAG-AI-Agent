/**
 * UpgradePage - Plan comparison and upgrade page
 */
import { useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { pricingTiers } from "../constants/pricing";

export function UpgradePage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  // Current plan (hardcoded to "Free" for now - will be dynamic later)
  const currentPlan = "Free";

  // Calculate usage percentage (mock data for now)
  const tokensUsed = user?.tokens_used ?? 0;
  const tokenLimit = 10000;
  const usagePercent = Math.min((tokensUsed / tokenLimit) * 100, 100);

  return (
    <div className="min-h-screen bg-[var(--color-bg)]">
      {/* Header */}
      <header className="border-b border-[var(--color-border)] bg-[var(--color-surface)]">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            <ArrowLeft size={20} />
            Back to app
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-6xl mx-auto px-4 py-12">
        <div className="text-center mb-12">
          <h1 className="text-3xl sm:text-4xl font-bold text-[var(--color-text-primary)] mb-4">
            Upgrade your plan
          </h1>
          <p className="text-[var(--color-text-secondary)]">
            Unlock more tokens, models, and features
          </p>
        </div>

        {/* Usage Bar (for free users) */}
        {currentPlan === "Free" && (
          <div className="max-w-md mx-auto mb-12 p-6 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)]">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-[var(--color-text-secondary)]">
                Token Usage
              </span>
              <span className="text-[var(--color-text-primary)] font-medium">
                {tokensUsed.toLocaleString()} / {tokenLimit.toLocaleString()}
              </span>
            </div>
            <div className="h-2 bg-[var(--color-border)] rounded-full overflow-hidden">
              <div
                className="h-full bg-[var(--color-accent)] transition-all duration-300"
                style={{ width: `${usagePercent}%` }}
              />
            </div>
            {usagePercent >= 80 && (
              <p className="mt-2 text-sm text-amber-600 dark:text-amber-400">
                You're running low on tokens. Consider upgrading!
              </p>
            )}
          </div>
        )}

        {/* Plan Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {pricingTiers.map((tier) => {
            const isCurrent = tier.name === currentPlan;

            return (
              <div
                key={tier.name}
                className={`relative flex flex-col p-6 rounded-xl border transition-all ${
                  tier.highlighted
                    ? "border-amber-400 dark:border-amber-500 bg-gradient-to-b from-amber-50/50 to-transparent dark:from-amber-900/10"
                    : isCurrent
                    ? "border-[var(--color-accent)] bg-[var(--color-accent-subtle)]"
                    : "border-[var(--color-border)] bg-[var(--color-surface)]"
                }`}
              >
                {/* Current badge */}
                {isCurrent && (
                  <div className="absolute -top-3 left-4 px-3 py-1 bg-[var(--color-accent)] text-white text-xs font-semibold rounded-full">
                    Current Plan
                  </div>
                )}

                {/* Best Value badge */}
                {tier.badge && !isCurrent && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-xs font-semibold rounded-full">
                    ⭐ {tier.badge}
                  </div>
                )}

                <h3 className="text-lg font-semibold text-[var(--color-text-primary)] mb-1 mt-2">
                  {tier.name}
                </h3>
                <p className="text-sm text-[var(--color-text-secondary)] mb-4">
                  {tier.description}
                </p>
                <div className="mb-4">
                  <span className="text-3xl font-bold text-[var(--color-text-primary)]">
                    {tier.price}
                  </span>
                  <span className="text-[var(--color-text-secondary)] text-sm">
                    {tier.period}
                  </span>
                </div>

                <ul className="flex-1 space-y-2 mb-6">
                  {tier.features.map((feature) => (
                    <li
                      key={feature.text}
                      className={`flex items-start gap-2 text-sm ${
                        feature.included
                          ? "text-[var(--color-text-secondary)]"
                          : "text-[var(--color-text-tertiary)] line-through"
                      }`}
                    >
                      <span
                        className={
                          feature.included
                            ? "text-[var(--color-accent)]"
                            : "text-[var(--color-text-disabled)]"
                        }
                      >
                        {feature.included ? "✓" : "×"}
                      </span>
                      {feature.text}
                    </li>
                  ))}
                </ul>

                <button
                  disabled={isCurrent || tier.comingSoon}
                  className={`w-full py-3 px-4 rounded-lg font-medium text-sm transition-all ${
                    isCurrent
                      ? "bg-[var(--color-border)] text-[var(--color-text-tertiary)] cursor-not-allowed"
                      : tier.comingSoon
                      ? "bg-[var(--color-border)] text-[var(--color-text-tertiary)] cursor-not-allowed"
                      : tier.highlighted
                      ? "bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white"
                      : "btn-primary"
                  }`}
                >
                  {isCurrent
                    ? "Current Plan"
                    : tier.comingSoon
                    ? "Coming Soon"
                    : "Upgrade"}
                </button>

                {tier.comingSoon && !isCurrent && (
                  <p className="mt-3 text-xs text-center text-[var(--color-text-tertiary)]">
                    We're working hard to bring you {tier.name}!
                  </p>
                )}
              </div>
            );
          })}
        </div>

        {/* Contact */}
        <p className="text-center mt-12 text-[var(--color-text-secondary)]">
          Have questions?{" "}
          <a
            href="mailto:support@querious.app"
            className="text-[var(--color-accent)] hover:underline"
          >
            Contact support@querious.app
          </a>
        </p>
      </main>
    </div>
  );
}
