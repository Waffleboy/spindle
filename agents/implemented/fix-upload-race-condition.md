# Fix: Upload Instantly Fails + Perpetual Spinners + Retry Button

## Problems
1. When files were uploaded and "Process" was clicked, the frontend immediately showed failure — no error logs appeared in the backend.
2. After a pipeline error, uploaded files showed perpetual loading spinners instead of resetting.
3. Pipeline errors were not logged to the backend console, and the frontend showed a generic error message instead of the actual error.
4. No way to retry processing after a transient error (e.g., SSL/network failure to LLM provider).

## Fixes

### Backend
- `backend/api/routes.py` — Pre-seed `pipeline_status` with a `"running"` entry before launching the background task, and clear stale entries (fixes race condition).
- `backend/pipeline/orchestrator.py` — Added `logger.error()` so pipeline failures appear in the backend console.

### Frontend
- `frontend/src/lib/types.ts` — Added `error` field to `PipelineStatus` interface.
- `frontend/src/lib/notifications.tsx` — Added `actionLabel` and `onAction` fields to `NotificationType` for action buttons on notifications.
- `frontend/src/components/notifications.tsx` — Renders action button in notification card when `actionLabel`/`onAction` are provided.
- `frontend/src/components/document-panel.tsx` — Spinner now only shows when `isProcessing` is true. Unprocessed docs at rest show no icon.
- `frontend/src/App.tsx` — Error notification shows actual backend error message with a "Retry" button (non-auto-dismissing). Stores last processed document IDs in a ref so retry can re-trigger processing. Added `retryProcessing` callback.
