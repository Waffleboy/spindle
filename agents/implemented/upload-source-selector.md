# Upload Source Selector

## Task
Add a source selection UI before the file upload zone in the Document Panel. Users pick from "Sharepoint", "Database", or "Manual Upload" before seeing the drag-and-drop upload interface.

## Implementation
- Added a `uploadSource` state to `DocumentPanel` with values `"select" | "sharepoint" | "database" | "manual"`.
- When in `"select"` mode, three styled buttons are shown with icons (Globe, Database, FolderUp) and descriptions.
- Clicking any option transitions to the existing upload UI (drag-and-drop + staged files + process button).
- A "Back to sources" link lets users return to the source selection screen.
- All three sources currently lead to the same manual upload flow (Sharepoint and Database are UI placeholders for future integration).

## Files Changed
- `frontend/src/components/document-panel.tsx` — Added source selection state, selector UI, and back navigation.
