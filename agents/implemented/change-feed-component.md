# Change Feed Component

## Task
Create `frontend/src/components/change-feed.tsx` — an entity-centric change timeline component accessible from the insights dashboard. Shows how an entity's extracted dimensions changed across multiple documents over time.

## Implementation

### Component: `ChangeFeed`
- **Props:** `entities: EntityType[]`, `initialEntityId?: string`, `onClose?: () => void`
- **Entity selector:** Dropdown at top to choose which entity to view. Auto-selects `initialEntityId` or first entity.
- **Data fetching:** Calls `getEntityTimeline(entityId)` via `useEffect` on `selectedEntityId` change. Includes request cancellation via closure flag to prevent stale updates.
- **Loading state:** Initialized as `true`; spinner shown during fetch.
- **Back button:** Shows "Back to Insights" with ChevronLeft icon when `onClose` is provided.

### Timeline Layout
- Vertical timeline with `border` line and positioned dots at each node.
- Each `TimelineNode` shows:
  - Document filename + date badge (prefixed with "uploaded" for approximate dates)
  - Diff section showing changes from previous document (color-coded by change type)
  - Full dimension values list with low-confidence indicators (<80%)
- Diff color coding:
  - **New** (emerald): `Plus` icon, success badge
  - **Updated** (amber): `RefreshCw` icon, warning badge
  - **Contradiction** (rose): `AlertTriangle` icon, destructive badge

### Sub-components
- `DiffItem` — Renders a single diff with colored dot, badge, and old/new values with arrow
- `TimelineNodeCard` — Renders a timeline node card with document info, diffs, and dimension values

### Design Decisions
- Used existing `Badge`, `Card`, `ScrollArea` UI components
- Followed project's color system: emerald/amber/rose for new/updated/contradiction
- Used `CHANGE_CONFIG` lookup object to avoid repeated conditionals
- Avoided `useCallback` + `useEffect` `setState` pattern to satisfy strict `react-hooks/set-state-in-effect` ESLint rule; instead setState calls only happen in promise callbacks

## Files Changed
- `frontend/src/components/change-feed.tsx` (new)
- `agents/architecture.md` (updated frontend structure)
