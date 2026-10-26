"""Offline regression selection for latency changes and existing behavior."""
from pathlib import Path
import datetime,json,sys,time,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
records=[]
class Recorded(unittest.TextTestResult):
    def startTest(self,test):self.start=time.perf_counter();super().startTest(test)
    def stopTest(self,test):
        records.append({'test':test.id(),'passed':not any(t is test for t,_ in self.failures+self.errors),'seconds':round(time.perf_counter()-self.start,3)})
        super().stopTest(test)
modules=['test_intent_router','test_chart_language','test_chart_edits','test_chart_format',
         'test_purpose','test_memory','test_institution_confirmation','test_chat_loading',
         'test_transcript_scroll','test_trend_followup','test_observations',
         'test_latency_improvements','test_discovery_narrative','test_discovery_interpretation',
         'test_catalog_planner']
suite=unittest.defaultTestLoader.loadTestsFromNames(['prototype.tests.'+m for m in modules])
result=unittest.TextTestRunner(verbosity=1,resultclass=Recorded).run(suite)
(ROOT/'evaluations/latency_verification.json').write_text(json.dumps({
    'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tests':result.testsRun,
    'failures':len(result.failures),'errors':len(result.errors),'cases':records,
    'scope':'Selected offline routes, UI, typed patches, chart exports, conversation, and categorical regressions. Provider transport mocked. Legacy UI tests explicitly select offline mode; separate AI UI tests require initial interpretation.'},indent=2),encoding='utf-8')
raise SystemExit(not result.wasSuccessful())
