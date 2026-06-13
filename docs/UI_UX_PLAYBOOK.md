# ClientFinder UI/UX Playbook

> The canonical design system + principles for ClientFinder UI.
> Apply these to every page, every component, every interaction.
> Inspired by **Linear + Stripe** — minimal sophistication with warm professionalism.

---

## 0. Design Philosophy

**Audience**: Freelance software developers in Indonesia using this for outreach to UMKM.
**Tone**: Professional but **approachable**. Sophisticated but not cold. Modern but not gimmicky.
**Reference**: A developer should look at this and think *"I want to use this every day"*, not *"oh, another SaaS dashboard"*.

### Core tenets

1. **Hierarchy first** — every screen has one clear primary action. Don't make users think.
2. **Whitespace is content** — generous padding breathes life into dense data.
3. **Depth, not flatness** — multi-layer shadows, subtle borders, never bare HTML.
4. **Motion with purpose** — 150-200ms transitions on state changes. Never gratuitous.
5. **Taste over features** — when in doubt, remove something.

---

## 1. Color System

### Brand

| Role | Light | Dark | Usage |
|---|---|---|---|
| `--primary` | `262 83% 58%` (Violet 600) | `263 85% 70%` | CTAs, links, brand accents |
| `--primary-foreground` | `0 0% 100%` | `222 47% 11%` | Text on primary bg |

Use `bg-gradient-to-r from-violet-600 to-indigo-600` for hero CTAs and brand elements.

### Neutrals (warm slate, not blue-gray)

| Role | Light | Dark |
|---|---|---|
| `--background` | `0 0% 100%` (off-white) | `222 47% 7%` |
| `--foreground` | `222 47% 11%` | `210 20% 98%` |
| `--card` | `0 0% 100%` | `222 47% 9%` |
| `--card-foreground` | `222 47% 11%` | `210 20% 98%` |
| `--muted` | `210 40% 96%` | `217 33% 14%` |
| `--muted-foreground` | `215 16% 47%` | `215 20% 65%` |
| `--border` | `220 13% 91%` | `217 33% 18%` |
| `--ring` | `262 83% 58%` | `263 85% 70%` |

### Semantic

| Role | Color | Hex | Usage |
|---|---|---|---|
| Success | Emerald 600 | `#059669` | Won, confirmed, positive deltas |
| Warning | Amber 500 | `#f59e0b` | Pending, attention needed |
| Danger | Rose 500 | `#f43f5e` | Lost, errors, destructive |
| Info | Sky 500 | `#0ea5e9` | Informational badges |

### Pipeline status (Prospects)

| Status | Color | Hex | Tone |
|---|---|---|---|
| `new` | Slate 500 | `#64748b` | neutral, untouched |
| `enriching` | Blue 500 | `#3b82f6` | in progress |
| `scored` | Violet 500 | `#8b5cf6` | evaluated |
| `approved` | Indigo 500 | `#6366f1` | ready to contact |
| `contacted` | Amber 500 | `#f59e0b` | outreach sent |
| `replied` | Orange 500 | `#f97316` | hot, needs response |
| `won` | Emerald 600 | `#059669` | success! |
| `lost` | Rose 500 | `#f43f5e` | closed-lost |
| `archived` | Zinc 500 | `#71717a` | dormant |

### Lead grade

| Grade | Color | Score range |
|---|---|---|
| A | Emerald 600 | 80-100 |
| B | Sky 500 | 60-79 |
| C | Amber 500 | 40-59 |
| D | Rose 500 | 0-39 |

---

## 2. Typography

- **Font**: `Inter` (loaded via Google Fonts in production; system fallback now)
- **Weights**: 400, 500, 600, 700
- **Line height**: 1.25 (tight, headings), 1.5 (normal, body)
- **Letter spacing**: `-0.025em` (tight, headings ≥ 24px), 0 (body)

### Hierarchy

| Element | Class |
|---|---|
| Page title | `text-3xl font-semibold tracking-tight` |
| Section title | `text-xl font-semibold` |
| Card title | `text-base font-semibold` |
| Body | `text-sm text-foreground` |
| Helper | `text-xs text-muted-foreground` |
| Numeric stat | `text-3xl font-bold tracking-tight tabular-nums` |

`tabular-nums` for ALL numbers (prices, scores, counts) — keeps columns aligned.

---

## 3. Spacing & Layout

- **4px base grid**: 0, 1, 2, 3, 4, 6, 8, 12, 16, 20, 24, 32, 48, 64
- **Generous padding**: `p-6` (24px) for cards, `gap-6` (24px) for grid sections
- **Container widths**:
  - Main: `max-w-7xl mx-auto`
  - Forms: `max-w-md` (login) or `max-w-2xl` (settings)
  - Modals: `max-w-lg` to `max-w-2xl`
- **Sidebar**: `w-60` (240px) on desktop, drawer on mobile

---

## 4. Shadows & Depth

Multi-layer shadows for soft, realistic depth. **Never** single-layer.

```css
--shadow-sm:    0 1px 2px 0 rgb(0 0 0 / 0.05);
--shadow-DEFAULT: 0 1px 3px 0 rgb(0 0 0 / 0.08), 0 1px 2px -1px rgb(0 0 0 / 0.06);
--shadow-md:    0 4px 6px -1px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.05);
--shadow-lg:    0 10px 15px -3px rgb(0 0 0 / 0.10), 0 4px 6px -4px rgb(0 0 0 / 0.05);
--shadow-glow:  0 0 20px hsl(262 83% 58% / 0.4);
```

Use:
- Cards: `shadow-sm`
- Popovers, dropdowns: `shadow-md`
- Modals, dialogs: `shadow-lg` or `shadow-xl`
- Hero CTAs (hover): `shadow-glow`

---

## 5. Borders & Radius

- **Borders**: 1px with `border-border` (subtle slate-200/700)
- **Radius scale**:
  - `rounded-sm` (4px) — badges
  - `rounded-md` (6px) — buttons, inputs
  - `rounded-lg` (8px) — cards
  - `rounded-xl` (12px) — modals
  - `rounded-2xl` (16px) — hero sections
  - `rounded-full` — pills, avatars
- **No sharp 90° corners** except table cells, code blocks

---

## 6. Motion & Transitions

| Speed | Duration | Easing | Use for |
|---|---|---|---|
| Fast | 150ms | `cubic-bezier(0.16, 1, 0.3, 1)` | Hover, focus, color changes |
| Default | 200ms | same | Background, border, transform |
| Slow | 300ms | same | Layout, sidebar, drawer |

**Never** use `linear` easing. **Never** use durations > 500ms for UI.

**Custom transition utility**:
```css
.transition-base { transition: all 200ms cubic-bezier(0.16, 1, 0.3, 1); }
```

---

## 7. Component Patterns

### 7.1 Button

```tsx
// Variants (shadcn cva):
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium " +
  "transition-all duration-150 ease-out-expo " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 " +
  "disabled:pointer-events-none disabled:opacity-50 " +
  "active:scale-[0.98]",
  {
    variants: {
      variant: {
        default: "bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-sm hover:shadow-glow",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        destructive: "bg-gradient-to-r from-rose-600 to-red-600 text-white shadow-sm",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        sm: "h-8 px-3 text-xs",
        md: "h-10 px-4",
        lg: "h-12 px-6 text-base",
        icon: "h-10 w-10",
      },
    },
  }
);
```

Note the `active:scale-[0.98]` — tiny press feedback. And the gradient on default.

### 7.2 Card

```tsx
<Card className="border border-border shadow-sm hover:shadow-md transition-all duration-200">
  <CardHeader>
    <CardTitle className="text-base font-semibold">Prospect Summary</CardTitle>
    <CardDescription>Quick overview of your pipeline</CardDescription>
  </CardHeader>
  <CardContent>...</CardContent>
</Card>
```

### 7.3 Stat Card (custom)

```tsx
<Card className="relative overflow-hidden border border-border shadow-sm">
  {/* Gradient left border */}
  <div className="absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-violet-500 to-indigo-500" />

  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
    <CardDescription className="font-medium">{title}</CardDescription>
    <div className="h-8 w-8 rounded-md bg-muted flex items-center justify-center text-muted-foreground">
      {icon}
    </div>
  </CardHeader>
  <CardContent>
    <div className="text-3xl font-bold tracking-tight tabular-nums">{value}</div>
    <div className="flex items-center gap-1 text-xs mt-1">
      <span className="text-emerald-600 font-medium">▲ +12%</span>
      <span className="text-muted-foreground">vs last week</span>
    </div>
  </CardContent>
</Card>
```

### 7.4 Status Pill

```tsx
const statusColors = {
  new: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  enriching: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  scored: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400",
  contacted: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  replied: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  won: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  lost: "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400",
  archived: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
};

<span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", statusColors[status])}>
  {label}
</span>
```

### 7.5 Input

```tsx
<div className="space-y-2">
  <label htmlFor="email" className="text-sm font-medium leading-none">
    Email
  </label>
  <Input
    id="email"
    type="email"
    className="h-10"  // explicit height for consistency
  />
  <p className="text-xs text-muted-foreground">Helper text below</p>
</div>
```

### 7.6 Empty State

```tsx
<div className="flex flex-col items-center justify-center py-16 text-center">
  <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-4">
    <Icon className="h-6 w-6 text-muted-foreground" />
  </div>
  <h3 className="text-base font-semibold">No prospects yet</h3>
  <p className="text-sm text-muted-foreground mt-1 max-w-sm">
    Run a scout job to discover businesses that need software services.
  </p>
  <Button className="mt-6">Run first scout</Button>
</div>
```

---

## 8. Page Layouts

### 8.1 Login

**Split-screen layout**:
- Left (40%): gradient background, logo + value prop, decorative orbs
- Right (60%): centered form card

```tsx
<div className="min-h-screen grid lg:grid-cols-5">
  {/* Left — branding panel */}
  <div className="hidden lg:flex lg:col-span-2 relative bg-gradient-to-br from-violet-600 to-indigo-700 p-12 flex-col justify-between text-white">
    <div className="relative z-10">
      <Logo className="h-8" />
      <h1 className="text-4xl font-bold mt-12 leading-tight">
        Find your next client in minutes, not weeks.
      </h1>
      <p className="text-violet-100 mt-4 text-lg max-w-md">
        AI-powered lead generation for Indonesian freelance developers.
      </p>
    </div>
    <p className="text-violet-200 text-sm">© 2026 ClientFinder</p>

    {/* Decorative gradient orbs */}
    <div className="absolute top-0 right-0 h-96 w-96 bg-violet-400/30 rounded-full blur-3xl" />
    <div className="absolute bottom-0 left-0 h-72 w-72 bg-indigo-400/30 rounded-full blur-3xl" />
  </div>

  {/* Right — form */}
  <div className="lg:col-span-3 flex items-center justify-center p-6 bg-background">
    <Card className="w-full max-w-md border-0 shadow-none">
      <CardHeader>
        <CardTitle className="text-2xl">Sign in</CardTitle>
        <CardDescription>Welcome back</CardDescription>
      </CardHeader>
      {/* form */}
    </Card>
  </div>
</div>
```

### 8.2 Dashboard

```tsx
<div className="space-y-8">
  {/* Hero header */}
  <header className="flex items-end justify-between">
    <div>
      <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
      <p className="text-muted-foreground mt-1">
        Your lead generation at a glance
      </p>
    </div>
    <Button>New search</Button>
  </header>

  {/* Stat grid */}
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
    {stats.map(...)}
  </div>

  {/* Main content — 2 column */}
  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <Card className="lg:col-span-2">Chart</Card>
    <Card>Recent activity</Card>
  </div>
</div>
```

### 8.3 List Page (Prospects)

```tsx
<div className="space-y-6">
  <header className="flex items-end justify-between">
    <div>
      <h1 className="text-3xl font-bold tracking-tight">Prospects</h1>
      <p className="text-muted-foreground mt-1">{total} total · {filteredCount} filtered</p>
    </div>
    <div className="flex gap-2">
      <Input placeholder="Search..." className="w-64" />
      <Button>New search</Button>
    </div>
  </header>

  {/* Table or cards */}
  <Card>
    <Table>...</Table>
  </Card>
</div>
```

---

## 9. Loading & Error States

### Skeleton (use as default)

```tsx
<Skeleton className="h-4 w-3/4" />
<Skeleton className="h-4 w-1/2" />
<Skeleton className="h-32 w-full" />
```

### Error

```tsx
<Card className="border-rose-200 bg-rose-50/30">
  <CardContent className="py-6 text-center">
    <p className="text-sm text-rose-700">Could not load prospects.</p>
    <Button variant="outline" size="sm" className="mt-3" onClick={refetch}>
      Try again
    </Button>
  </CardContent>
</Card>
```

### Empty

(Already in 7.6)

---

## 10. Accessibility

- **Color contrast**: WCAG AA (4.5:1 for body text)
- **Focus visible**: Always 2px ring with offset
- **Keyboard nav**: Tab order = visual order, Escape closes modals
- **Screen reader**: `aria-label` on icon-only buttons, `aria-describedby` on form fields
- **Skip link**: First focusable element on every page
- **Reduced motion**: Wrap animations in `@media (prefers-reduced-motion: no-preference)`

---

## 11. Anti-Patterns — DON'T

- ❌ Pure `#fff` backgrounds (use subtle gradient or off-white)
- ❌ Centered everything (asymmetric layouts feel intentional)
- ❌ All text same weight (vary 400/500/600/700)
- ❌ Single-layer shadows
- ❌ Tailwind defaults without thought
- ❌ Stock shadcn without customization
- ❌ Generic illustrations / clip art
- ❌ "Web 2.0" diagonal rainbow gradients
- ❌ More than 2 accent colors on one screen
- ❌ Linear easing
- ❌ Animations > 500ms
- ❌ Placeholder Lorem Ipsum (use real-feeling data)
- ❌ Emoji as icon replacement (use lucide-react)
- ❌ "Click here" link text

---

## 12. Reference Inspiration

- **Linear** — minimalism, dark sidebar, bold type, sparse UI
- **Stripe** — generous whitespace, soft shadows, gradient orbs
- **Vercel** — ultra minimal, mono+sans mix
- **Raycast** — dark with colorful accents, playful
- **Notion** — warm, friendly, document-like
- **Cal.com** — modern, gradient, professional (closest match)
- **Linear changelog** — best in class typography hierarchy

---

## 13. Code Conventions

- Use `cn()` for class composition
- Prefer Tailwind utilities over inline styles
- Extract repeated patterns to components
- Use `forwardRef` for inputs/buttons
- Use `asChild` prop for linkable buttons (`<Button asChild><Link/></Button>`)
- TypeScript strict mode
- Named exports for components, default exports for pages

---

## 14. Implementation Phases

This playbook is applied in 7 groups (T9.5.x):

1. **T9.5.1** — Playbook + design tokens (this doc + tailwind.config.js + index.css)
2. **T9.5.2** — Custom shadcn variants (Button gradient, Card hover, Badge variants, StatusPill)
3. **T9.5.3** — Redesign Login + Register (split-screen, gradient hero)
4. **T9.5.4** — Redesign Sidebar + Topbar (dark sidebar, glass topbar)
5. **T9.5.5** — Redesign Dashboard (hero + 4 stat cards + chart + activity)
6. **T9.5.6** — Redesign Prospects + Pipeline + Settings
7. **T9.5.7** — Polish: dark mode, micro-interactions, accessibility

Each group = 1 commit + 1 push + 1 auto-PR-merge to develop.

---

## 15. Future Considerations

- **Theme toggle** (already supported via HSL vars)
- **Empty state illustrations** — consider custom SVG set
- **Motion library** — Framer Motion for complex animations (if needed)
- **Icon system** — lucide-react (current), consider custom icon set if needed
- **A/B testing** — once we have data, test design choices
- **Storybook** — for component documentation (T8 maybe)

---

*This playbook is a living document. Update it as the design evolves.*
