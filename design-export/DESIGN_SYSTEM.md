# FallGuard Design System

A privacy-first, dark-mode-only design system optimized for fall-detection caregiver dashboards. Built with Tailwind CSS 4 and emphasizing clarity, accessibility, and a tech-forward aesthetic.

## Design Tokens

### Color Palette

**Primary Colors (Dark Mode Only)**
- `ink-950`: `#010613` — Darkest background (page/body)
- `ink-900`: `#020612` — Card/elevated backgrounds
- `ink-800`: `#040c1d` — Borders, hover states
- `ink-700`: `#050c1e` — Subtle borders, disabled states

**Accent Colors**
- `cyan-500`: `#06B6D4` — Primary action color (buttons, focus states, success indicators)
- `cyan-600`: `#0891b2` — Hover/active state for cyan buttons
- `teal-500`: `#14B8A6` — Secondary accent (reserved for future use)

**Text Colors**
- White (`#FFFFFF`) — Primary text
- `gray-300` (`#d1d5db`) — Secondary text, medium emphasis
- `gray-400` (`#9ca3af`) — Tertiary text, low emphasis

### Typography

**Font Families** (loaded via Next.js Google Fonts)
- **Sans-serif**: `Inter` — Used for all body text, UI labels, headings
  - Default weight: 400 (regular)
  - Medium: 500 (buttons, labels)
  - Bold: 700 (page titles, emphasis)
- **Monospace**: `JetBrains Mono` — Used for technical content (timestamps, IDs, metrics)
  - Configured with `letter-spacing: 0.05em` for the `.tech-mono` class

**Typography Scale**
- `text-xs`: 12px (labels, badges, timestamps)
- `text-sm`: 14px (secondary text, descriptions)
- (default): 16px (body text)
- `text-2xl`: 24px (page titles, large stats)

**Font Weights**
- 400: regular text
- 500: medium emphasis (buttons, labels)
- 700: bold (headings, large stats)

### Spacing

Uses Tailwind's default spacing scale (4px base unit):
- `px-2` / `py-1`: 8px / 4px — Compact components (badges)
- `px-3` / `py-2`: 12px / 8px — Nav items, pill padding
- `px-4` / `py-2`: 16px / 8px — Button padding, input padding
- `px-6`: 24px — Page/section horizontal padding
- `gap-1`: 4px — Minimal spacing between items
- `gap-2`: 8px — Typical spacing between elements
- `gap-4`: 16px — Larger spacing between sections
- `mb-6`: 24px — Vertical spacing between sections

### Border Radius

- `rounded-full`: 9999px — Pills, badges, circular avatars
- `rounded-xl`: 12px — Buttons, inputs, nav items, small cards
- `rounded-2xl`: 16px — Main cards, large containers
- Default border: 1px solid `ink-800`

### Shadows & Depth

No explicit shadow definitions; depth achieved through:
- Background color hierarchy (ink-950 < ink-900 < ink-800)
- 1px borders with `ink-800`
- **Glassmorphism effect** (`.glass-panel` class):
  - `background: rgba(2, 6, 18, 0.6)` (semi-transparent ink-900)
  - `backdrop-filter: blur(12px)`
  - `border: 1px solid rgba(255, 255, 255, 0.05)` (subtle white border)

### Breakpoints

Uses Tailwind's default breakpoints:
- `md` (768px): Desktop threshold — Sidebar visible, mobile bar hidden

### Motion & Transitions

- `transition-colors`: Default smooth color transitions (hover states)
- `animate-spin`: Spinner animation (8px, border-t cyan)
- No custom animation definitions; uses Tailwind defaults

## Component Inventory

### Button

**Variants**
- **Primary**: `bg-cyan-500 hover:bg-cyan-600 text-white`
  - Used for main actions (submit, confirm, save)
- **Secondary**: `bg-ink-800 hover:bg-ink-700 text-white border border-ink-700`
  - Used for secondary actions (cancel, logout, optional actions)

**States**
- Base: `px-4 py-2 rounded-xl font-medium transition-colors`
- Hover: Color change only (primary darkens cyan, secondary darkens ink)
- Focus: Uses browser default focus ring (can be customized)
- Disabled: No specific styling implemented; uses HTML `disabled` attribute

**Usage**
```tsx
<Button variant="primary">Save</Button>
<Button variant="secondary">Cancel</Button>
```

### Input

**States**
- Default: `bg-ink-900 border border-ink-800 rounded-xl px-4 py-2 text-white`
- Focus: `focus:outline-none focus:border-cyan-500` (cyan border highlight)
- Placeholder: Inherited from browser styling; can be customized with `placeholder-gray-400`

**Usage**
```tsx
<Input type="text" placeholder="Enter username" />
```

### Select (Dropdown)

**States**
- Default: `bg-ink-900 border border-ink-800 rounded-xl px-4 py-2 text-white`
- Focus: `focus:outline-none focus:border-cyan-500`
- Option styling: Uses browser default (may need CSS customization per browser)

**Usage**
```tsx
<Select>
  <option value="admin">Admin</option>
  <option value="caregiver">Caregiver</option>
</Select>
```

### Card

**Base Card**
- `bg-ink-900 border border-ink-800 rounded-2xl p-4`
- Flexible container for grouped content

**StatCard** (specialized Card)
- Displays title (small, gray-400) + value (large, bold)
- Use for metrics, stats, KPIs

**Usage**
```tsx
<Card>Content</Card>
<StatCard title="Total Alerts" value={42} />
```

### Pill (Badge)

**States**
- Default: `px-2 py-1 text-xs font-medium rounded-full bg-ink-800 border border-ink-700`
- Role badges: Uppercase, wide letter-spacing via `.tech-mono` class

**Variants**
- Standard: ink background, used for tags, role labels, status indicators
- Can be extended with background color classes for severity (e.g., `bg-red-900` for errors)

**Usage**
```tsx
<Pill>caregiver</Pill>
<Pill className="bg-red-900 border-red-700">High Priority</Pill>
```

### Table (DataTable)

**Structure**
- Container: `overflow-x-auto rounded-2xl border border-ink-800`
- Header: `bg-ink-900 text-xs uppercase text-gray-400`
- Header cells: `px-4 py-3`
- Rows: `border-b border-ink-800`
- Row cells: `px-4 py-3`
- Row hover: `hover:bg-ink-900/50` (subtle background highlight)

**Usage**
```tsx
<DataTable 
  columns={["Name", "Status", "Date"]}
  data={[
    [<span>Alert 1</span>, <Pill>Pending</Pill>, "2025-01-15"],
  ]}
/>
```

### Navbar / Sidebar

**Sidebar** (Desktop only, `hidden md:flex`)
- Width: 256px (w-64)
- Background: `bg-ink-950`
- Border: `border-r border-ink-800`
- Height: 100vh (full height)

**Sidebar Header**
- Height: 64px (h-16)
- Logo area: `font-bold text-xl` with `gap-2` flex layout
- Accent: `text-cyan-500 font-mono` for logo mark

**Sidebar Nav**
- Flex column, `gap-1` between items
- Nav items: `px-3 py-2 rounded-xl transition-colors`
- Active: `bg-ink-800 text-white font-medium`
- Inactive: `text-gray-400 hover:text-white hover:bg-ink-900/50`

**Mobile Bar** (Mobile only, `md:hidden`)
- Position: Fixed bottom of screen (`fixed bottom-0`)
- Background: `bg-ink-950`
- Border: `border-t border-ink-800`
- Layout: Horizontal scroll (`flex overflow-x-auto`)
- Nav items: `px-4 py-2 rounded-xl text-sm`
- Similar active/inactive styling as sidebar

### Loading / Skeleton

**Loading Spinner**
- Container: `flex items-center justify-center w-full h-full p-8`
- Spinner: `w-8 h-8 border-4 border-ink-700 border-t-cyan-500 rounded-full animate-spin`
- Color: Dark border with cyan accent on top border

**Empty State**
- Container: `flex flex-col items-center justify-center w-full h-48`
- Border: `border border-dashed border-ink-700`
- Background: `bg-ink-900/20` (semi-transparent)
- Text: `text-gray-400` (muted)

### Page Header

**Structure**
- Container: `mb-6` (margin bottom for spacing)
- Title: `text-2xl font-bold text-white`
- Description (optional): `text-gray-400 text-sm mt-1`

**Usage**
```tsx
<PageHeader 
  title="Alerts"
  description="Monitor and manage fall detection alerts"
/>
```

## Layout Patterns

### Page Shell

```
<html> (dark mode)
  <body> (bg-ink-950, text-white, font-sans)
    <Sidebar /> (md:flex, w-64)
    <TopHeaderBar /> (sticky, h-16)
    <main> (flex-1)
      <PageHeader />
      <div className="p-6">
        {/* Page content */}
      </div>
    </main>
    <MobileBar /> (md:hidden)
  </body>
</html>
```

### Responsive Grid

- Desktop: Use `grid grid-cols-4` / `grid-cols-3` for card layouts
- Mobile: Stack vertically or use `grid-cols-1`
- Breakpoint: 768px (`md:`)

### Spacing Rhythm

- Page padding: 24px (px-6)
- Section gap: 16px (gap-4)
- Component gap: 8px (gap-2)
- Internal padding (cards): 16px (p-4)

### Card Grid Example

```tsx
<div className="grid grid-cols-1 md:grid-cols-4 gap-4">
  <StatCard title="Total" value={42} />
  <StatCard title="Pending" value={12} />
  <StatCard title="Resolved" value={30} />
  <StatCard title="High Risk" value={5} />
</div>
```

## Icon Library

**Library**: Lucide React (`lucide-react`)
- 4000+ icons available
- Usage: `import { IconName } from 'lucide-react'`
- Size: Default 24x24px; can customize with `size={16}` prop
- Color: Inherits text color; customize with `className` or `color` prop

**Common icons**:
- Navigation: `Menu`, `X`, `ChevronRight`, `Home`
- Status: `Check`, `AlertCircle`, `Clock`, `Zap`
- Action: `Settings`, `LogOut`, `Download`, `Upload`

**Usage**
```tsx
import { AlertCircle, Check } from 'lucide-react';

<AlertCircle className="text-cyan-500" size={20} />
<Check className="text-green-500" />
```

## Visual Tone

**FallGuard embodies a tech-forward, clinical aesthetic:**
- **Modern**: Clean lines, generous whitespace (dark space), no ornamentation
- **Trustworthy**: High contrast for readability; clear hierarchies via color and size
- **Professional**: Monospace fonts for technical data; precise icon usage
- **Accessible**: Dark mode by default reduces eye strain; cyan accent provides color-blind-friendly contrast
- **Focused**: Minimal distractions; card-based layouts guide user attention
- **Efficient**: Fast feedback (color transitions); responsive to input without delays

Colors evoke a "medical dashboard" aesthetic: dark backgrounds for data richness, cyan accent suggesting accuracy and care, while maintaining warmth through anti-aliasing and polished typography.

## Dependencies

### Core
- **Next.js 16.3.2** — React framework with SSR, file-based routing
- **React 19.2.8** — UI library
- **React DOM 19.2.8** — DOM rendering

### Styling
- **Tailwind CSS 4** — Utility-first CSS framework
- **@tailwindcss/postcss 4** — Tailwind PostCSS plugin (required for Tailwind CSS 4)
- **PostCSS** — CSS transformer (via tailwindcss plugin)

### State Management
- **Zustand 5.0.15** — Lightweight state management (used for user/auth state in store)

### Data & Async
- **@tanstack/react-query 5.103.2** — Server-state management (fetch, cache, sync)

### UI Elements
- **Lucide React 1.34.0** — SVG icon library (4000+ icons)

### Data Visualization
- **Recharts 3.10.1** — React charting library built on D3
  - Used for: Line charts, bar charts, area charts, pie charts

### Development
- **TypeScript 5** — Type safety
- **ESLint 9** — Linting
- **eslint-config-next** — Next.js ESLint rules

## Setup Instructions for Reuse

1. **Install dependencies**:
   ```bash
   npm install next react react-dom tailwindcss @tailwindcss/postcss postcss zustand @tanstack/react-query lucide-react recharts
   npm install -D typescript @types/react @types/react-dom @types/node eslint eslint-config-next
   ```

2. **Copy configuration files**:
   - `postcss.config.mjs` → project root
   - `globals.css` → `app/` or `src/` directory
   - `next.config.ts` → project root (if using Next.js)

3. **Copy font setup** (from `app/layout.tsx`):
   ```tsx
   import { Inter, JetBrains_Mono } from "next/font/google";
   
   const inter = Inter({ 
     subsets: ["latin"],
     variable: "--font-inter",
     display: 'swap',
   });
   
   const jetbrainsMono = JetBrains_Mono({ 
     subsets: ["latin"],
     variable: "--font-jetbrains-mono",
     display: 'swap',
   });
   
   // Apply to html root: className={`${inter.variable} ${jetbrainsMono.variable} dark`}
   ```

4. **Copy component library**:
   - `components/ui/index.tsx` → `components/ui/`
   - `components/layout/` → `components/layout/`

5. **Add custom fonts CSS** (already in `globals.css`):
   ```css
   @theme {
     --color-ink-950: #010613;
     --color-ink-900: #020612;
     --color-ink-800: #040c1d;
     --color-ink-700: #050c1e;
     --color-cyan-500: #06B6D4;
     --color-teal-500: #14B8A6;
     --font-sans: var(--font-inter), sans-serif;
     --font-mono: var(--font-jetbrains-mono), monospace;
   }
   ```

## Notes for Implementers

- **Dark mode only**: This design system is optimized for dark mode. Light mode support requires significant color adjustments.
- **Tailwind 4**: Uses CSS-based theming via `@theme` blocks; no `tailwind.config.js` needed.
- **No component framework**: Components are vanilla React with Tailwind classes; not built on shadcn/ui or similar.
- **Responsive gaps**: Use Tailwind's breakpoints (`md:`, `lg:`) to adjust layout on smaller screens.
- **Chart styling**: Recharts respects Tailwind colors by default; customize via component props.
- **Icon sizing**: Lucide defaults to 24x24; adjust with `size` prop for smaller/larger icons.
- **Accessibility**: Text contrast meets WCAG AA standards (white on ink-900 = 8.5:1); cyan on dark = 5.5:1 for accents.
