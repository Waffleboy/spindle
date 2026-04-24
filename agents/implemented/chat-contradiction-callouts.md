# Chat Panel: Contradiction Callout Blocks

## Task
Enhance the chat panel to visually distinguish contradiction and temporal note paragraphs in assistant responses.

## Changes

**File:** `frontend/src/components/chat-panel.tsx`

### What was done
1. Added a `renderContentWithCallouts` function that post-processes assistant response text:
   - Splits response content on newlines into paragraphs
   - Paragraphs matching the pattern `/\bnote:\s|contradiction/i` are rendered as callout blocks with:
     - Warning-colored left border (`border-warning`)
     - Subtle warning background (`bg-warning/5`)
     - An `AlertTriangle` icon from lucide-react
   - Consecutive matching lines are grouped into a single callout block
   - Regular paragraphs render as normal text
   - Blank lines render as line breaks

2. User messages are rendered as plain text (no callout processing).

### Styling
Uses the project's existing `--warning` CSS variable (amber/orange) for both light and dark themes, consistent with the design system.

### No breaking changes
- Citation badges (filename + page indicator) remain unchanged
- Suggested queries, session handling, typing indicator all untouched
- Build, TypeScript, and ESLint all pass clean
