# Layout Reference

## Anti-Slop Layout Patterns

The three-column feature card grid is dead. The hero-with-floating-mockup is dead.
These patterns are what real designers actually use.

---

## Core Principle: Structure over Decoration

AI designs use cards and shadows to create structure.
Real designs use **whitespace, borders, and typographic hierarchy** to create structure.

Rules:
- If you're using `box-shadow` as a primary layout element, you're doing it wrong.
- `border-radius: 12px` on everything = AI default. Either commit to zero rounding (brutalist/technical)
  or use rounding very selectively (one radius value, applied to ≤2 element types).
- Cards are containers of last resort. Ask: can this information live in a bordered section instead?

---

## Pattern 1: Editorial Column Grid

**Use for:** Portfolios, agencies, studios, services pages
**Aesthetic:** Editorial, Luxury, Organic

Structure: named grid with a label column + content column. Sections are rows of the grid.
Content bleeds across columns. Serif headline in the label area, prose in content area.

```html
<!-- Section structure -->
<section style="
  display: grid;
  grid-template-columns: 220px 1fr;
  border-top: 1px solid var(--border);
  min-height: 400px;
">
  <div style="padding: 3rem 2rem; border-right: 1px solid var(--border);">
    <div class="section-label">What we do</div>
    <h2 class="section-title">Services</h2>
  </div>
  <div style="padding: 3rem 3rem;">
    <!-- content here -->
  </div>
</section>
```

Key: The label column creates rhythm. Section numbering (01, 02, 03) in the label area
instead of a centered section heading feels editorial and intentional.

---

## Pattern 2: Full-Bleed Horizontal Rule Sections

**Use for:** Technical agencies, developer tools, startups
**Aesthetic:** Technical, Brutalist

Structure: No cards. Content is divided by 1px horizontal rules.
Each row has a clear structure: number | title | description | metadata.

```html
<div style="border-top: 1px solid var(--border);">
  <div style="
    display: grid;
    grid-template-columns: 60px 1fr 1fr 120px;
    align-items: start;
    padding: 2rem;
    border-bottom: 1px solid var(--border);
    gap: 2rem;
  ">
    <span class="mono-label">01</span>
    <span class="item-title">Discovery Call</span>
    <span class="item-desc">We understand your problem...</span>
    <span class="item-meta mono-label">Day 1</span>
  </div>
  <!-- repeat for each item -->
</div>
```

This works for: process steps, team members, services list, portfolio index.
The power is in the rigidity — every row the same structure, infinitely scalable.

---

## Pattern 3: Asymmetric Split Hero

**Use for:** Any site hero
**Aesthetic:** Any (with different fonts/colors)

Structure: Two unequal columns. Left: large headline + desc + CTA. Right: real content (terminal,
live data, code, stats table) — NOT a generic UI mockup or phone frame.

```html
<section style="
  display: grid;
  grid-template-columns: 55% 45%;
  min-height: calc(100vh - 60px);
  border-bottom: 1px solid var(--border);
">
  <div style="
    padding: 5rem 3rem;
    border-right: 1px solid var(--border);
    display: flex; flex-direction: column; justify-content: space-between;
  ">
    <div class="eyebrow-label"><!-- tag/badge --></div>
    <h1 class="hero-title"><!-- headline --></h1>
    <div>
      <p class="hero-desc"><!-- description --></p>
      <div class="cta-row"><!-- buttons --></div>
    </div>
  </div>
  <div style="
    background: var(--bg-alt);
    padding: 2.5rem;
    display: flex; flex-direction: column; gap: 1.5rem;
  ">
    <!-- Real content: terminal, stats, live feed, map, code block, etc. -->
    <!-- NOT: phone mockup, browser frame, floating cards with gradients -->
  </div>
</section>
```

The right column should show something **real and functional** — a terminal log,
a data table, a code snippet, a before/after comparison, stats with context.

---

## Pattern 4: Magazine Pull-Quote Layout

**Use for:** Case studies, about pages, testimonials
**Aesthetic:** Editorial, Organic, Luxury

Structure: Text content in one column. A large pull-quote or stat bleeds into the margin
or interrupts the flow unexpectedly.

```html
<div style="max-width: 680px; margin: 0 auto; padding: 4rem 2rem; position: relative;">
  <p>Regular paragraph content here...</p>

  <!-- Pull quote: bleeds into the margin -->
  <blockquote style="
    margin: 3rem -6rem 3rem 0;
    padding: 0 0 0 2rem;
    border-left: 3px solid var(--accent);
    font-family: var(--font-display);
    font-size: 1.5rem;
    font-style: italic;
    font-weight: 300;
    line-height: 1.4;
    color: var(--ink);
  ">
    "The most important sentence from this section, isolated and enlarged."
  </blockquote>

  <p>Content continues here...</p>
</div>
```

---

## Pattern 5: Dense Stats / Numbers Band

**Use for:** Social proof, metrics, credibility
**Aesthetic:** Technical, Brutalist, Editorial

NOT four equal-width cards with centered numbers. Instead: a ruled band with
numbers integrated with labels on the same line, or a tabular stat layout.

```html
<!-- Option A: Inline tabular stats -->
<div style="border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);">
  <div style="
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    divide-x: var(--border);
  ">
    <div style="padding: 2rem; border-right: 1px solid var(--border);">
      <div class="stat-big">18+</div>
      <div class="stat-label">Products shipped</div>
    </div>
    <!-- etc. -->
  </div>
</div>

<!-- Option B: Horizontal ticker-style stats (single line) -->
<div style="
  display: flex; gap: 0;
  border-top: 1px solid var(--border);
  overflow: hidden;
">
  <div style="padding: 1.2rem 2.5rem; border-right: 1px solid var(--border);">
    <span class="mono">18+</span> products
  </div>
  <div style="padding: 1.2rem 2.5rem; border-right: 1px solid var(--border);">
    <span class="mono">3 wks</span> avg. delivery
  </div>
  <!-- etc. -->
</div>
```

Key: in the tabular version, `stat-big` should be a large serif or mono number —
not a gradient, not a colored number, not animated counting. Just a big, confident number.

---

## Pattern 6: Portfolio as Index / Table

**Use for:** Work/portfolio sections
**Aesthetic:** Technical, Editorial

NOT a grid of project cards with thumbnail images and hover overlays.
Instead: a table-of-contents style list. Each project is one row. Numbers in the margin.
On hover, the row highlights — or a thumbnail appears absolutely positioned.

```html
<div>
  <div style="
    display: grid;
    grid-template-columns: 48px 1fr auto auto;
    padding: 1.5rem 2rem;
    border-bottom: 1px solid var(--border);
    align-items: baseline;
    gap: 2rem;
    cursor: pointer;
    transition: background 0.1s;
  " onmouseover="this.style.background='var(--bg-hover)'"
     onmouseout="this.style.background='transparent'">
    <span class="mono-label">01</span>
    <span class="project-title">Multi-Agent Support System</span>
    <span class="project-tags">LangGraph · FastAPI</span>
    <span class="project-year mono-label">2025</span>
  </div>
  <!-- repeat -->
</div>
```

---

## What NOT to do (Layout anti-patterns)

| Pattern | Why it's AI slop | Alternative |
|---|---|---|
| 3-column icon cards | Statistical default | Ruled list (Pattern 2) |
| Hero with floating UI mockups | Overused since 2021 | Split hero with real content (Pattern 3) |
| Bento grid | Trendy → cliché | Editorial columns (Pattern 1) |
| Full-page animated gradient bg | Screams "AI made this" | Texture + solid base color |
| Testimonial carousels with avatar circles | Generic | Pull quotes in running text (Pattern 4) |
| Particle field / Three.js particles | Most common AI tell | Static background or subtle SVG texture |
| Centered everything | Safe = boring | Left-aligned, asymmetric grids |
| 4 equal stat cards | Templated | Stats band (Pattern 5) |
| Portfolio card grid | Generic | Portfolio as index (Pattern 6) |
