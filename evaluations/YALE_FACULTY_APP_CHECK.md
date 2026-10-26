# Exact live-app question — October 21, 2026

Submitted **“how many faculty does Yale have?”** through the main app's Ask & Analyze page in a fresh browser session with conversational AI enabled. No earlier faculty definition was present in this session. The app proceeded directly to a statistical answer, without offering a definition clarification.

Displayed answer:

> For Yale University (Fall 2024), Instructional staff, total (total employees): 3,800; Instructional staff, total (full-time employees): 2,995; Instructional staff, total (part-time employees): 805. The reporting period and source definitions are available below.

Definitions & sources displayed **“Population / selection: Instructional staff, total; All staff”**, Fall 2024, from the staff-by-occupation/faculty-and-tenure-status table. The provisional-release warning was visible. Screenshot: `yale_faculty_app_check.png`.

Independent read-only source SQL, EAP2024, Yale UNITID 130794:

| EAPCAT | Occupation | Faculty status | Total | Full-time | Part-time |
|---|---|---|---:|---:|---:|
| 21000 | 210: Instructional staff, total | 0: All staff | 3800 | 2995 | 805 |
| 21010 | 210: Instructional staff, total | 10: With faculty status, total | 3800 | 2995 | 805 |
| 10010 | 100: All staff | 10: With faculty status, total | 5735 | 4688 | 1047 |

**Assessment:** Returned numbers agree exactly with the selected instructional-staff population. At Yale in this release, that population happens to have the same counts as instructional staff explicitly restricted to faculty status. Those filters are nevertheless different definitions and cannot be substituted generally. The broader faculty-status headcount is 5,735, including research/public-service roles beyond instruction. The answer did not explain that alternative or clarify which population the user intended.

This reveals a remaining ambiguity-recognition gap, not an option-selection/execution failure: the new structured clarification workflow was never invoked. No code or methodological defaults were changed during this check. Recorded as F022. Browser response latency/model cost were not instrumented for this UI-only run; no estimates are asserted. Source data remain unchanged and national aggregate testing remains paused.
