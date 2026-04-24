# Document Panel: Report Date Display & Ordering

**Date:** 2026-04-24

## Task
Update the frontend document panel to display report dates extracted by the pipeline and order documents by report date (most recent first).

## Problem
Documents in the sidebar had no temporal context. Users couldn't tell when a report was from without opening it.

## Changes

### File: `frontend/src/components/document-panel.tsx`

1. **Added `Calendar` icon import** from lucide-react.
2. **Added `useMemo` import** for memoised sorting.
3. **Added `sortedDocuments` memo** that sorts documents by `report_date` (preferred) falling back to `uploaded_at`, most recent first.
4. **Added `formatDate` helper** that formats ISO date strings as "24 Apr 2024" style.
5. **Added `getDocDateLabel` helper** that returns the date label and whether it's approximate:
   - If `report_date` is available: shows the formatted report date (normal style).
   - If `report_date` is null: shows "uploaded [date]" in italic style so users know the ordering is approximate.
6. **Updated document list rendering** to use `sortedDocuments` and display a date row with a small Calendar icon below the doc type line.
7. **Styling:** `text-[10px]` for the date, `text-muted-foreground/70` for report dates, `text-muted-foreground/50 italic` for approximate upload dates. Calendar icon is `h-2.5 w-2.5`.

## Verification
- TypeScript type-check (`tsc --noEmit`): passed
- ESLint: passed
