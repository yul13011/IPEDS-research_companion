"""Trend windows must expand endpoint dates and requery annual source data."""
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import sys,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.agent import ask,canonical_time
from prototype.analytics import execute,Plan
from prototype.responses import finalize_answer,adjust_presentation
from prototype.time_scope import trend_years

class TrendFollowupTests(unittest.TestCase):
    def test_endpoint_duration_variants_and_defaults(self):
        expected=list(range(2015,2025))
        for q in ['Show a 10-year trend.','Show a ten-year trend ending with Fall 2024',
                  'Show a longitudinal trend over the 10 fall terms ending with fall 2024',
                  'Show the past 10 years','Show a longitudinal trend','Show a 10‑year trend']:
            self.assertEqual(trend_years(q),expected,q)
        self.assertEqual(trend_years('Show a 5-year trend ending in 2022'),list(range(2018,2023)))
        self.assertEqual(trend_years('Show a trend for 10 years starting in 2015'),expected)
        self.assertEqual(trend_years('Show a trend',previous_years=list(range(2020,2025))),list(range(2020,2025)))
        self.assertEqual(trend_years('Show a 10-year trend',previous_years=[2024]),expected)
        self.assertIsNone(trend_years('Six-year graduation rate in 2024'))
        self.assertIsNone(trend_years('Enrollment from 2018 through 2024'))
        self.assertIsNone(trend_years('Chart values for 2016, 2019 and 2024'))
        with self.assertRaisesRegex(ValueError,'disagree'):trend_years('10-year trend from 2018 through 2024')
        with self.assertRaisesRegex(ValueError,'1–10'):trend_years('Show the past 11 years')
        with self.assertRaisesRegex(ValueError,'1–10'):trend_years('Show a 0-year trend')

    def test_canonical_binding_overrides_one_year_model_plan(self):
        p={'metrics':['total_enrollment'],'institutions':['166939'],'years':[2024],'time_basis':'observation','output':'answer'}
        expected=list(range(2015,2025))
        fixed=canonical_time('Show a 10-year trend of total enrollment for 166939, ending with fall 2024.',p)
        self.assertEqual(fixed['years'],expected);self.assertEqual(fixed['output'],'chart');self.assertEqual(p['years'],[2024])
        self.assertEqual(canonical_time('Show a 10-year trend ending in fall 2025',p)['years'],list(range(2016,2026)))
        with self.assertRaises(ValueError):Plan(**canonical_time('Show a 10-year trend ending in fall 2025',p)).validate()
        cohort={**p,'metrics':['graduation_rate'],'time_basis':'entry_cohort','years':[2018]}
        fixed=canonical_time('Show a trend by entering cohort',cohort)
        self.assertEqual(fixed['years'],list(range(2009,2019)));self.assertEqual(fixed['time_basis'],'entry_cohort')
        classes={**p,'metrics':['applicants'],'time_basis':'class','years':[2028]}
        fixed=canonical_time('Show a 10-year trend',classes)
        self.assertEqual(fixed['years'],list(range(2019,2029)));self.assertEqual(fixed['time_basis'],'class')
        self.assertEqual(Plan(**fixed).validate(),list(range(2015,2025)))

    def test_catalog_window_precedes_inherited_single_year(self):
        from prototype.catalog_planner import _source_years
        old={'version':1,'source_years':[2024]}
        self.assertEqual(_source_years('Show a 10-year trend.',old),list(range(2015,2025)))
        self.assertEqual(_source_years('Show a longitudinal trend',old),list(range(2015,2025)))
        self.assertEqual(_source_years('Show a longitudinal trend ending in Fall 2024',old),list(range(2015,2025)))
        self.assertEqual(_source_years('Show a trend',{'source_years':list(range(2020,2025))}),list(range(2020,2025)))
        self.assertEqual(_source_years('Show the same table',old),[2024])

    def test_followup_with_actual_bad_resolution_executes_ten_years(self):
        base=execute(Plan(['total_enrollment'],['166939'],[2024],output='answer'))
        before=deepcopy(base)
        history=[{'question':'how many students does mount holyoke have','answer':finalize_answer({'result':base,'plan':base['plan']})}]
        resolved={'kind':'followup','question':'Show a 10-year trend of total enrollment (fall credit headcount) for Mount Holyoke College (UNITID 166939), ending with fall 2024.','referenced_turns':[1]}
        with patch('prototype.memory.resolve',return_value=(resolved,{'calls':1,'latency_seconds':.01})),patch('prototype.agent.model_plan',return_value={'intent':'analyze','plan':{**base['plan'],'output':'chart'}}):
            answer=ask('Show a 10-year trend.',previous=base['plan'],use_model=True,conversation=history)
        self.assertEqual(answer['intent'],'analyze');self.assertEqual(answer['presentation']['chart_type'],'line')
        rows=answer['result']['rows'];self.assertEqual([r['observation_year'] for r in rows],list(range(2015,2025)))
        self.assertTrue(all(r['unitid']==166939 for r in rows));self.assertEqual([r['value'] for r in rows],[2215,2327,2334,2335,2300,2040,2342,2392,2330,2275])
        self.assertEqual(base,before)
        self.assertIsNone(adjust_presentation('Show a 10-year trend.',history[0]['answer']))

    def test_real_chat_followups_render_line_and_all_years(self):
        import json
        from streamlit.testing.v1 import AppTest
        from prototype import agent
        base=execute(Plan(['total_enrollment'],['166939'],[2024],output='answer'))
        a=finalize_answer({'result':base,'plan':base['plan']})
        a['institution_identity']={'unitids':[166939],'confirmed_choices':{'mount holyoke':166939}}
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        app.session_state['main_page']='Ask & Analyze';app.session_state['use_ai']=False
        app.session_state['last_plan']=base['plan'];app.session_state['history']=[{'question':'how many students does mount holyoke have','answer':a}]
        app.run()
        # Real offline reviewed planner and source execution; never a chart-only edit.
        for q in ['Show a 10-year trend.','Show a longitudinal trend']:
            app.chat_input(key='followup_question').set_value(q).run();self.assertFalse(app.exception)
            answer=app.session_state['history'][-1]['answer']
            self.assertIn('presentation',answer,answer)
            self.assertEqual(answer['presentation']['chart_type'],'line')
            self.assertEqual(answer['result']['observation_years'],list(range(2015,2025)))
            spec=json.loads(app.get('vega_lite_chart')[-1].proto.spec)
            self.assertEqual(spec['mark']['type'],'line')
            self.assertEqual(spec['encoding']['x']['axis']['values'],[str(y) for y in range(2015,2025)])

if __name__=='__main__':unittest.main()
