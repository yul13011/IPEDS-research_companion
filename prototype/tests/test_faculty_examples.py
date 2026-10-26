"""Reviewed faculty presets: raw-source agreement and both click surfaces."""
import json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.workflows import topics,execute_example,example_by_id
from prototype.catalog import readonly,annual_path
from prototype.responses import finalize_answer
from prototype.charts import panels
from prototype.exports import csv_bytes,excel_bytes

class FacultyExampleTests(unittest.TestCase):
    def test_style_colors_match_salary_chart_and_recolor_actual_bars(self):
        from copy import deepcopy
        from streamlit.testing.v1 import AppTest
        from prototype.chart_format import color_series,DEFAULTS
        a=finalize_answer(execute_example('faculty-salaries'),example_by_id('faculty-salaries')['question'])
        expected={'Yale University':'#24658A','Harvard University':'#C47A28','Princeton University':'#78649B'}
        self.assertEqual(color_series(a['result'],a['presentation']),expected)
        self.assertEqual(len(color_series(a['result'],{**a['presentation'],'chart_type':'line'})),9)
        self.assertEqual(set(color_series(a['result'],{**a['presentation'],'color':'#333333'}).values()),{'#333333'})
        original=deepcopy(a['result']['rows'])
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        app.session_state['use_ai']=False  # Explicit offline path; AI routing has separate tests.
        app.session_state['main_page']='Ask & Analyze';app.session_state['history']=[{'question':example_by_id('faculty-salaries')['question'],'answer':a}];app.run()
        with patch('prototype.ui.ask',side_effect=AssertionError('Color edit must not replan')),patch('prototype.query_engine.execute',side_effect=AssertionError('Color edit must not query data')):
            next(b for b in app.button if b.label=='Format chart').click().run()
            colors={w.label:w.value for w in app.color_picker if w.label!='Background color'}
            self.assertEqual(colors,expected)
            next(w for w in app.color_picker if w.label=='Harvard University').set_value('#112233').run()
            self.assertFalse(app.exception)
            spec=json.loads(app.get('vega_lite_chart')[-1].proto.spec)
            scale=spec['layer'][0]['encoding']['color']['scale']
            actual=dict(zip(scale['domain'],scale['range']))
            self.assertEqual(actual,{**expected,'Harvard University':'#112233'})
            self.assertEqual(next(w for w in app.color_picker if w.label=='Harvard University').value,'#112233')
            app.chat_input(key='followup_question').set_value('Make Princeton green').run()
            self.assertFalse(app.exception)
            answer=app.session_state['history'][-1]['answer']
            self.assertEqual(answer['mode'],'presentation adjustment')
            self.assertEqual(answer['presentation']['series_colors']['Princeton University'],'green')
            self.assertEqual(answer['presentation']['series_colors']['Harvard University'],'#112233')
            self.assertEqual(answer['result']['rows'],original)

    def test_salary_bars_have_clear_gaps_and_match_legend_order(self):
        import re,xml.etree.ElementTree as ET
        from copy import deepcopy
        import vl_convert as vlc
        from prototype.chart_format import DEFAULTS,styled,figure_spec
        a=finalize_answer(execute_example('faculty-salaries'),example_by_id('faculty-salaries')['question'])
        original=deepcopy(a['result']['rows']);ns={'s':'http://www.w3.org/2000/svg'}
        for size in [18,40]:
            p={**DEFAULTS,**a['presentation'],'bar_size':size}
            panel=panels(a['result'],p)[0]
            for export in [False,True]:
                spec=figure_spec(panel,p,a['result'],1200,675) if export else styled(panel,p)
                if not export:spec['width']=650
                root=ET.fromstring(vlc.vegalite_to_svg(spec));bars=[]
                for g in root.findall('.//s:g',ns):
                    if 'mark-rect role-mark' not in g.get('class',''):continue
                    for node in g:
                        m=re.match(r'M[-\d.]+,([-\d.]+)h[-\d.]+v([-\d.]+)',node.get('d',''))
                        if m:bars.append((float(m[1]),float(m[2]),re.search(r'Institution: ([^;]+)',node.get('aria-label',''))[1]))
                self.assertEqual(len(bars),9)
                bars.sort()
                self.assertGreaterEqual(min(bars[i+1][0]-bars[i][0]-bars[i][1] for i in range(8)),6)
                for i in [0,3,6]:self.assertEqual([b[2] for b in bars[i:i+3]],['Yale University','Harvard University','Princeton University'])
        self.assertEqual(a['result']['rows'],original)

    def test_all_values_match_independent_source_rows(self):
        topic=next(t for t in topics() if t['id']=='faculty')
        self.assertEqual(topic['subtitle'],'Faculty & Staff')
        for ex in topic['examples']:
            with self.subTest(example=ex['id']):
                answer=finalize_answer(execute_example(ex['id']),ex['question']);r=answer['result']
                self.assertEqual(answer['mode'],'reviewed example')
                self.assertTrue(csv_bytes(r));self.assertTrue(excel_bytes(r))
                for row in r['rows']:
                    y=row['observation_year']
                    with readonly(annual_path(y)) as db:
                        if ex['id']=='faculty-salaries':
                            rank={'Professor':1,'Associate professor':2,'Assistant professor':3}[row['groups'][0].split(': ',1)[-1]]
                            raw=db.execute('SELECT SAEQ9AT FROM SAL2023_IS WHERE UNITID=? AND ARANK=?',(row['unitid'],rank)).fetchone()[0]
                            self.assertEqual(y,2023)
                        else:
                            raw=db.execute(f'SELECT EAPFT,EAPPT FROM EAP{y} WHERE UNITID=130794 AND EAPCAT=21000 AND OCCUPCAT=210 AND FACSTAT=0').fetchone()[0 if row['metric'].endswith('full_time') else 1]
                        self.assertEqual(row['value'],raw)
                self.assertEqual(len(r['rows']),9 if ex['id']=='faculty-salaries' else 20 if ex['id']=='faculty-changes' else 2)
                if ex['id']=='faculty-changes':
                    self.assertEqual(r['observation_years'],list(range(2015,2025)))
                    self.assertEqual(answer['presentation']['chart_type'],'line')
                    spec=panels(r,answer['presentation'])[0]['chart'].to_dict()
                    self.assertEqual(spec['mark']['type'],'line')
                    data=next(v for v in spec['datasets'].values() if v and 'series_label' in v[0])
                    self.assertEqual(sorted(sum(x['series_label']==s for x in data) for s in {x['series_label'] for x in data}),[10,10])

    def test_click_each_example_from_both_surfaces_without_chat_planning(self):
        from streamlit.testing.v1 import AppTest
        with patch('prototype.ui.ask',side_effect=AssertionError('Preset must not use chat planning')):
            for surface in ['home','ideas']:
                app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
                app.session_state['use_ai']=False  # Explicit offline path; AI routing has separate tests.
                for eid in ['faculty-counts','faculty-salaries','faculty-changes']:
                    if surface=='home':
                        app.button(key='nav_explore').click().run()
                        app.button(key='topic_faculty').click().run()
                    else:
                        app.button(key='nav_ask').click().run()
                        app.selectbox(key='ideas_topic_widget').set_value('faculty').run()
                    app.button(key=surface+'_'+eid).click().run()
                    self.assertFalse(app.exception)
                    self.assertFalse(app.session_state.get('request_error'))
                    a=app.session_state['history'][-1]['answer']
                    self.assertEqual(a['intent'],'analyze');self.assertEqual(a['mode'],'reviewed example')
                    self.assertEqual(app.session_state['history'][-1]['question'],example_by_id(eid)['question'])
                    if eid=='faculty-changes':self.assertEqual(a['presentation']['chart_type'],'line')

    def test_annual_named_templates_keep_scope_bounds(self):
        from prototype.population_annual import annual_plans
        p=json.loads((ROOT/'prototype/faculty_example_plans.json').read_text())['faculty-changes']
        self.assertEqual(len(annual_plans(p)),10)
        for override in [{'institutions':[]},{'annual_years':[2024,2024]},{'annual_years':[2025]}]:
            with self.assertRaises(ValueError):annual_plans({**p,**override})

if __name__=='__main__':unittest.main()
