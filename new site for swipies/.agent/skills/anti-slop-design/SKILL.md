---
name: anti-slop-design
description: >
  Produce frontend web designs (HTML, React, CSS) that are unmistakably human-crafted and
  avoid every known AI-generated design cliché. Use this skill whenever the user asks to build
  or redesign a website, landing page, portfolio, dashboard, UI component, or any web artifact —
  especially when they mention words like "modern", "clean", "professional", "premium", "unique",
  "not generic", "avoid AI look", "human feel", or "stand out". Also use it proactively whenever
  you are about to generate a website or UI, even if the user didn't ask explicitly — because
  AI-generated design defaults are now so recognizable they actively hurt credibility.
  This skill overrides any default design instincts. Read it fully before writing a single line of code.
---

# Anti-Slop Design Skill

You are about to build a UI. Before you write one line of code, read this skill completely.
AI-generated websites are now instantly recognizable and damage trust. Your job is to produce
something that feels **genuinely designed**, not statistically averaged.

---

## Step 1 — Run the Slop Checklist (pre-flight)

Before designing, ask yourself: am I about to reach for any of these?

### 🚫 Banned colors
- Purple (`#7c3aed`, `#8b5cf6`, `#a78bfa`, or any violet) as a primary brand color
- Purple-to-blue gradients on dark backgrounds
- Teal-on-dark as the sole accent
- Neon glow effects on any color (`box-shadow: 0 0 20px`)
- Pure `#ffffff` white or pure `#000000` black as the base — they read flat and lifeless

**Instead:** Off-whites (`#f5f0e8`, `#fafaf5`, `#f0ede6`), warm blacks (`#0e0d09`, `#111108`),
or fully committed dark navies (`#080c14`). Pick an accent that's *earned* — amber, rust, forest
green, burgundy, slate blue — not the default AI palette.

### 🚫 Banned typography
- Inter (the single most overused AI font — banned entirely)
- Roboto, Arial, system-ui as display fonts
- "Space Grotesk" (was trendy in 2022, now a slop signal)
- Gradient text fills on hero headings (`-webkit-background-clip: text`)
- All-caps tracking-widened subheadings as section labels (overused pattern)

**Instead:** Make a deliberate pairing decision. See `references/typography.md` for vetted options.
The pairing *is* the identity. Serif + mono, editorial serif + grotesque, display slab + clean sans.

### 🚫 Banned layouts
- Three equal-width feature cards with icons on top
- Full-viewport hero with centered text + two CTA buttons + floating UI mockups
- "Bento grid" of cards with rounded corners and subtle shadows
- Particle field or animated mesh gradient as hero background (Three.js particles = instant slop)
- Frosted glass cards (`backdrop-filter: blur`) as a primary design element
- Staggered fade-up animation on every single section

**Instead:** Read `references/layouts.md` for editorial, brutalist, and asymmetric patterns that
feel designed, not generated.

### 🚫 Banned copy patterns
- "Supercharge your workflow"
- "The future of X is here"
- Any sentence with "seamlessly", "effortlessly", "powerful", "robust"
- Three benefit columns with emoji icons and one-line descriptions
- Testimonials with initials avatars in circles

### 🚫 Banned micro-details
- `border-radius: 12px` or `16px` on every card (everything rounded = AI tell)
- Identical border-radius across all elements
- `opacity: 0.7` muted text on dark backgrounds (use a real color from your palette)
- `gap: 1rem` grid layouts with 4 identical stat cards

---

## Step 2 — Choose a Real Aesthetic Direction

Do not design "in general." Pick one of these directions and commit fully.
Half-committed = slop. The aesthetic must be visible in every detail.

### A. Editorial / Magazine
Inspired by print: asymmetric grid, serif headline, numbered sections, ruled lines as structure.
Reference: Are.na, Stripe Press, NYT Cooking, Futura.
- Font: Playfair Display or Fraunces (display) + DM Sans or Neue Haas (body)
- Color: Cream/paper base, single ink color, one accent (amber or brick red)
- Grid: Named columns, content bleeds, pull quotes, large white space
- NO cards. Structure comes from borders and columns, not boxes.

### B. Technical / Mono
Inspired by developer tools, terminals, data systems. Credibility through density and precision.
Reference: Linear, Vercel, shadcn, Oxide Computer.
- Font: Space Mono or Berkeley Mono (headings/UI) + Inter... actually NO. Use Geist or Commit Mono.
- Color: Near-black base, warm off-white text, single amber/green status accent
- Grid: Dense, ruled, tabular. Numbers aligned. Pixel-precise.
- Details: 1px borders, no border-radius or very minimal (2-4px), monospaced data values

### C. Brutalist / Raw
Inspired by raw HTML, print protest design, bold typography over aesthetics.
Reference: Balenciaga.com (old), Bloomberg Businessweek, brutalistwebsites.com
- Font: A grotesque at extreme weights (Bebas Neue, Barlow Condensed, Anton) + a neutral body
- Color: Black + white + ONE aggressive accent (yellow, red, electric blue)
- Grid: Full bleed, overflowing text, deliberate collision of elements
- NO rounded corners. NO shadows. Borders are structural, not decorative.

### D. Organic / Tactile
Inspired by craft, materials, physical texture. Anti-digital.
Reference: Are.na, small studio sites, Loewe, Massimo Dutti digital.
- Font: A humanist serif (Lora, Crimson Pro, Cormorant Garamond) + a lightweight grotesque
- Color: Warm sand, terracotta, sage green, natural linen. Avoid digital primaries.
- Grid: Organic rhythm, uneven spacing that feels hand-laid, not aligned to a strict grid
- Details: SVG noise texture overlay, natural-feeling transitions (not ease-in-out everywhere)

### E. Luxury / Refined
Inspired by high-end fashion, galleries, architecture portfolios.
Reference: Bottega Veneta, Zaha Hadid Architects, Celine.
- Font: A refined thin serif (Garamond, Cormorant, Didot) + uppercase spaced sans for labels
- Color: Near-white or near-black. NO colors except one: warm gold, deep wine, or forest.
- Grid: Extreme whitespace. Content is sparse. Nothing competes with the hero statement.
- Details: Very thin borders (0.5px), no decorative elements, motion is slow and intentional

---

## Step 3 — Typography Rules

Read `references/typography.md` for the full font pairing guide. Key rules:

1. **Always pair two fonts with intentional contrast** — a display font and a body/UI font.
   Never use a single font family for everything.
2. **Establish a real type scale** — not just sm/base/lg. Pick 4-5 sizes and stick to them.
   Hero: 5–8rem. Section title: 2–3rem. Body: 15–16px. Label: 11–12px mono.
3. **Vary weight dramatically** — a 300 italic next to a 700 upright is more interesting than
   everything at 500.
4. **Line-height is personality** — tight (0.95–1.05) for headlines, loose (1.65–1.75) for body.
5. **Letter-spacing is not decoration** — use it only for ALL-CAPS labels (0.08–0.12em),
   never on body text, never on display headlines.

---

## Step 4 — Color System Rules

1. **Start with a base** — not pure white, not pure black. Something with temperature.
2. **Define 2–3 neutrals** from that base (lighter, darker, muted text color).
3. **Pick ONE accent** — only one. It should be unusual for your industry.
4. **Derive everything from those values** — no reaching for random colors mid-design.
5. **Test contrast** — body text must be readable. Muted text must still be legible.
6. **Never use opacity hacks** — `color: rgba(0,0,0,0.5)` is lazy. Pick an actual muted color.

---

## Step 5 — Motion & Interaction Rules

AI-generated sites animate everything with the same `fadeUp + stagger` pattern. Avoid it.

**Rules:**
- If you animate, animate ONE thing on page load — the hero. Make it count.
- Scroll reveals: max 2–3 sections, not every element. Use `IntersectionObserver`.
- Hover states should feel immediate and mechanical (0.1–0.15s), not floaty (0.3–0.4s ease).
- NO particle fields, NO animated mesh gradients, NO floating 3D objects in heroes.
- Transitions in a terminal/technical design should feel instant. Brutalist = no animation.
- Reserve slow, graceful animation (0.6–1s) for luxury/editorial aesthetics only.

---

## Step 6 — Final Gut-Check Before Shipping

Before returning your code, ask:

1. If I saw this on Awwwards or Typewolf, would it fit? Or would it look like a template?
2. Can I name the aesthetic direction in one word? (Editorial / Brutalist / Technical / Organic / Luxury)
3. Is every design decision intentional or is it a default I didn't question?
4. Does the font pairing feel like a real typographer chose it?
5. Is the color palette something I'd find in a real brand guide, or is it "dark mode purple"?
6. Does it have a detail — one unexpected, memorable thing — that makes it *designed*?

If any answer is "I'm not sure", fix it before shipping.

---

## Reference files

- `references/typography.md` — Vetted font pairings by aesthetic, Google Fonts CDN links, scale examples
- `references/layouts.md` — Anti-slop layout patterns with HTML structure sketches
- `references/colors.md` — Color system templates per aesthetic, banned palette reference
