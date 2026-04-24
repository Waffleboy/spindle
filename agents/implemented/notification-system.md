# Notification / Toast System

## Task
Add a dismissible notification/toast system to the React frontend that displays at the top-right corner, built from scratch using React context and state (no external library).

## What was done

### 1. Created `frontend/src/lib/notifications.tsx`
- `NotificationType` with id, type (error/success/info/warning), title, optional message, optional duration
- `NotificationContext` with `addNotification` and `removeNotification`
- `NotificationProvider` manages a state array of notifications with auto-dismiss timers
- `useNotifications()` hook for consuming components
- Auto-generates `id` via `crypto.randomUUID()` if not provided
- Default durations: 5000ms for success/info, 8000ms for error/warning
- Timers cleaned up properly on removal and unmount

### 2. Created `frontend/src/components/notifications.tsx`
- Fixed container at `top-4 right-4 z-50`
- Each notification card has: type-specific lucide-react icon, bold title, optional message, X dismiss button
- Color-coded per type using zinc-based dark theme (emerald for success, red for error, blue for info, amber for warning)
- Slide-in animation from right using custom `animate-slide-in-right` keyframe
- Backdrop blur, rounded corners, max-width 400px

### 3. Wired up in `frontend/src/App.tsx`
- Wrapped app in `<NotificationProvider>` with `<NotificationDisplay />` rendered at the top level
- Extracted inner app logic to `AppContent` component so it can use `useNotifications()` hook
- Added notifications for:
  - Upload/process success: "Processing started"
  - Upload/process catch block: "Upload failed" with error message
  - Pipeline status polling: "Processing failed" on error, "Processing complete" on completion

### 4. Added Tailwind animations
- `slideInRight` and `slideOutRight` keyframes added to `tailwind.config.js`

## Files changed
- `frontend/src/lib/notifications.tsx` (new)
- `frontend/src/components/notifications.tsx` (new)
- `frontend/src/App.tsx` (modified)
- `frontend/tailwind.config.js` (modified)
