# Taxonomy Sidebar — Schema + Chat Tabs

## Task
When the Taxonomy tab is active in the center panel, the right sidebar should be tabbed with two tabs: **Schema** (showing the extracted taxonomy schema) and **Chat** (the existing chat panel).

## Changes

### New File
- `frontend/src/components/taxonomy-schema-panel.tsx` — Displays the taxonomy schema in the sidebar:
  - Lists all taxonomy dimensions with type-specific icons (text, number, date, currency, entity, etc.)
  - Shows dimension name, expected_type badge, and description
  - Per-dimension extraction coverage bar (X/N docs extracted)
  - Tooltip with full details on hover
  - Empty state when no taxonomy exists

### Modified Files
- `frontend/src/App.tsx` — Added `sidebarTab` state (`"chat" | "schema"`). When `centerTab === "taxonomy"`, the right sidebar renders tab buttons (Schema, Chat) and switches between `TaxonomySchemaPanel` and `ChatPanel`. On other center tabs, the sidebar shows only Chat as before.
- `frontend/src/components/chat-panel.tsx` — Added optional `embedded` prop. When `embedded=true`, the component omits its outer width/border container and header, allowing it to be nested inside the tabbed sidebar.
- `agents/architecture.md` — Updated to reflect the context-sensitive sidebar and new component.
