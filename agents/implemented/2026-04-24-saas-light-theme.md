# SaaS Light Theme + Theme Switcher

**Date:** 2026-04-24

## Task
Add a SaaS-style light theme alongside the existing dark theme, with a persistent toggle in the header.

## What was done
- Created `ThemeProvider` context (`src/lib/theme.tsx`) with localStorage persistence using key `spindle-theme`
- Converted CSS variables to dual-theme: `:root` holds light values (soft blue accent `#5B8DEF`, cool-gray backgrounds `#F5F7FA`), `.dark` holds original dark values
- Updated `index.html` with FOWT-prevention script (applies `dark` class before React hydrates)
- Extended `tailwind.config.js` with semantic color utilities (`bg-background`, `text-foreground`, `bg-primary`, etc.)
- Updated all UI primitives (button, badge, card, input, popover, scroll-area, tooltip) to use semantic classes
- Updated all feature panels (document, taxonomy, chat, top-bar, templates, entity-review, contradiction, notifications) to use semantic theme-aware classes
- Added ThemeToggle button (moon/sun icon) in the app header
- Zero remaining hardcoded `zinc-` or `indigo-` color references

## Fix: Light theme colors aligned with mockup (2026-04-24)
The original implementation used generic gray HSL values that didn't match `frontend/mockup-saas-theme.html`. Key corrections in `src/index.css`:
- **Background** `#F5F7FA` → `216 33% 97%` (was `216 20% 97%` — too little blue saturation)
- **Foreground** `#111827` → `221 39% 11%` (was `220 13% 10%` — needed blue-ink tint)
- **Secondary/muted** bumped to `218 29% 95%` to carry the cool-blue tint from the mockup
- **Accent bg** → `218 36% 96%` (subtle blue wash like `--blue-50: #F0F5FF`)
- **Success** `#059669` → `161 94% 30%` (was over-bright at 39% lightness)
- **Warning** `#D97706` → `32 95% 44%` (was over-bright at 50% lightness)

## Architecture impact
- `ThemeProvider` wraps the entire app (above `NotificationProvider`)
- Theme state: `"light" | "dark"`, defaults to `"dark"`, persisted in `localStorage["spindle-theme"]`
- Tailwind `darkMode: "class"` strategy — `.dark` class on `<html>` element
- All colors flow through CSS custom properties defined in `src/index.css`
