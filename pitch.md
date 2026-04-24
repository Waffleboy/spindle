# Pitch & Demo Script

## The Pitch (use this verbatim)

"Every analyst I've worked with spends hours cross-referencing reports manually — checking if revenue numbers match, figuring out that 'Tan Kim Bock' and 'Bock Kim Tan' are the same person, spotting which report supersedes which. This tool does that in 30 seconds."

## Wow Statements

Drop these naturally during the demo, not as a rehearsed script:

- **On taxonomy discovery**: "These columns weren't configured. The system read the documents and decided what matters. No predefined categories, no setup wizard, no schema file."
- **On entity resolution**: "It figured out these two names refer to the same person across different reports — and it flagged the ones it wasn't sure about for me to confirm."
- **On contradictions**: "It didn't just extract data — it cross-referenced every report and caught that the revenue figure changed between July and August. It knows which report is newer."
- **On the chat**: "I can ask analytical questions across all reports and get cited answers. It's not just keyword search — it reasons over the structured data it extracted."
- **On extensibility**: "Right now I'm uploading files. In production, this plugs into SharePoint, Slack, Outlook — any source. The pipeline doesn't change."

## Demo Sequence (2-3 minutes)

### Setup (before demo starts)
- Have 4-5 anonymised investor reports pre-uploaded and ready
- Have a fully processed backup dataset in case LLM calls are slow during live demo
- Dark theme on, browser full-screen

### The Flow

**1. Open with the problem (10 seconds)**
Deliver the pitch line above. Keep it conversational.

**2. Upload & Process (20 seconds)**
- Show the documents already uploaded in the left panel
- Optionally type a one-line company profile
- Hit "Process"
- Progress bar runs — briefly explain: "It's detecting the document type, figuring out what to extract, then running extraction, entity resolution, and contradiction detection."

**3. Taxonomy Discovery — THE wow moment (30 seconds)**
- Dashboard populates with the table
- Pause here. Say: "These columns weren't configured. The system read the documents and decided these 8 dimensions matter for investor reports. No one told it what to extract."
- Briefly scan the columns: company name, reporting period, revenue, key personnel, risk factors, etc.

**4. Contradictions (30 seconds)**
- Point to a red-highlighted cell
- Click/hover to show the detail: "Revenue was reported as $4.2M in the August report but $3.9M in the July report"
- Say: "It cross-referenced every report and flagged this automatically. It knows August is newer."

**5. Entity Resolution (20 seconds)**
- Point to a yellow-highlighted cell
- Click to show the alias list: "Tan Kim Bock" = "Bock Kim Tan"
- Say: "It matched these across reports by context. For the ones it's not confident about, it asks me to confirm."
- Click approve on one to show the human-in-the-loop flow

**6. Chat — Analytical Queries (40 seconds)**
- Type: "How did revenue change over the last 3 reports?"
- Show the cited, analytical answer with document references
- Type: "Which reports mention [person name]?"
- Show entity-aware lookup
- Say: "This isn't just search. It reasons over the structured data it extracted, and falls back to the raw documents for anything the taxonomy didn't capture."

**7. Close with the vision (15 seconds)**
- "Right now I'm uploading files manually. But the ingestion layer is pluggable — SharePoint, Slack, Outlook, databases. Same pipeline, no changes."
- "And here's the real moat: every correction a user makes — fixing an entity name, rejecting a taxonomy dimension — improves the system for next time. The taxonomy evolves."

### If something goes wrong
- LLM calls slow? Switch to pre-processed backup: "Let me show you one I prepared earlier" — then continue the demo from step 3.
- API error? Have a screen recording as absolute last resort.

## What Judges Will Remember

1. "It figured out the schema on its own" — nobody else will have this
2. The red contradiction highlight — visual, immediate, undeniable value
3. The chat answer with citations — proves depth, not just a pretty table
