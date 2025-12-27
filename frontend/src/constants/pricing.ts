/**
 * Shared pricing tier data for landing page, upgrade page, and modals
 */

export interface PricingFeature {
  text: string;
  included: boolean;
}

export interface PricingTier {
  name: string;
  price: string;
  period: string;
  description: string;
  features: PricingFeature[];
  highlighted?: boolean;
  comingSoon?: boolean;
  badge?: string;
}

export const pricingTiers: PricingTier[] = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "Perfect for trying out Querious",
    features: [
      { text: "10,000 tokens (one-time)", included: true },
      { text: "3 chats", included: true },
      { text: "1 project", included: true },
      { text: "3 documents", included: true },
      { text: "DeepSeek model", included: true },
      { text: "Quick & Standard quality", included: true },
    ],
    comingSoon: false,
  },
  {
    name: "Pro",
    price: "$10",
    period: "/month",
    description: "For regular users who need more",
    features: [
      { text: "2,000,000 tokens/month", included: true },
      { text: "Unlimited chats", included: true },
      { text: "5 projects", included: true },
      { text: "25 documents", included: true },
      { text: "Gemini & GPT-5 mini", included: true },
      { text: "Thorough quality preset", included: true },
    ],
    comingSoon: true,
  },
  {
    name: "Premium",
    price: "$25",
    period: "/month",
    description: "Unlimited power for professionals",
    features: [
      { text: "15,000,000 tokens/month", included: true },
      { text: "Unlimited everything", included: true },
      { text: "All AI models", included: true },
      { text: "GPT-5.2, Claude Opus, Gemini Pro", included: true },
      { text: "All quality presets", included: true },
      { text: "Priority support", included: true },
    ],
    highlighted: true,
    comingSoon: true,
    badge: "Best Value",
  },
];
