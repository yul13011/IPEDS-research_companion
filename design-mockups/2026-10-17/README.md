# IPEDS interface mockups — design review, October 17, 2026

These are static design concepts generated with the built-in image-generation tool. They are not screenshots of implemented changes. No prototype code or data was changed for this design review.

- `explore-ipeds-v1.png`: default Explore IPEDS landing page with six topic cards and a direct route to asking a question.
- `ask-and-analyze-v1.png`: the conversational workspace with the optional guided query builder open. Browse definitions is collapsed; evaluation/coverage lives under About this prototype in the header.

## Placement of existing functions

| Current function | Proposed location |
| --- | --- |
| Ask a question | Main conversation area |
| Guided analysis | Optional Build a query panel on the right |
| Explore codebooks | Optional Browse definitions panel on the right |
| Evaluation status | About this prototype / Evaluation & coverage in the header |

The builder is shown open to demonstrate its layout; both tools can start collapsed. Need ideas is shown expanded with admissions examples. On narrow screens, optional tools would need to move into a drawer or stack; mobile layout has not been specified by these desktop mockups.

The landing-page topics describe the source data's breadth, not a claim that all corresponding analytical queries already work. The mockup includes a discovery-only scope note. Topic-detail panels, running example questions and contextual follow-up buttons are proposed UI capabilities, not implemented here. The example Yale statistics use the existing fall-2024 reference result (57,517 applicants, 2,227 admits, 3.87%); they are rounded for presentation.

## Generation prompt briefs

Tool: built-in `image_gen.imagegen`, two separate new-image generations; opaque backgrounds, no input/reference images.

**Explore IPEDS prompt:** Create a polished flat desktop UI mockup for IPEDS Research Companion, approximately 1536×1024. Use warm near-white, navy text, muted teal controls, thin borders and generous whitespace. Shared header has Explore IPEDS, Ask & Analyze and About this prototype. Large introduction, Ask a question button, ten-release coverage label, and six cards in a 3×2 grid: Getting in, Who attends, Paying for college, Graduation & degrees, Faculty & staff, About the institution. Include friendly descriptions, official topic subtitles and Explore topic links. No selected topic panel in this default state. Add a note that statistical answers use reviewed measures and other topics support discovery. No invented statistics, browser chrome, perspective or photos.

**Ask & Analyze prompt:** Create a matching flat desktop workspace mockup in the same palette and typography. Keep the conversation as the wide primary column and put optional tools in a narrow right rail. Show Need ideas with admissions examples; a user asks about Yale fall-2024 applicants, admits and admission rate. Show precisely 57,517, 2,227 and 3.87%, a provisional-release label, Data used and definitions with ADM2024/APPLCN/ADMSSN, contextual Compare/Trend/Download controls, and a follow-up composer. Show Build a query open with Yale/admission-rate/2024 fields and Run analysis. Show Browse definitions collapsed beneath it. Put evaluation and coverage under About this prototype in the shared header. Keep tools secondary and preserve conversation context. No extra statistics or crowded dashboard panels.
