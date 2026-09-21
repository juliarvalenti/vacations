# Styling a single vacation

Each trip can look different from the others. There are three levels, all opt-in by filename,
and you can mix them:

| Level | File | Use it for |
|---|---|---|
| 1 | `content/<trip>.json` → `theme` | colours and fonts, no code |
| 2 | `src/styles/trips/<trip>.css` | CSS tweaks to the standard page |
| 3 | `src/layouts/trips/<trip>.astro` | a completely bespoke page |

## Level 3 — a bespoke page

Copy `src/layouts/trips/_starter.astro` to `src/layouts/trips/<trip>.astro`. That trip now renders
your file instead of the standard page (`default.astro`). Inside it you write ordinary HTML + CSS
and drop in shared pieces wherever you want them — `<Hero>`, `<Grid>`, `<Carousel>`, `<Photo>` —
all fed from the trip's JSON (`trip.sections`, `trip.hero`, `allImages(trip)`). Keep the `<Base>`
wrapper: it provides fonts, theme, the sticky top bar and the lightbox.

The starter file is commented and shows the common moves (a section by name, two photos
side by side, a free-text intro).

## Level 1 — knobs in the JSON (no CSS needed)

Open `content/<trip>.json` and add/edit the `theme` block near the top. Every key is optional;
leave one out and the site default is used.

```json
"theme": {
  "accent": "#c8102e",              // eyebrows, active nav item, section numbers
  "bg": "#f7f5f0",                  // page background (light mode)
  "fg": "#1b1917",                  // text colour (light mode)
  "bgDark": "#101214",              // page background (dark mode)
  "fgDark": "#ece7de",              // text colour (dark mode)
  "stage": "#121110",               // carousel background
  "displayFont": "Shippori Mincho", // headings — any Google Fonts family name
  "bodyFont": "Inter"               // body text — any Google Fonts family name
}
```

Fonts: pick anything from https://fonts.google.com and use its name exactly as shown there.
Colours: any CSS colour (`#hex`, `rgb(...)`, `oklch(...)`).

`content/japan.json` has a working example.

## Level 2 — a CSS file for the trip

For anything the knobs don't cover, create `src/styles/trips/<trip>.css` (same name as the JSON file).
It is loaded automatically on that trip's page only.

Every trip page has `data-trip="<trip>"` on the `<html>` element, so **start every rule with
`[data-trip="<trip>"]`** to keep it from affecting other trips:

```css
[data-trip="london"] h2 { font-variant: small-caps; }
[data-trip="london"] .carousel { border-radius: 0; }
```

`src/styles/trips/london.css` has a working example.

### Useful hooks

| Selector | What it is |
|---|---|
| `.hero`, `.cover` | full-bleed cover photo + title block |
| `.section`, `.section header`, `.num` | a numbered section and its heading row |
| `.eyebrow` | small uppercase label (location, year) |
| `.grid`, `.grid .photo` | masonry photo grid |
| `.carousel`, `.track`, `.slide`, `.arrow`, `.bar` | carousel and its controls |
| `.bar` (top), `.ftoc` | sticky top bar, floating section list |

Site-wide defaults (colours, fonts, spacing) live in `src/styles/global.css`.

## Seeing your changes

```
npm install     # first time only
npm run dev     # then open http://localhost:4321/vacations/
```

Edits show up instantly. When you're happy: commit and push to `main`, and the live site
rebuilds itself in about a minute.
