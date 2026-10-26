# Build a data extract — static interaction previews

October 17, 2026. Design review only; prototype code, data, catalog and mappings are unchanged. Generated with the built-in image-generation tool. These images extend the earlier two-page mockups.

- `institution-autocomplete-v1.png`: institution step, with Yale and Harvard already selected, the query Smith typed, and three distinct selectable candidates. The names, locations and UNITIDs were checked against HD2024: Smith College (167835, Northampton MA), Johnson C Smith University (198756, Charlotte NC), Hobart William Smith Colleges (191630, Geneva NY). The typed query does not automatically select a candidate.
- `measure-search-v1.png`: measure step after Smith College has been added. A short search-results list, source details and explicit Add controls sit beside the persistent selected-measures list. There is no hundreds-item variable dropdown.

## Design decisions illustrated

The optional builder opens into a spacious focused workspace within Ask & Analyze rather than squeezing all controls into the earlier narrow rail. Proposed steps are Institutions, Measures, Years, Preview & download. Back to conversation preserves the intended context; these transitions have not been implemented. Requests originating in chat could prefill the selections.

Institution autocomplete supports multiple choices and disambiguates full names using city/state/UNITID. Measure search supports concepts/questions/exact variable names, short ranked result pages, optional topic filters, expandable definitions/sources and a persistent selection list across searches. Ready-to-extract versus discovery-only availability must remain explicit. New-measure plan validation/execution is still a separate outstanding task. The proposed Years step would explicitly offer one year, selected years or an inclusive range. Dataset preview and CSV/Excel extraction remain primary outcomes.

## Generation prompt briefs

1. Create a matching flat desktop IPEDS Research Companion mockup in warm near-white, navy and muted teal, approximately 1536×1024. Show the shared Explore IPEDS/Ask & Analyze navigation and a centered Build a data extract panel. Mark Institutions active in the four-step workflow. Show removable Yale University/Harvard University chips and an open autocomplete for Smith containing the exact three verified names, locations and UNITIDs above, with explicit add controls. Show 2 institutions selected and Next: Measures. Avoid extra statistics and unrelated UI.
2. Create the matching Measures step, showing Yale, Harvard and Smith College as scope. Provide a concept/question/variable search containing admission, short topic filters, and three result cards: Admission rate, Applicants and Admitted students. Show the first two added to Your extract and an Add action on the third. Include readable definitions/source-variable details, Ready to extract status, Definition & sources disclosures, Show more matches, and Next: Years. Do not show a long dropdown or invented statistical values.
3. Targeted edit of the measure image: preserve the layout and replace the first card's source-variable line with exactly “First-time undergraduates · Source variables: ADMSSN, APPLCN”, removing an erroneous arithmetic symbol in the initial generated image. The corrected image above is the selected final version.
