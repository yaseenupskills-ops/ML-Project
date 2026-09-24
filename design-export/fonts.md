# Font Configuration

The FallGuard design system uses two Google Fonts via Next.js font optimization.

## Fonts

### Inter (Sans-serif)

**Usage**: Body text, headings, UI labels, buttons
**Source**: Google Fonts
**Weights Used**: 400 (regular), 500 (medium), 700 (bold)
**CSS Variable**: `--font-inter`

**Next.js Setup**:
```tsx
import { Inter } from "next/font/google";

const inter = Inter({ 
  subsets: ["latin"],
  variable: "--font-inter",
  display: 'swap',
});
```

**HTML Application**:
```tsx
<html className={`${inter.variable} dark`}>
  <body className="font-sans">
    {/* Content */}
  </body>
</html>
```

**CSS Reference**:
```css
@theme {
  --font-sans: var(--font-inter), sans-serif;
}
```

---

### JetBrains Mono (Monospace)

**Usage**: Technical content (timestamps, IDs, metrics, code), role labels with tech aesthetic
**Source**: Google Fonts
**Weights Used**: 400 (regular), 500 (medium), 700 (bold)
**CSS Variable**: `--font-jetbrains-mono`

**Next.js Setup**:
```tsx
import { JetBrains_Mono } from "next/font/google";

const jetbrainsMono = JetBrains_Mono({ 
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: 'swap',
});
```

**HTML Application**:
```tsx
<html className={`${jetbrainsMono.variable} dark`}>
  <body>
    {/* Content */}
  </body>
</html>
```

**CSS Reference**:
```css
@theme {
  --font-mono: var(--font-jetbrains-mono), monospace;
}
```

---

## Usage in Components

### Applying Sans-serif (Default)

```tsx
<div className="font-sans">Regular body text</div>
<h1 className="font-sans font-bold text-2xl">Heading</h1>
<button className="font-medium">Button Label</button>
```

### Applying Monospace

```tsx
<span className="font-mono">user_id_12345</span>
<time className="font-mono text-sm">2025-01-15 14:30:42</time>
<span className="font-mono">192.168.1.1</span>
```

### Combining with Tech Aesthetic

Use the `.tech-mono` utility class for extra letter-spacing on monospace text:

```tsx
<span className="tech-mono text-xs">{userRole.toUpperCase()}</span>
// Renders with 0.05em letter-spacing
```

---

## Performance Considerations

- **Font Display Strategy**: `display: 'swap'` — Shows fallback fonts immediately while Google Fonts load
- **Fallbacks**: 
  - Sans-serif fallback: `sans-serif` (system font)
  - Monospace fallback: `monospace` (system font)
- **Subsets**: `latin` only — Reduces font file size for English-only content
- **Optimization**: Next.js automatically self-hosts fonts and optimizes delivery

---

## Customization

To use different Google Fonts:

1. **Update `app/layout.tsx`**:
   ```tsx
   import { YourFont, AnotherFont } from "next/font/google";
   
   const yourFont = YourFont({ 
     subsets: ["latin"],
     variable: "--font-your-name",
     display: 'swap',
   });
   ```

2. **Update `globals.css`**:
   ```css
   @theme {
     --font-sans: var(--font-your-name), sans-serif;
   }
   ```

3. **Update Tailwind Classes**:
   - Apply new font variable to `html` className
   - Existing `font-sans` and `font-mono` classes automatically use new fonts

---

## Font Sizes in Tailwind

The design system uses Tailwind's default font sizes:

| Class | Size | Usage |
|-------|------|-------|
| `text-xs` | 12px | Labels, badges, timestamps |
| `text-sm` | 14px | Secondary text, descriptions |
| (default) | 16px | Body text |
| `text-2xl` | 24px | Page titles, large stats |

---

## Font Weights

Tailwind's default weights are applied via classes:

| Class | Weight |
|-------|--------|
| `font-normal` | 400 |
| `font-medium` | 500 |
| `font-bold` | 700 |

---

## Anti-aliasing

Both fonts include smoothing directives in `globals.css`:

```css
-webkit-font-smoothing: antialiased;
-moz-osx-font-smoothing: grayscale;
```

This ensures crisp rendering on macOS and webkit browsers.
