Problem that we're trying to solve:
  1. No autonomous taxonomy discovery. Every product in the market classifies into predefined categories. None discovers, proposes, or refines a taxonomy from a document corpus. 
  2. Content decay is invisible. No product auto-detects stale content, flags contradictions, or triggers review workflows. Knowledge bases rot within weeks.
    - for example, investor reports. a new report in 2025 august for a company X might override information in earlier reports.
    - entity resolution. even within the same dataset (eg, investor reports), the same entity might be called differently.


Possible solution: Taxonomy Discovery & Entity Resolution Engine
What: 
  - Drop in a corpus (can be 1 file, or a series of files), LLM discovers taxonomy dimensions, proposes a schema, human refines, system learns. No predefined categories needed. for "dropping in" this can be manual upload or more realistically connection to sharepoint, slack, outlook, databases, whatever sources of info.

  - theres an entity resolution layer that then looks at the extracted taxonomies and tries to match likely similar entities by context (eg, tan kim bock vs bock kim tan). surfaces things its not confident about for human review. This is to improve data consistency.

  - Moat: The feedback loop — corrections improve the taxonomy itself, not just the classifier.


But im stuck with 

1) is this a good idea? 
2) is this a good idea for the push to prod hackathon? Info on that below.
3) I'm unsure whats the final thing the solution serves. eg, ok taxonomy and entity resolution per row in the table provides consistency and makes it way easier for models to qna over and even structured output, but means the output is another table?


Push to prod:
Every company runs on invisible workflows - messy handoffs, broken processes, repetitive tasks. This hackathon is about fixing that.

Problem Statement:
Bring a real internal workflow problem you've experienced at a company and solve it with AI.

This is a high-energy, in-person sprint. Not hypothetical ideas - we want sharp, practical solutions inspired by actual friction you've experienced inside teams, companies, or organizations. Spend a day turning everyday inefficiencies into AI-native tools using Claude and Genspark.

We’re looking for solutions that:
Automate repetitive internal work
Improve team coordination and decision-making
Reduce operational overhead
Unlock new ways of working with AI inside organizations
What to expect:
5 hours of focused building to turn ideas into working prototypes
Mentorship from the teams behind Claude, Genspark, and ecosystem partners
Access to cutting-edge AI tooling to accelerate your build
Prizes and recognition for standout solutions
📅 Event Details
Theme: Solve internal workflow problems with AI
Date: 24th April 2026
Format: In-person, Singapore
Rules

Follow the Code of Conduct.