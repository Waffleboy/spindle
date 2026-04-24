# Fix: False Contradictions on List-Type Dimensions

## Problem
Contradiction detection (Step 5) was incorrectly flagging different members of list-type dimensions (`entity_list`, `text_list`) as contradictions. For example, `ESG_REPRESENTATIVES` listing "Rachel Goh" in one document and "James Chia" in another was flagged as a contradiction, when these are simply different people listed in different reports.

## Root Cause
The LLM prompt in `step5_contradictions.py` had no awareness of dimension types. It treated all dimensions identically, so when two documents had different values for a list-type dimension, the LLM interpreted them as conflicting scalar values rather than distinct list members.

## Fix
Modified `backend/pipeline/step5_contradictions.py`:

1. **Added dimension type lookup**: Built a `dim_type_map` from `taxonomy.dimensions` to know each dimension's `expected_type`.
2. **Included type in comparison text**: Each dimension comparison now shows its type (e.g., `(type: entity_list)`), giving the LLM context about whether different values are expected.
3. **Updated prompt**: Added explicit rules that for `entity_list` and `text_list` dimensions, different members across documents are NOT contradictions.
4. **Updated system prompt**: Reinforced that list-type dimensions naturally have different entries per document.
