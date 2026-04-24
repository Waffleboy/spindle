# Landing Page Integration

## Task
Add a marketing landing page for Spindle (Investor Report Intelligence) to the React frontend, accessible at the root URL, with "Open Spindle" CTAs that navigate to the main app.

## What was done

### New component: `frontend/src/components/landing-page.tsx`
- Full landing page as a React component with self-contained CSS (all classes prefixed `lp-` to avoid collisions with Tailwind/shadcn styles)
- Aesthetic: "Institutional Intelligence Noir" — dark theme, gold accents (#c4a04e), Instrument Serif + Outfit + JetBrains Mono typography
- Sections: hero with scan-line animation, stats bar with counter animation, problem/pitch quote, 5-step pipeline flow, 3 feature deep-dives (schema discovery, entity resolution, contradiction detection) with interactive scroll-triggered visuals, product preview mockup, CTA, footer
- All animations use IntersectionObserver for scroll-triggered reveals
- Responsive down to mobile
- `onEnterApp` prop navigates to the main Spindle app

### Modified: `frontend/src/App.tsx`
- Added hash-based routing via `useHashRoute()` hook
- Root URL (`/`) shows the landing page
- `#app` hash shows the main Spindle application
- "Open Spindle" buttons set `window.location.hash = "#app"`

### Modified: `frontend/index.html`
- Extended Google Fonts link to include Outfit and JetBrains Mono (landing page typography)

### Modified: `agents/architecture.md`
- Added landing page component to frontend structure section

## Design decisions
- Used hash routing instead of adding react-router — zero new dependencies, simple toggle between landing and app
- All landing page CSS is scoped with `lp-` prefix and injected via `<style>` tag to avoid any interference with the existing Tailwind/shadcn design system
- Landing page always renders in dark theme regardless of the app's theme setting — it's a marketing page with its own visual identity
