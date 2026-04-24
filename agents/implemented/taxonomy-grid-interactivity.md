# Taxonomy Grid Interactivity

## Problem
The taxonomy dashboard grid displayed extracted data but was mostly non-interactive. Clicking a document in the sidebar filtered the grid down to a single row (hiding all other documents), violating the spec which says clicking should highlight the row with a border glow. Cells had no click interaction beyond contradiction (red) and entity review (amber) cells.

## Changes

### `frontend/src/components/taxonomy-panel.tsx` — Major rewrite
- **Fixed document selection = highlight, not filter**: Selecting a document now highlights its entire row with an indigo ring/glow (`ring-1 ring-inset ring-indigo-500/30 bg-indigo-500/5`) while keeping ALL documents visible. Previously `filteredDocs` filtered to only the selected doc.
- **Clickable document names in grid**: Document filenames in the sticky left column are buttons that toggle selection (same as sidebar click). Visual feedback on hover and selection.
- **Column header info icons + tooltips**: Each dimension column header has an `Info` icon. Hovering shows a tooltip with the dimension's LLM-generated description and expected type (per spec: "small info icon that reveals the LLM's description of why this dimension matters").
- **Cell detail popovers**: Clicking any regular cell with extraction data opens a popover showing confidence (color-coded), source pages, raw vs resolved values, document filename, confirmation status, and dimension description.
- **Entity alias pills in cell popovers**: When a cell's value resolves to a known entity, the popover shows all aliases as pill badges (per spec: "hovering a resolved entity shows a small pill list of all aliases").
- **Header stats badges**: Added "needs review" badge count alongside existing contradictions count.
- **Visual affordances**: cursor-pointer and hover backgrounds on all interactive cells.

### `frontend/src/App.tsx`
- Passes `onSelectDoc={setSelectedDocId}` to TaxonomyPanel for bidirectional doc selection.
