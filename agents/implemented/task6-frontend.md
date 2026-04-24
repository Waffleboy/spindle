# Task 6: Frontend — Next.js + shadcn/ui Three-Panel Layout

## Summary
Built a React/Next.js frontend with shadcn/ui providing a three-panel layout for the Taxonomy Discovery Engine. The app includes document upload (left panel), taxonomy dashboard (main panel), and chat (right panel).

## Implementation

### Architecture
- **Framework:** Next.js 15 (App Router) with TypeScript
- **UI Library:** shadcn/ui with Radix UI primitives
- **Styling:** Tailwind CSS with dark theme (zinc/slate)
- **State Management:** React hooks (useState/useEffect/useCallback)
- **API Communication:** Fetch-based client targeting `http://localhost:8000/api/`

### File Structure
```
frontend/src/
  app/
    layout.tsx          # Root layout with dark theme, Inter font
    page.tsx            # Main page orchestrating three-panel layout
    globals.css         # Tailwind + CSS variables + custom animations
  components/
    document-panel.tsx   # Left: drag-and-drop upload + document list
    taxonomy-panel.tsx   # Main: data table with colored cell highlights
    chat-panel.tsx       # Right: chat with citations and suggestions
    top-bar.tsx          # Progress bar showing 5 pipeline steps
    contradiction-popover.tsx  # Hover popover for contradiction details
    entity-review-card.tsx     # Inline approve/reject/override UI
    ui/                  # shadcn/ui components (button, card, input, etc.)
  lib/
    api.ts              # API client with all endpoint functions
    types.ts            # TypeScript interfaces matching backend schemas
    utils.ts            # cn() utility for Tailwind class merging
```

### Key Features
1. **Dark theme** with zinc-950 backgrounds, colored accent system
2. **Drag-and-drop** file upload with pulse animation
3. **Pipeline progress bar** with 5 segmented steps (polling every 2s)
4. **Taxonomy table** with document rows x dimension columns
5. **Color-coded cells**: rose for contradictions, amber for review, emerald for resolved
6. **Contradiction popover** showing both values and temporal info
7. **Entity review cards** with approve/reject/override actions
8. **Chat panel** with citation badges, typing indicator, starter queries

## Setup
```bash
cd frontend
npm install
npm run build
npm run dev
```
