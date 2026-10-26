"""Regression runner with wall-clock latency for every test case."""
from pathlib import Path
import datetime
import json
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]


class TimedResult(unittest.TextTestResult):
    def startTest(self,test):
        self.mark=time.perf_counter();super().startTest(test)

    def stopTest(self,test):
        records.append({'case':test.id(),'test_wall_seconds':time.perf_counter()-self.mark,
                        'passed':not any(t is test for t,_ in self.failures+self.errors)})
        super().stopTest(test)


records=[]
suite=unittest.defaultTestLoader.loadTestsFromNames([
    'prototype.tests.test_purpose',
    'prototype.tests.test_institution_examples',
    'prototype.tests.test_observations',
    'prototype.tests.test_definitions',
    'prototype.tests.test_documentation',
    'prototype.tests.test_coverage_gap',
    'prototype.tests.test_units',
    'prototype.tests.test_shared_units',
    'prototype.tests.test_unit_resolution',
    'prototype.tests.test_analysis_clarification',
    'prototype.tests.test_transcript_scroll',
    'prototype.tests.test_chart_density',
    'prototype.tests.test_chart_workflow',
    'prototype.tests.test_faculty_examples',
    'prototype.tests.test_populations',
    'prototype.tests.test_discovery',
    'prototype.tests.test_discovery_narrative',
    'prototype.tests.test_discovery_interpretation',
    'prototype.tests.test_intent_checks',
    'prototype.tests.test_trend_followup',
    'prototype.tests.test_chart_format',
    'prototype.tests.test_chart_edits',
    'prototype.tests.test_chart_language',
    'prototype.tests.test_intent_router',
    'prototype.tests.test_latency_improvements',
    'prototype.tests.test_source_series',
    'prototype.tests.test_result_text','prototype.tests.test_charts','prototype.tests.test_institution_confirmation','prototype.tests.test_memory','prototype.tests.test_query_engine','prototype.tests.test_general_calculations','prototype.tests.test_enrollment_gender','prototype.tests.test_chat_loading','prototype.tests.test_catalog_execution','prototype.tests.test_catalog_planner',
    'prototype.tests.test_prototype','analysis_catalog.test_catalog'])
result=unittest.TextTestRunner(verbosity=2,resultclass=TimedResult).run(suite)
report={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tests_run':result.testsRun,
        'failures':len(result.failures),'errors':len(result.errors),'cases':records,
        'scope':'Real local data and UI checks with mocked provider transport where needed. Per-test wall time can include several requests or UI reruns; it is not live unfamiliar-question response latency. Live timings are in catalog_latency.json.'}
(ROOT/'evaluations/catalog_execution_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
sys.exit(not result.wasSuccessful())





