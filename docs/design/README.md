# PowerTrackZ Design Tokens

**English** | [Português](README.pt-BR.md)

## Overview

The look of the frontend is defined by a single set of design tokens: CSS variables holding the colors, typography, spacing, border radii and shadows. They live in [`services/frontend_service/static/css/base/tokens.css`](../../services/frontend_service/static/css/base/tokens.css). Style sheets use the tokens instead of fixed values, so a color or size change is made in one place.

## Style sheet organization

```text
static/css/
├── base/                  # loaded by every page (base.html)
│   ├── tokens.css         # design tokens
│   ├── elements.css       # reset and base elements (html, body, main, .container)
│   └── components.css     # navigation bar, modals, forms, buttons, tables, footer
└── pages/                 # one file per page, loaded only by that page (extra_css block)
    ├── home.css
    ├── infrastructure.css
    ├── analysis.css
    └── scalability.css
```

New rules go to `components.css` when they serve more than one page, and to the page file when they are specific to it. Scripts do not create CSS: they apply classes. Only styles computed at runtime, such as positions, widths and the color of each configuration in the graphs, stay in JavaScript.

## Colors

### Accent

There is a single accent color; its state variations derive from it.

| Token | Value | Use |
|---|---|---|
| `--color-accent` | `#236dc9` | primary buttons, links, selection, highlighted icons |
| `--color-accent-hover` | `#1d5fb0` | hover and active states; accent text on light backgrounds |
| `--color-accent-light` | `#6ea6e6` | accent on the dark surface (active navigation item) |
| `--color-accent-soft` | `#eaf2fb` | soft background (badges, icons, selected row) |
| `--color-accent-ring` | `rgba(35, 109, 201, 0.25)` | focus ring and translucent borders |
| `--color-on-accent` | `#fff` | text on the accent and on status colors |

The accent has the same hue as the chart blue (`#2a78d6`), darkened to meet AA contrast.

### Neutrals

A blue-gray family, with text in three levels.

| Token | Value | Use |
|---|---|---|
| `--color-text-strong` | `#18222d` | headings and values |
| `--color-text` | `#304556` | default text |
| `--color-text-muted` | `#607080` | labels, hints and secondary text |
| `--color-bg` | `#f5f7f9` | page background |
| `--color-surface` | `#fff` | cards, panels and modals |
| `--color-surface-muted` | `#f8fafc` | table headers and soft hover |
| `--color-surface-sunken` | `#eef2f5` | recessed areas (tracks, disabled fields) |
| `--color-surface-translucent` | `rgba(255, 255, 255, 0.88)` | overlays on top of content |
| `--color-border` | `#e2e7ec` | dividers and card borders |
| `--color-border-strong` | `#cbd5df` | field and control borders |
| `--color-overlay` | `rgba(24, 34, 45, 0.5)` | backdrop behind modals |
| `--color-surface-inverse` | `#22313f` | navigation bar |
| `--color-on-inverse` / `--color-on-inverse-muted` | `#fff` / 85% | text on the navigation bar |
| `--color-inverse-hover` | `rgba(255, 255, 255, 0.1)` | hover on the navigation bar |

### Status

Kept apart from the accent and always with the same meaning: success (completed action, improvement), warning (attention, channel overlap) and error (failure, regression). Each has a text color, a soft background and a border.

| Status | Text | Soft background | Border |
|---|---|---|---|
| Success | `--color-success` `#15803d` | `--color-success-soft` `#ecfdf3` | `--color-success-border` `#86efac` |
| Warning | `--color-warning` `#b45309` | `--color-warning-soft` `#fffbeb` | `--color-warning-border` `#fcd34d` |
| Error | `--color-danger` `#b42318` | `--color-danger-soft` `#fef2f2` | `--color-danger-border` `#fca5a5` |

Color must not be the only signal: the changes in the summary panel, for example, also use an arrow and a sign.

### Graphs

The legend lines of the conflict graphs use `--color-graph-conflict` (`#d62828`), `--color-graph-overlap` (`#c3cad2`) and `--color-graph-resolved`. They repeat the edge colors drawn by Cytoscape; aligning the graphs with the palette is planned in #96.

## Contrast

Every text combination in use meets the AA level (4.5:1 for normal text, 3:1 for large text).

| Text | on `surface` | on `surface-muted` | on `bg` | on `surface-sunken` |
|---|---|---|---|---|
| `text-strong` | 16.09 | 15.37 | 14.98 | 14.29 |
| `text` | 9.95 | 9.51 | 9.26 | 8.84 |
| `text-muted` | 5.09 | 4.86 | 4.74 | 4.52 |
| `accent` | 5.12 | 4.89 | 4.77 | 4.55 |
| `success` | 5.02 | 4.79 | 4.67 | 4.46 ✗ |
| `warning` | 5.02 | 4.80 | 4.68 | 4.46 ✗ |
| `danger` | 6.57 | 6.28 | 6.12 | 5.84 |

- `on-accent` (white) on `accent`: 5.12; on `accent-hover`: 6.33; on `warning`: 5.02; on `danger`: 6.57; on `text-muted` (secondary button): 5.09.
- On the navigation bar: `on-inverse` 13.30; `on-inverse-muted` 10.05; `accent-light` 5.23.
- Status colors on their own soft background: success 4.76; warning 4.84; error 6.01.
- Success or warning text must not sit on `surface-sunken` or `accent-soft` (4.44 to 4.46).

Contrast was also checked on the rendered pages, for every visible text, at widths of 1280, 1000, 800 and 600 px.

## Typography

| Token | Value | Use |
|---|---|---|
| `--font-family-base` | system font stack | all text |
| `--font-size-xs` | `0.75rem` | badges, uppercase labels, captions |
| `--font-size-sm` | `0.85rem` | helper text, compact tables, hints |
| `--font-size-md` | `0.9rem` | buttons, fields, table bodies |
| `--font-size-base` | `1rem` | default text |
| `--font-size-lg` | `1.15rem` | card and section titles |
| `--font-size-xl` | `1.5rem` | panel and modal titles |
| `--font-size-2xl` | `2rem` | highlighted numbers |
| `--font-size-display` | `clamp(2rem, 4vw, 3rem)` | page title |
| `--font-weight-regular` … `--font-weight-bold` | 400, 500, 600, 700 | weights |
| `--line-height-tight` / `--line-height-base` | 1.2 / 1.5 | heading and text line height |

The root stays at `16px`, the base of every `rem` value.

## Spacing, radii and shadows

| Token | Value |
|---|---|
| `--space-1` … `--space-7` | `0.25rem`, `0.5rem`, `0.75rem`, `1rem`, `1.5rem`, `2rem`, `3rem` |
| `--radius-sm` | `4px`: buttons, fields, small badges |
| `--radius-md` | `8px`: cards and panels |
| `--radius-lg` | `12px`: large panels and strategy buttons |
| `--radius-pill` / `--radius-round` | `999px` / `50%`: pills and circles |
| `--shadow-sm` | light elevation (cards) |
| `--shadow-md` | medium elevation (panels, hovered cards) |
| `--shadow-lg` | floating elements (modals, overlays, add button) |
| `--shadow-focus` | focus ring with `--color-accent-ring` |

Spacing tokens are meant for new code; existing spacing has not been converted yet.

## Bootstrap

Bootstrap 5.3 is still used. The tokens set its variables (`--bs-primary`, `--bs-link-color`, `--bs-body-color`, `--bs-border-color`, `--bs-focus-ring-color`) in `tokens.css` and the button variables (`--bs-btn-*`) of `.btn-primary`, `.btn-secondary`, `.btn-outline-primary`, `.btn-outline-secondary` and `.btn-outline-danger` in `components.css`, so hover, focus and active states use the token colors. Native controls (checkboxes) use the accent through `accent-color`.

## Exceptions

Fixed values that remain outside the tokens:

- `font-size: 16px` on the root, which defines the `rem`;
- `inherit` in the Leaflet overrides;
- colors computed at runtime in JavaScript (the color of each configuration in graphs and charts), handled in #96.
