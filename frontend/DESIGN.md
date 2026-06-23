# IncidentOps AI Design System

## 1. Atmosphere & Identity

IncidentOps AI should feel like a quiet incident command center: dense, precise, and highly legible. The signature is layered operational depth, where the user can read the state of an investigation at a glance without fighting decorative clutter. Every panel should feel like it belongs to the same system, with the lifecycle of an incident visible from trigger to merge request.

## 2. Color

### Palette

| Role | Token | Value | Usage |
|------|-------|-------|-------|
| Surface / base | `--surface-base` | `#070B14` | App background |
| Surface / panel | `--surface-panel` | `#0C1220` | Primary cards |
| Surface / raised | `--surface-raised` | `#111A2C` | Selected cards, overlays |
| Surface / subtle | `--surface-subtle` | `#0A101B` | Secondary regions |
| Text / primary | `--text-primary` | `#F4F7FB` | Headlines, body text |
| Text / secondary | `--text-secondary` | `#A9B4C4` | Supporting copy |
| Text / tertiary | `--text-tertiary` | `#748196` | Labels, hints |
| Border / default | `--border-default` | `rgba(148, 163, 184, 0.18)` | Card outlines |
| Border / subtle | `--border-subtle` | `rgba(148, 163, 184, 0.10)` | Dividers |
| Accent / primary | `--accent-primary` | `#5DD6FF` | Selected states, links, focus |
| Accent / primary-soft | `--accent-primary-soft` | `rgba(93, 214, 255, 0.14)` | Banners, chip fills |
| Accent / success | `--status-success` | `#4ADE80` | Validation pass |
| Accent / warning | `--status-warning` | `#FBBF24` | Warnings, checkpoints |
| Accent / error | `--status-error` | `#FB7185` | Failures, regressions |
| Accent / info | `--status-info` | `#7DD3FC` | Evidence, metadata |
| Code / background | `--code-bg` | `#050A12` | Diff and log panes |

### Rules

- Use tonal depth rather than shadows.
- Only use accent colors for state, focus, and key metrics.
- Do not introduce arbitrary colors outside this palette.

## 3. Typography

### Scale

| Level | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| Display | 56px | 700 | 1.05 | Dashboard title |
| H1 | 36px | 700 | 1.15 | Section titles |
| H2 | 28px | 650 | 1.2 | Panel headers |
| H3 | 22px | 600 | 1.3 | Card titles |
| Body | 16px | 400 | 1.6 | Standard content |
| Body / small | 14px | 400 | 1.5 | Metadata, helper text |
| Caption | 12px | 500 | 1.4 | Labels, timestamps |
| Mono | 13px | 500 | 1.5 | Diff, logs, hashes |

### Font Stack

- Primary: `Geist Sans, system-ui, sans-serif`
- Mono: `Geist Mono, ui-monospace, monospace`

### Rules

- Use at most two font families.
- Never drop body text below 14px.
- Numeric UI values should use mono or tabular figures.

## 4. Spacing & Layout

### Base Unit

All spacing is derived from a 4px grid.

| Token | Value | Usage |
|-------|-------|-------|
| `--space-1` | 4px | Tight gaps |
| `--space-2` | 8px | Chip padding, inline metadata |
| `--space-3` | 12px | Compact blocks |
| `--space-4` | 16px | Default inner spacing |
| `--space-5` | 20px | Comfortable gaps |
| `--space-6` | 24px | Card padding |
| `--space-8` | 32px | Section spacing |
| `--space-10` | 40px | Larger content gaps |
| `--space-12` | 48px | Page section spacing |
| `--space-16` | 64px | Major vertical rhythm |

### Grid

- Max content width: `1440px`
- Main layout: `280px` rail + fluid workspace
- Desktop breakpoint: `1280px`
- Tablet breakpoint: `1024px`
- Mobile breakpoint: `768px`

### Rules

- No magic spacing values outside the grid.
- Primary content should be readable in 5 minutes of demo navigation.

## 5. Components

### Incident Rail
- **Structure**: incident list, status chips, timestamps, repo metadata
- **Variants**: active, resolved, failed, waiting
- **Spacing**: `--space-4` to `--space-6`
- **States**: default, hover, selected, focus
- **Accessibility**: keyboard focus, clear selected state, sufficient contrast

### Lifecycle Timeline
- **Structure**: ordered phase stack with connectors and per-step metadata
- **Variants**: pending, running, complete, blocked
- **Spacing**: `--space-4`, `--space-6`
- **States**: current, completed, attention, error
- **Accessibility**: semantic ordered list, readable status text

### Evidence Panel
- **Structure**: source tabs, log excerpt, commit summary, pipeline summary
- **Variants**: logs, GitLab, CI/CD
- **Spacing**: `--space-4`, `--space-6`
- **States**: empty, populated, loading

### Diff Viewer
- **Structure**: header metadata, file path, unified diff lines
- **Variants**: added, removed, context
- **Spacing**: `--space-3`, `--space-4`
- **States**: default, overflow, copyable snippet

### Status Pill
- **Structure**: compact label with semantic color
- **Variants**: success, warning, error, info, neutral
- **Spacing**: `--space-2`, `--space-3`
- **States**: static, hover on interactive pills

## 6. Motion & Interaction

### Timing

| Type | Duration | Easing | Usage |
|------|----------|--------|-------|
| Micro | 120ms | ease-out | Buttons, chips |
| Standard | 220ms | ease-in-out | Panel switching |
| Entry | 360ms | cubic-bezier(0.16, 1, 0.3, 1) | Page load, section reveal |

### Rules

- Only animate `transform` and `opacity`.
- Keep motion subtle.
- No complex choreography or attention-grabbing animation.

## 7. Depth & Surface

### Strategy: tonal-shift

Use progressively lighter surfaces to define hierarchy. Avoid shadows and decorative gradients. Separation comes from border color, contrast, and a small number of raised surfaces for active content.

| Token | Value | Usage |
|-------|-------|-------|
| Base | `--surface-base` | App background |
| Panel | `--surface-panel` | Primary cards |
| Raised | `--surface-raised` | Active or selected states |
| Subtle | `--surface-subtle` | Secondary blocks |

