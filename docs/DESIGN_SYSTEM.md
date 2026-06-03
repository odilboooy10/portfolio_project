# ERP Design System

Single reference for all visual decisions. All values live in
`core/static/css/theme.css` as CSS custom properties. Change them
there — everything in the app inherits them automatically.

---

## Palette

| Token | Hex | Use |
|---|---|---|
| `--color-primary` | `#4f46e5` | Buttons, links, active nav, focus rings |
| `--color-primary-hover` | `#4338ca` | Hover state on primary elements |
| `--color-primary-light` | `#e0e7ff` | Badge backgrounds, row highlights |
| `--color-sidebar-bg` | `#1e293b` | Sidebar background |
| `--color-page-bg` | `#f1f5f9` | Main content area background |
| `--color-card-bg` | `#ffffff` | Cards, tables, modals |
| `--color-border` | `#e2e8f0` | All borders and dividers |
| `--color-text-primary` | `#0f172a` | Headings, field labels |
| `--color-text-secondary` | `#475569` | Body text, table rows |
| `--color-text-muted` | `#94a3b8` | Timestamps, placeholders, column headers |

### Status colors

| State | Color | Background |
|---|---|---|
| Draft | `#94a3b8` | `#f1f5f9` |
| Confirmed | `#4f46e5` | `#e0e7ff` |
| In Progress | `#d97706` | `#fef3c7` |
| Done / Paid | `#16a34a` | `#dcfce7` |
| Cancelled / Overdue | `#dc2626` | `#fee2e2` |

---

## Typography

- **Font:** Inter (system-ui fallback)
- **Mono:** JetBrains Mono (reference numbers, IDs)
- Body text: `14px / 400`
- Table headers: `12px / 600 / uppercase / 0.05em tracking`
- Page titles: `20px / 600`
- KPI numbers: `30px / 700`

---

## Layout

| Variable | Value | Use |
|---|---|---|
| `--sidebar-width` | `240px` | Sidebar fixed width |
| `--topbar-height` | `56px` | Top navigation bar |
| `--card-padding` | `24px` | Padding inside cards |

Content area starts at `margin-left: 240px`. On mobile (<768px)
sidebar collapses to an off-canvas drawer.

---

## Spacing (8px grid)

`4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 / 64px`

Always use the `--space-*` tokens, not hardcoded px values.

---

## Component Patterns

### Page header
Every list and detail page opens with a `.page-header` bar:
- Left: breadcrumb + page title
- Right: primary action button (e.g. "New Order")

### Status bar
Record detail pages show a `.status-bar` strip below the page header
displaying each pipeline stage. Active stage is highlighted in primary
color. Completed stages show a checkmark.

### List view structure
```
page-header
filter-bar  (search input + filter dropdowns + group-by)
erp-table   (th: muted/uppercase labels, td: normal weight rows)
pagination
```

### Form layout
- Two-column grid for fields on medium+ screens
- Full-width on mobile
- Save / Discard buttons sticky at bottom of form
- Inline validation errors below each field in `--color-danger`

### Status badges
Use `.badge-status` + modifier class (`.badge-draft`, `.badge-paid`,
etc.) — pill shape with a leading dot in the status color.

---

## How to change the theme

1. Open `core/static/css/theme.css`
2. Edit the CSS variable value under the relevant section
3. Run `python manage.py collectstatic` (or the dev server picks it up
   automatically via `STATICFILES_DIRS`)
4. No other files need to change

### To switch the primary color (e.g. from indigo to teal)
```css
--color-primary:       #0d9488;  /* teal-600 */
--color-primary-hover: #0f766e;  /* teal-700 */
--color-primary-light: #ccfbf1;  /* teal-100 */
--bs-primary-rgb:      13, 148, 136;
```

### To switch the sidebar to light
```css
--color-sidebar-bg:    #ffffff;
--color-sidebar-text:  #475569;
--color-sidebar-active:#0f172a;
--color-sidebar-hover: #f1f5f9;
--color-sidebar-border:#e2e8f0;
```
