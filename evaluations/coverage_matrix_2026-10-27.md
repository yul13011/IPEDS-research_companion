# Coverage sweep matrix

Run 2026-10-27T02:15:21.611532+00:00. Spent **$1.3614** over 30/30 probes.

## Verdict tally

| Verdict | n |
| --- | --- |
| ANSWERED | 12 |
| CORRECT | 7 |
| BLOCKED | 4 |
| OTHER | 3 |
| CLARIFY | 1 |
| ANSWERED? | 1 |
| DEFINED | 1 |
| DISCOVERY-OK | 1 |

## Per-probe

| Family | Probe | Verdict | Detail | ~$ |
| --- | --- | --- | --- | --- |
| C (completions) | How many master's degrees did Yale award in 2023? | **CORRECT** | app=2846 expected=2846 | 0.11889910000000001 |
| C (completions) | How many research doctoral degrees did Harvard award | **CORRECT** | app=758 expected=758 | 0.05273043999999999 |
| C (completions) | Compare the number of bachelor's degrees Yale and Pr | **ANSWERED** | value=1449.0 | 0.00273134 |
| AL (libraries) | How many physical books were in Harvard's library co | **CORRECT** | app=14790270 expected=14790270.0 | 0.042420240000000005 |
| AL (libraries) | How many digital/electronic books does Yale's librar | **CORRECT** | app=2525935 expected=2525935.0 | 0.03422494 |
| SAL (salaries) | What was the average salary of full professors at Sm | **CORRECT** | app=152890 expected=152890 | 0.03773874 |
| SAL (salaries) | Compare the average instructional faculty salary at  | **ANSWERED** | value=115221 | 0.08032234 |
| F (finance) | What was Yale's revenue from tuition and fees in 202 | **BLOCKED** | expected 343599498.0, app gave no number | 0.12294603999999999 |
| F (finance) | What were Yale's total expenses in 2022-23? | **ANSWERED** | value=4563329798 | 0.04508832 |
| F (finance) | What was the value of Harvard's endowment at year en | **ANSWERED** | value=50877680000 | 0.08950322000000001 |
| EAP/S (staff) | How many full-time instructional faculty with facult | **ANSWERED** | value=2881 | 0.06851514 |
| EAP/S (staff) | How many total staff does Smith College employ in 20 | **ANSWERED** | value=1483 | 0.07988714000000001 |
| OM (outcomes) | What share of Yale's entering degree-seeking cohort  | **CORRECT** | app=97 expected=97 | 0.08832802000000001 |
| OM (outcomes) | What is the 8-year completion rate for Pell recipien | **CLARIFY** | The loaded graduation data has a six-year bachelor graduatio | 0.00117664 |
| EFFY (12-mo enroll) | What was Yale's 12-month unduplicated headcount for  | **CORRECT** | app=16416 expected=16416 | 0.045258820000000005 |
| EF (distance ed) | How many Yale students were enrolled exclusively in  | **ANSWERED** | value=56 | 0.023130140000000004 |
| EF (enrollment) | Show Yale's undergraduate enrollment by race and eth | **ANSWERED** | value=28 | 0.00107704 |
| COST/IC (price) | What was the published tuition and fees at Smith Col | **BLOCKED** | expected 61568, app gave no number | 0.09886764 |
| COST/IC (price) | What was the on-campus room and board charge at Moun | **ANSWERED?** | no ground-truth (app=None) | 0.07181872 |
| COST/IC (price) | What was the average net price for grant-aided stude | **BLOCKED** | no ground-truth (app=None) | 0.0012816400000000001 |
| ADM (admissions) | How many of Yale's admitted students submitted ACT s | **BLOCKED** | expected 384, app gave no number | 0.00135814 |
| ADM (admissions) | What are Yale's admissions test score requirements? | **ANSWERED** | value=730.0 | 0.00206612 |
| Aggregate | What was the overall six-year graduation rate for fo | **OTHER** | intent=catalog_plan | 0.13908884 |
| Aggregate | How many public four-year institutions are there in  | **OTHER** | intent=analyze | 0.0011106400000000002 |
| Aggregate | What was the total fall enrollment across all U.S. d | **ANSWERED** | value=19038434.0 | 0.03916524 |
| Definition | What is the definition of the first-year retention r | **DEFINED** |  | 0.00137659 |
| Discovery | What data do you have on institutional finances? | **DISCOVERY-OK** |  | 0.00098624 |
| Trend | Plot Yale's 12-month enrollment from 2015 to 2024. | **OTHER** | intent=task_response | 0.00174054 |
| IC (categorical) | Does Smith College provide on-campus housing? | **ANSWERED** | value=None | 0.054760340000000005 |
| HD (directory) | What city is Smith College located in? | **ANSWERED** | value=None | 0.01385082 |