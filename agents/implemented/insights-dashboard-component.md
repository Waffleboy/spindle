# Insights Dashboard Component

**Date:** 2026-04-24
**Task:** Build the `insights-dashboard.tsx` React component for the Investor Report Intelligence dashboard.

## What was done

Created `/frontend/src/components/insights-dashboard.tsx` -- the core insights dashboard component that shows contradictions, entities needing review, and staleness indicators after document processing.

### Component structure

- **`InsightsDashboard`** -- main exported component. Fetches data from `GET /api/insights` on mount using `useState` + `useEffect` with proper cleanup (cancellation flag). Handles loading, error, and empty states.

- **`SummaryBanner`** -- horizontal row of three count cards: Contradictions (rose), Entities to Review (amber), Temporal Updates (blue). Cards highlight with colored backgrounds when counts > 0.

- **`ContradictionCard`** -- displays two doc values side by side with filenames, formatted dates, "More recent" badge on the newer doc side, and resolution status badge.

- **`EntityReviewItem`** -- clickable list item showing canonical name, entity type badge, review count, and aliases. Calls `onSelectEntity` prop on click for navigating to the change feed view.

- **`StalenessCard`** -- shows old value (struck through) with arrow to new value, old and new doc filenames/dates, and an "Updated"/"Superseded" label.

### Key details

- Uses existing UI components: `Badge`, `Card`, `CardContent`, `CardHeader`, `CardTitle`, `ScrollArea`
- Uses existing badge variants: `destructive`, `success`, `secondary`, `outline`, `default`
- Uses `cn()` utility for conditional class names
- Uses lucide-react icons: `AlertTriangle`, `Clock`, `Users`, `ArrowRight`, `FileText`, `Shield`, `Loader2`, `Inbox`
- `formatDate()` helper renders dates as "Apr 24, 2024" format or "Unknown date" for null
- Passes ESLint and TypeScript type checking with zero errors

### Files modified
- `frontend/src/components/insights-dashboard.tsx` (new)
- `agents/architecture.md` (updated frontend structure section)
