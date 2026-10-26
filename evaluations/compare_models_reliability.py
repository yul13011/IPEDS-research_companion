"""Expanded, predeclared paired acceptance run after reliability repairs.

Pass --live; uses the original benchmark's metering, $5 cap and source checks.
Writes a separate artifact, preserving the original comparison unchanged.
"""
from pathlib import Path
import sys
import compare_models_current as bench

bench.TARGET=bench.ROOT/'evaluations/model_reliability_comparison.json'
if '--automatic' in sys.argv:
    bench.MODELS=['claude-sonnet-5-5','automatic']
    bench.TARGET=bench.ROOT/'evaluations/model_policy_comparison.json'
VARIANTS=[
 ('greeting__help','conversation','Thanks! What can I ask you about?','none'),
 ('definition__long_release','definition','Explain the meaning of admission rate using the 2024–2025 release.','none'),
 ('discovery__variation','discovery','Which variables and information are available about faculty?','none'),
 ('admissions__variation','numerical',"For fall 2024, give Yale's applicant count, admitted count and percent admitted.",'none'),
 ('yield_followup__variation','followup','Of those admitted, how many enrolled, and what percentage is that?','admissions'),
 ('cohort_trend__variation','numerical',"For Yale, chart six-year bachelor's completion rates for each entering cohort from 2009 to 2018 inclusive.",'none'),
 ('services__variation','categorical','For Smith College in the 2024-25 source release, show the reported yes/no responses for academic/career counseling, employment services for current students, and on-campus childcare.','none'),
 ('ma_distance__california','categorical','List California degree-granting schools that report offering distance education courses in the 2024-25 release. Use the institutional yes/no course-offering response.','none'),
 ('axis_reset__variation','chart_edit','Please set the horizontal numeric scale between zero and ten.','chart'),
 ('compound_style__variation','chart_edit',"Use red for Harvard, put the legend below, use 18-point text, and rename the chart exactly 'Admissions, and show table'.",'chart'),
 ('ambiguous_aid__variation','clarification',"In 2024, what share of Yale College students received financial aid?",'none'),
 ('weighted_salary__male','calculation',"For Yale University in the 2024-25 release, calculate the weighted average actual nine-month salary of male full-time nonmedical instructional staff across professor, associate professor and assistant professor ranks. Weight each rank's male nine-month average salary by its male nine-month staff count. Exclude other ranks and the total.",'none'),
 ('mixed__variation','mixed',"For fall 2024 show the percent of applicants admitted at Yale and Harvard; please color the resulting bars blue.",'none')]
bench.CASES+=VARIANTS
original_check=bench.check
def check(label,answer,history,expected):
    base=label.split('__')[0]
    expected=dict(expected)
    if label=='ma_distance__california':
        expected[base]={r[0] for r in bench.sql(2024,"SELECT h.UNITID FROM HD2024 h JOIN IC2024 i USING(UNITID) WHERE h.STABBR='CA' AND h.DEGGRANT=1 AND i.DISTCRS=1")}
    if label=='weighted_salary__male':
        expected[base]=bench.sql(2024,'SELECT SUM(1.0*SA09MAM*SA09MCM)/SUM(SA09MCM) FROM SAL2024_IS WHERE UNITID=130794 AND ARANK IN (1,2,3)')[0][0]
    checks=original_check(base,answer,history,expected)
    if not checks:raise ValueError('Case has no acceptance checks: '+label)
    return checks
bench.check=check
if __name__=='__main__':raise SystemExit(bench.main())
