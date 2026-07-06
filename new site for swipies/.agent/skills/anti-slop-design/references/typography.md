# Typography Reference

## Vetted Font Pairings by Aesthetic

Each pairing includes a Google Fonts CDN import and usage notes.
These are battle-tested combinations that read as designed, not generated.

---

### Editorial / Magazine

**Pairing A: Fraunces + DM Sans**
```html
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,700;1,9..144,300;1,9..144,700&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet"/>
```
- Fraunces: optical-size variable serif, beautiful at large sizes, italic is exquisite
- DM Sans: clean, unobtrusive body text
- Use: headlines in Fraunces 700 + italic 300, body in DM Sans 400

**Pairing B: Playfair Display + Jost**
```html
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,400&family=Jost:wght@300;400;500&display=swap" rel="stylesheet"/>
```
- Classic editorial serif + modern geometric sans
- Use: section titles italic, body in Jost 300/400

**Pairing C: Libre Baskerville + Source Sans 3**
```html
<link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,700;1,400&family=Source+Sans+3:wght@300;400&display=swap" rel="stylesheet"/>
```
- Sturdy editorial serif + neutral readable body
- Great for content-heavy or documentation sites

---

### Technical / Mono

**Pairing A: Space Mono + Geist Sans (via CDN)**
```html
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet"/>
```
Note: Geist is from Vercel. Load via unpkg:
```html
<link rel="stylesheet" href="https://unpkg.com/geist@1.3.0/dist/fonts/geist-sans/style.css"/>
```
- Space Mono for all UI labels, numbers, code
- Geist Sans for readable body text
- Keep body small (13–14px) and dense

**Pairing B: IBM Plex Mono + IBM Plex Sans**
```html
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:ital,wght@0,400;0,700;1,400&family=IBM+Plex+Sans:wght@300;400;500&display=swap" rel="stylesheet"/>
```
- Designed as a system — they pair perfectly
- Very legible at small sizes, great for dashboards

**Pairing C: Commit Mono + Inter... No. Use Commit Mono + Manrope**
```html
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;600&display=swap" rel="stylesheet"/>
```
Note: Commit Mono isn't on Google Fonts. Use this fallback for mono:
```css
font-family: 'SF Mono', 'Fira Code', 'Fira Mono', monospace;
```

---

### Brutalist / Raw

**Pairing A: Barlow Condensed + Barlow**
```html
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800;900&family=Barlow:wght@400;500&display=swap" rel="stylesheet"/>
```
- Condensed at massive sizes for impact
- Regular weight for body — same family, total contrast

**Pairing B: Anton + Work Sans**
```html
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Work+Sans:wght@300;400&display=swap" rel="stylesheet"/>
```
- Anton is a display grotesque — single weight, pure impact
- Work Sans for everything readable

**Pairing C: Oswald + Karla**
```html
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@600;700&family=Karla:ital,wght@0,400;1,400&display=swap" rel="stylesheet"/>
```
- Oswald: condensed, serious, poster-like
- Karla: humanist, slightly quirky body text

---

### Organic / Tactile

**Pairing A: Cormorant Garamond + Nunito Sans**
```html
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,600;1,300;1,600&family=Nunito+Sans:wght@300;400&display=swap" rel="stylesheet"/>
```
- Cormorant is a wine-region serif — incredibly refined at large sizes
- Nunito Sans: friendly, organic, approachable body

**Pairing B: Lora + Raleway**
```html
<link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,700;1,400&family=Raleway:wght@300;400;500&display=swap" rel="stylesheet"/>
```
- Classic editorial serif with a craft feel
- Raleway: elegant, geometric, light-weight default

**Pairing C: Crimson Pro + Mulish**
```html
<link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,600;1,400&family=Mulish:wght@300;400&display=swap" rel="stylesheet"/>
```

---

### Luxury / Refined

**Pairing A: Cormorant + Montserrat (sparse)**
```html
<link href="https://fonts.googleapis.com/css2?family=Cormorant:ital,wght@0,300;0,400;1,300&family=Montserrat:wght@300;400&display=swap" rel="stylesheet"/>
```
- Cormorant at 300 weight is almost whisper-thin — deeply elegant
- Montserrat for uppercase labels at 0.2em tracking ONLY
- Rule: Never Montserrat as body text. Only for UI labels, 11–12px, uppercase.

**Pairing B: EB Garamond + Didact Gothic**
```html
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;1,400&family=Didact+Gothic&display=swap" rel="stylesheet"/>
```
- EB Garamond: classical, proportional, beautiful in long text
- Didact Gothic: bare, neutral, almost invisible — lets the serif shine

**Pairing C: Tenor Sans + Josefin Sans**
```html
<link href="https://fonts.googleapis.com/css2?family=Tenor+Sans&family=Josefin+Sans:wght@300;400&display=swap" rel="stylesheet"/>
```
- Tenor Sans: wide, high-contrast, fashion-adjacent
- Josefin Sans: geometric, art-deco, refined

---

## Type Scale Templates

### Editorial scale
```css
--t-hero: clamp(4rem, 8vw, 8rem);       /* Fraunces 700 */
--t-section: clamp(2rem, 4vw, 3.5rem);  /* Fraunces 300 italic */
--t-subhead: 1.25rem;                    /* DM Sans 500 */
--t-body: 1rem;                          /* DM Sans 400 */
--t-label: 0.75rem;                      /* DM Sans 400, tracking 0.1em */
```

### Technical scale
```css
--t-hero: clamp(2.5rem, 5vw, 5rem);     /* Space Mono 700 */
--t-section: 1.5rem;                     /* Space Mono 700 */
--t-body: 0.875rem;                      /* Geist 400 */
--t-mono: 0.75rem;                       /* Space Mono 400 */
--t-label: 0.6875rem;                    /* Space Mono 400, tracking 0.08em */
```

### Luxury scale
```css
--t-hero: clamp(3rem, 6vw, 6rem);       /* Cormorant 300 */
--t-section: clamp(1.5rem, 3vw, 2.5rem); /* Cormorant 300 italic */
--t-body: 0.9375rem;                     /* Montserrat 300 */
--t-label: 0.6875rem;                    /* Montserrat 400, uppercase, tracking 0.2em */
```

---

## Anti-Patterns

- **Never use Inter for a display font** — it's a UI font, not a headline font
- **Never mix three serif families** — one serif max
- **Never use font-weight: 600 or 700 on body text** — use 400 or 500 max
- **Never track body text** — letter-spacing on paragraphs = amateur signal
- **Never use font-size below 12px for visible text** — 11px labels are the floor
- **Never use the same font-size for both heading and body** — contrast is required
- **Gradient text fills are an AI cliché** — ban them in all aesthetics except maximalist/retro
