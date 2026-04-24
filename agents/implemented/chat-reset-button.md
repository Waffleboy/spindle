# Feature: Chat Reset Button

## Task
Add a button to clear/reset the chat conversation.

## Implementation
Added a reset button (rotate icon) to the chat panel that:
- Clears all messages
- Resets suggestions to defaults
- Generates a new session ID (so the backend starts fresh context)

The button appears in two locations depending on mode:
- **Standalone mode**: In the chat header bar (top-right)
- **Embedded mode** (sidebar): In the input bar (left of the text input)

Only visible when there are messages to clear.

## Files Changed
- `frontend/src/components/chat-panel.tsx`
