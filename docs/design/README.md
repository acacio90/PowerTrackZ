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
│   └── components.css     # navigation, buttons, fields, panels, tables, chips and tags, modals, footer
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

The colors of the configurations in the conflict graphs and of the series in the scalability test charts come from an eight-color categorical palette, always in the same order:

| Position | Token | Color |
|---|---|---|
| 1 | `--color-graph-series-1` | blue `#2a78d6` |
| 2 | `--color-graph-series-2` | orange `#eb6834` |
| 3 | `--color-graph-series-3` | aqua `#1baf7a` |
| 4 | `--color-graph-series-4` | yellow `#eda100` |
| 5 | `--color-graph-series-5` | pink `#e87ba4` |
| 6 | `--color-graph-series-6` | green `#008300` |
| 7 | `--color-graph-series-7` | violet `#4a3aa7` |
| 8 | `--color-graph-series-8` | red `#e34948` |

**Assignment.** The configurations present in both graphs (original and proposed) are sorted by band, bandwidth and channel, and each one receives, in that order, a fixed combination of color and node shape. The same configuration therefore has the same color and shape in both graphs and in the legends; when the analysis brings new configurations, the original graph is recolored too. Colors no longer come from the hash computed by analysis_service (the `cor` and `proposed_cor` fields remain in the API response, but the interface does not use them).

**Color and shape.** In the graphs, any node can sit next to any other, so the palette must work for every pair, not only for neighboring colors. That is why color is combined with shape:

- configurations 1 to 8: the eight colors, as circles, except orange (square) and red (triangle), which are confused with other colors by people with color vision deficiency;
- 9th to 28th: the colors repeat as squares, triangles, diamonds and hexagons, and each shape only receives colors that can be told apart;
- from the 29th configuration on, the combinations repeat in the same order. In that case, the legend, which lists the channel, bandwidth and band of each combination, is the reference.

The full sequence is `CONFIG_STYLE_SEQUENCE`, in `analysis.js`.

**Color vision validation.** The palette was checked with the categorical palette validator (OKLab separation for protanopia, deuteranopia and tritanopia):

- between neighboring colors in the order, it passes every check (worst pair: yellow and aqua, ΔE 9.1 in protanopia; normal vision: ΔE 19.6);
- across all pairs, five combinations fall below the minimum: orange with yellow, pink, green and red, and pink with red (the worst, orange and green, at ΔE 3.2 in protanopia). In all of them the two configurations have different shapes, which was checked for the 28 combinations;
- yellow, pink and aqua are below 3:1 on white; that is why nodes carry the AP name and the legend describes each configuration in text.

Edges use `--color-graph-conflict` (`#d62828`) for conflicts, `--color-graph-overlap` (`#c3cad2`) for overlap without conflict and `--color-graph-resolved` (resolved conflict, dashed). The border of changed APs uses `--color-text-strong`, and edge labels use `--color-text-muted` on `--color-surface`. JavaScript reads these tokens from the CSS, so the colors of graphs, legends and charts change in one place.

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

## Components

Each kind of component has a single style, defined in `components.css`. Pages only add what is specific to them (width, position, columns), without redefining colors, borders, radii or shadows.

### Buttons

Variants by role, on top of Bootstrap's `.btn`:

| Role | Class | Look | Examples |
|---|---|---|---|
| Primary | `.btn-primary` | filled with the accent | Save, Run analysis, Generate, Load APs |
| Secondary | `.btn-secondary` | neutral outline | Cancel, Test connection, Refit, Analysis |
| Danger | `.btn-danger` | red outline, filled on hover | Delete selected, delete run |
| Subtle | `.btn-ghost` | text only, soft background on hover | Edit in the table, View, CSV, JSON |

Two sizes: default and `.btn-sm`. States (hover, active, disabled and focus) follow the same mechanism in every variant. One primary action per area; destructive actions use danger even when they are secondary. Choice components, such as the strategy selector on the Analysis page, the AP loading sources and the map's floating button, have their own style and do not use these variants.

### Panels

`.panel` is the standard surface for cards and sections (background, border, `md` radius, `sm` shadow and `--space-5` padding). Modifiers:

| Class | Use |
|---|---|
| `.panel-compact` | less padding (summaries, embedded forms) |
| `.panel-flush` | almost no padding (graph frames) |
| `.panel-muted` | neutral background and no shadow (indicators, blocks inside another panel) |
| `.panel-floating` | elements laid over the content (analysis progress) |

### Tables

`.app-table` is the standard table (neutral header background, rows separated by a border, hover highlight), inside `.app-table-shell` (outline) and `.app-table-wrap` (horizontal scroll). `.app-table-compact` is the dense version, used for data tables and the run history.

### Chips and tags

- `.chip`: interactive, pill-shaped (spectrum map shortcuts).
- `.tag`: informative only; `.tag-accent` to highlight (new configuration, data source) and `.tag-outline` for outlined labels (break points).

### Form fields

Text, number and select fields share a single style, applied to the element and to Bootstrap's `.form-control` and `.form-select` classes: `border-strong` border, `sm` radius, accent focus ring and a recessed background when disabled. The icon next to a field (`.input-group-text`) follows the same border and height.

### Keyboard focus

Every interactive element shows focus when navigating with the keyboard: buttons and fields with the focus ring (`--shadow-focus`), and links, `summary` elements and other controls with an accent outline (`:focus-visible`), which uses the light accent on the navigation bar.

## Bootstrap

Bootstrap 5.3 is still used, for these components: buttons (`.btn`, `.btn-sm`), fields (`.form-control`, `.input-group`), system message alerts (`.alert`), the settings modal, the close button (`.btn-close`) and a few spacing utilities (`me-2`, `mt-4`). Its relation to the tokens is:

- in `tokens.css`, its global variables (`--bs-primary`, `--bs-link-color`, `--bs-body-color`, `--bs-border-color`, `--bs-focus-ring-color`) point to the tokens;
- in `components.css`, button variants are defined through the `--bs-btn-*` variables, so hover, active, focus and disabled states are still Bootstrap's, with the token colors;
- `.form-control`, `.form-select` and `.input-group-text` get the single field style;
- alerts (`.alert-success`, `.alert-warning`, `.alert-danger`) use the status colors through the `--bs-alert-*` variables;
- the dark backdrop of the settings modal comes from `.modal` itself, so Bootstrap's `.modal-backdrop` is hidden.

Cards use `.panel`, not Bootstrap's `.card`. Native controls (checkboxes) use the accent through `accent-color`.

## Exceptions

Fixed values that remain outside the tokens:

- `font-size: 16px` on the root, which defines the `rem`;
- `inherit` in the Leaflet overrides;
- the color of each legend swatch and chart series, applied by JavaScript from the palette tokens.

The style sheets do not use `!important`: the overrides of Leaflet (`.map-container .leaflet-*`) and of the inventory rows win through selector specificity.

## Interface text

The interface is written in Brazilian Portuguese, with full accentuation. Code comments and log messages may remain unaccented, following the code convention.

### Conventions

- Capital letter only on the first word of titles, labels and buttons ("Salvar alterações", "Metadados da execução"), except proper names and acronyms (AP, Zabbix, JSON).
- Buttons state the action in the infinitive: "Executar análise", "Carregar APs", "Excluir selecionados".
- No exclamation marks. States in progress end with an ellipsis ("Salvando…"); confirmations are short and use the participle ("Configuração salva.").
- Numbers with a decimal comma and the unit separated by a space ("2,4 GHz", "60 s", "84,53 kWh").

### Error messages

Every error message says what happened and what to do, in that order:

- "Não foi possível carregar o grafo. Recarregue a página." (the graph could not be loaded; reload the page)
- "A execução ainda está em andamento. Cancele-a antes de excluir." (the run is still in progress; cancel it before deleting)
- "Usuário ou senha inválidos. Confira as credenciais do Zabbix." (invalid user or password; check the Zabbix credentials)

Field validation messages state the expected value ("Informe um inteiro entre 2 e 1000."). The services return messages in the same format, and the interface shows them as received; when a service does not respond, the interface shows "Não foi possível contatar o serviço. Confira se os serviços estão no ar e tente de novo.".

### Glossary

| Term (pt-BR) | Use |
|---|---|
| AP | Access point. "AP" in running text and labels; "ponto de acesso" spelled out in titles and descriptions. |
| Faixa | Band: 2.4, 5 or 6 GHz. In forms and tables, "Faixa" (not "Frequência"). |
| Largura (de banda) | Bandwidth: 20, 40, 80 or 160 MHz. |
| Canal | The AP's primary channel (or the pair, such as 7+11, at 40 MHz in 2.4 GHz). |
| Configuração | Combination of band, bandwidth and channel of an AP. |
| Perfil | Configuration available to the strategies; k is the number of profiles in a band. |
| Conflito | Pair of APs with overlapping coverage and overlapping channels (interference greater than zero). Do not use "colisão". |
| Sobreposição | Overlapping coverage without conflict. |
| Interferência | Sum of w·s over the conflicting edges (spatial × spectral overlap). |
| Estratégia | Method that proposes the configurations: Backtracking, Guloso (greedy) and Algoritmo genético (genetic algorithm). |
| Análise | Running a strategy on the graph, on the Análise page. |
| Execução | One run of the scalability test ("Execução #4"). |
| Nó | Only for the nodes explored by the search; in the graph, vertices are "APs". |
| Ponto de quebra | Break point: first network size at which a strategy no longer solves the problem within the time limit. |
| Consumo / Potência | Energy in kWh over the period / power in W. |
