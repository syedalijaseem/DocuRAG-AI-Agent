# Landing Page + Upgrade Flow Implementation Plan

## Overview

Create a modern, mobile-first landing page and upgrade system for Querious.

**Routing Strategy:**

- `/` → Landing page (public, for unauthenticated users)
- `/home` → App dashboard (protected, for authenticated users)
- `/upgrade` → Plan upgrade page (protected)

---

## Performance Best Practices (FCP/LCP)

To ensure fast First Contentful Paint (FCP) and Largest Contentful Paint (LCP):

1. **Lazy-load animations**: Import Framer Motion dynamically, animations trigger after initial paint
2. **Above-the-fold priority**: Hero renders static HTML first, animations apply after hydration
3. **No blocking animations**: All entrance animations use `initial` opacity for graceful degradation
4. **Font optimization**: Use `font-display: swap` for web fonts
5. **Image optimization**: Hero image should use `loading="eager"`, below-fold images use `loading="lazy"`

---

## Animations (CSS-Only)

No additional dependencies. Pure CSS animations for best performance.

**Animations applied:**

- Hero: Fade-up entrance using `@keyframes` with `animation-delay`
- Features: `IntersectionObserver` + CSS class toggle for viewport animations
- Pricing cards: `transform: scale()` on hover with `transition`
- Navbar: `backdrop-filter` transition on scroll state

**CSS utilities in `index.css`:**

```css
.animate-fade-up {
  animation: fadeUp 0.6s ease-out forwards;
  opacity: 0;
}
@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

---

## Email Waitlist (Pro/Premium Plans)

On pricing cards where `comingSoon: true`:

- Show email input + "Join Waitlist" button below disabled CTA
- Store emails in MongoDB `waitlist` collection
- New API endpoint: `POST /api/waitlist`

**Schema:**

```typescript
interface WaitlistEntry {
  email: string;
  plan: "pro" | "premium";
  created_at: Date;
}
```

---

## Contact Form (Footer)

Simple contact form with:

- Name, Email, Message fields
- API endpoint: `POST /api/contact`
- Store in MongoDB or send via email service (future)
- Client-side validation with clear error states

---

## Proposed Changes

### Shared Constants

#### [NEW] [pricing.ts](file:///home/syedalijaseem/Projects/DocuRAG-AI-Agent/frontend/src/constants/pricing.ts)

Shared pricing data used by LandingPage, UpgradePage, and any upgrade modals:

```typescript
export const pricingTiers = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    features: [...],
    comingSoon: false,
  },
  {
    name: "Pro",
    price: "$10",
    period: "/month",
    features: [...],
    comingSoon: true,
  },
  {
    name: "Premium",
    price: "$25",
    period: "/month",
    features: [...],
    comingSoon: true,
    highlighted: true,
    badge: "Best Value",
  },
];
```

---

### Landing Page

#### [NEW] [LandingPage.tsx](file:///home/syedalijaseem/Projects/DocuRAG-AI-Agent/frontend/src/pages/LandingPage.tsx)

Main landing page with:

- Navbar (sticky, blur on scroll, mobile hamburger)
- Hero section (headline, CTAs)
- Features section (6 cards in grid)
- How It Works (3 steps)
- Pricing section (uses shared `pricingTiers`)
- Footer

**Auth-aware behavior:** If user is logged in, CTAs change:

- "Get Started Free" → "Go to Dashboard"
- "Log in" button hidden

---

### Upgrade Page

#### [NEW] [UpgradePage.tsx](file:///home/syedalijaseem/Projects/DocuRAG-AI-Agent/frontend/src/pages/UpgradePage.tsx)

- Back to app link
- Current plan indicator with usage bar
- Three plan cards (uses shared `pricingTiers`)
- Coming Soon state for Pro/Premium

---

### Routing Updates

#### [MODIFY] [App.tsx](file:///home/syedalijaseem/Projects/DocuRAG-AI-Agent/frontend/src/App.tsx)

Update routing:

- `/` → `LandingPage` (public)
- `/home` → `ChatsPage` (protected, current app dashboard)
- `/upgrade` → `UpgradePage` (protected)
- Update `AuthRoute` redirect from `/` to `/home`
- Update `ProtectedRoute` redirect to `/` (landing)

---

### Component Update

#### [MODIFY] [PlanCard.tsx](file:///home/syedalijaseem/Projects/DocuRAG-AI-Agent/frontend/src/components/PlanCard.tsx)

Add `comingSoon` prop for greyed-out disabled state.

---

## File Summary

| Action | File                      | Description                                   |
| ------ | ------------------------- | --------------------------------------------- |
| NEW    | `constants/pricing.ts`    | Shared pricing data                           |
| NEW    | `pages/LandingPage.tsx`   | Full landing page with all sections           |
| NEW    | `pages/UpgradePage.tsx`   | Upgrade page with plan comparison             |
| MODIFY | `App.tsx`                 | Update routes: `/` landing, `/home` dashboard |
| MODIFY | `components/PlanCard.tsx` | Add comingSoon prop                           |

---

## Verification Plan

### Manual Browser Testing

1. **Landing Page** (`http://localhost:5173/`)

   - [ ] Navbar sticky with blur on scroll
   - [ ] Hero, Features, How It Works, Pricing, Footer render
   - [ ] Section anchors scroll correctly
   - [ ] Auth-aware: Logged-in users see "Go to Dashboard"

2. **Mobile Responsive** (375px viewport)

   - [ ] Hamburger menu works
   - [ ] Sections stack vertically
   - [ ] Full-width buttons

3. **Dark Mode**

   - [ ] All sections respect theme colors

4. **Upgrade Page** (`/upgrade`, requires login)

   - [ ] Current plan badge shown
   - [ ] Coming Soon buttons disabled
   - [ ] Back link works

5. **CTA Actions**
   - [ ] "Get Started Free" → `/register`
   - [ ] "See how it works" → scrolls to `#how-it-works`
   - [ ] "Log in" → `/login`

### No Automated Tests

This is a UI-only feature. Manual browser testing is sufficient.
