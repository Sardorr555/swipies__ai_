# Color Reference

## Color System Templates by Aesthetic

Each system is defined as CSS variables. Copy the relevant block and customize.

---

## Editorial / Magazine

```css
:root {
  --bg:      #f5f0e8;   /* warm cream — NOT pure white */
  --bg2:     #ede8de;   /* slightly darker cream for alternate sections */
  --bg3:     #e4ddd1;   /* borders and dividers background */
  --ink:     #1a1814;   /* warm near-black — NOT #000 */
  --muted:   #7a7568;   /* secondary text */
  --muted2:  #a09890;   /* hints, placeholders, disabled */
  --border:  #1a181418; /* 10% ink */
  --border2: #1a181430; /* 19% ink */
  --accent:  #c8860a;   /* amber — one accent only */
  --accent2: #fdf3dc;   /* light amber for backgrounds */
}
```

Notes:
- The warm cream base immediately separates from AI defaults (white/dark)
- Amber accent is earned and specific — not a default
- No blue, no purple, no teal in this palette

---

## Technical / Mono

```css
:root {
  --bg:       #0c0c0f;  /* near-black with blue tint */
  --bg2:      #111116;  /* surface */
  --bg3:      #161620;  /* elevated surface */
  --text:     #e8e6e0;  /* warm off-white — NOT #fff */
  --muted:    #6e6c78;  /* secondary text */
  --muted2:   #45434e;  /* hints */
  --border:   #ffffff0f; /* 6% white */
  --border2:  #ffffff18; /* 9% white */
  --accent:   #e8a820;   /* amber status color */
  --accent2:  #e8a82015; /* amber background tint */
  --green:    #22c55e;   /* for live/online indicators */
  --red:      #ef4444;   /* for error/offline */
}
```

Notes:
- Blue-tinted near-black (not purple, not pure black)
- Amber accent for "active" states — status-meaningful, not decorative
- Green/red only for semantic meaning (live, error), not for style

---

## Brutalist / Raw

```css
:root {
  --bg:      #ffffff;   /* pure white — brutalism earns it */
  --bg-alt:  #f0f0f0;   /* one gray for alternate rows */
  --ink:     #000000;   /* pure black — brutalism earns this too */
  --muted:   #666666;   /* mid gray */
  --border:  #000000;   /* full black borders */
  --accent:  #ff3800;   /* aggressive orange-red */
  --accent2: #ffdd00;   /* alternate: electric yellow */
}
```

Notes:
- Brutalism is the ONE aesthetic where pure #000 and #fff work — because the rawness is intentional
- ONE accent only: either red, yellow, or electric blue — never combined
- No shadows. No gradients. Colors are either black, white, gray, or the one accent.

---

## Organic / Tactile

```css
:root {
  --bg:       #f9f5ef;  /* natural linen */
  --bg2:      #f0ebe2;  /* slightly warmer */
  --bg3:      #e6dfd5;  /* earth surface */
  --ink:      #2c2418;  /* warm deep brown — feels natural */
  --muted:    #8a7d6e;  /* warm gray-brown */
  --muted2:   #b0a495;  /* light warm gray */
  --border:   #2c241818; /* 10% ink */
  --accent:   #7a5c3a;   /* warm terracotta/sienna */
  --accent2:  #4a7c59;   /* sage green alternative accent */
  --accent3:  #c17f3b;   /* amber clay */
}
```

Notes:
- Can use two accents in organic (terracotta + sage) — they feel natural together
- Avoid any "digital" blue, purple, or neon
- The palette should feel like it could be found in a ceramics studio

---

## Luxury / Refined

```css
:root {
  /* Light variant */
  --bg:       #faf8f4;   /* bone white */
  --bg2:      #f3f0eb;   /* warm surface */
  --ink:      #141210;   /* deep warm black */
  --muted:    #8a8680;   /* stone gray */
  --border:   #14121010; /* 6% ink — very thin */
  --border2:  #1412101a; /* 10% ink */
  --accent:   #9d7c45;   /* antique gold */

  /* Dark variant */
  --bg:       #100f0d;   /* deep warm black */
  --bg2:      #181714;   /* surface */
  --ink:      #f0ece6;   /* warm cream */
  --muted:    #6e6c68;   /* warm dark gray */
  --border:   #f0ece610; /* 6% white */
  --accent:   #c9a96e;   /* warm gold on dark */
}
```

Notes:
- Luxury relies on restraint — the palette does very little
- Accent gold is used SPARINGLY — one CTA, one border accent, nothing else
- Never red, blue, or green in luxury — they feel "active" not refined

---

## Banned Palettes (Do Not Use)

These combinations are now AI-design fingerprints:

### The AI Dark Default
```
bg: #0a0a0a or #111111
accent: #7c3aed (violet) or #8b5cf6 (purple)
text: #e5e7eb
secondary: #6b7280
```
**Why it's slop:** Every AI-generated dark site uses this. The purple accent is now
the single biggest signal that a site was AI-built. Avoid even if you like purple.

### The AI Light Default
```
bg: #ffffff
accent: #3b82f6 (blue) or #6366f1 (indigo)
text: #111827
secondary: #6b7280
```
**Why it's slop:** Tailwind CSS defaults. Millions of AI-generated sites use exactly this.

### The "Modern Startup" Trap
```
bg: #0d1117 (GitHub dark)
accent: #58a6ff (GitHub blue) or any neon
card bg: rgba(255,255,255,0.05)
border: rgba(255,255,255,0.1)
```
**Why it's slop:** Developer community aesthetic, completely saturated. Fine for GitHub,
terrible for an agency or product that wants to stand out.

### The Gradient Overuse
```css
/* Any of these as primary design elements: */
background: linear-gradient(135deg, #667eea, #764ba2);
background: linear-gradient(to right, #f093fb, #f5576c);
-webkit-background-clip: text; /* gradient text */
box-shadow: 0 0 40px rgba(124, 58, 237, 0.5); /* glow */
```
**Why it's slop:** Gradients were the signature of 2023–2024 AI design.
If your site has gradient text headlines, it reads as AI-generated immediately.

---

## The One-Color Rule

Most great sites run on ONE non-neutral color. Fight the urge to use 3-4 accent colors.

- One accent = intentional, designed, memorable
- Two accents = acceptable only if they're semantically meaningful (e.g. green for success, amber for warning)
- Three accents = visual noise, looks generated

The accent should appear in approximately 3 places: one CTA button, one hover state,
one typographic accent or decorative detail. That's it.
