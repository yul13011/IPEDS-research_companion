"""Whole chart workflow: source rows, UI state, marks, legends and image exports."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import json,re,struct,sys,time,unittest,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.workflows import execute_example,example_by_id
from prototype.responses import finalize_answer
from prototype.charts import panels
from prototype.chart_format import DEFAULTS,color_series,styled,figure_spec,export_figure
from prototype.catalog import readonly,annual_path

OUT=ROOT/'evaluations/chart_workflow'
NS={'s':'http://www.w3.org/2000/svg'}


def bars_in(svg):
    root=ET.fromstring(svg);bars=[]
    for g in root.findall('.//s:g',NS):
        if 'mark-rect role-mark' not in g.get('class',''):continue
        for node in g:
            shape=re.match(r'M[-\d.]+,([-\d.]+)h[-\d.]+v([-\d.]+)',node.get('d',''))
            label=node.get('aria-label','')
            institution=re.search(r'Institution: ([^;]+)',label)
            if shape and institution:
                bars.append({'y':float(shape[1]),'height':float(shape[2]),'institution':institution[1],
                             'value':re.search(r'Value: \$([\d,]+)',label)[1].replace(',',''),'fill':node.get('fill')})
    return root,bars


class ChartWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OUT.mkdir(parents=True,exist_ok=True)
        cls.answer=finalize_answer(execute_example('faculty-salaries'),example_by_id('faculty-salaries')['question'])
        cls.original=deepcopy(cls.answer['result'])
        with readonly(annual_path(2023)) as db:
            cls.expected={(r[0],r[1]):r[2] for r in db.execute('SELECT UNITID,ARANK,SAEQ9AT FROM SAL2023_IS WHERE UNITID IN (130794,166027,186131) AND ARANK IN (1,2,3)')}
        ranks={'Professor':1,'Associate professor':2,'Assistant professor':3}
        for row in cls.original['rows']:
            rank=ranks[row['groups'][0].split(': ',1)[-1]]
            assert row['value']==cls.expected[row['unitid'],rank]

    def assert_export(self,result,p,tag):
        checks=[];all_panels=panels(result,p)
        for index,panel in enumerate(all_panels):
            for width,height in [(1200,675),(800,600)]:
                spec=figure_spec(panel,p,result,width,height)
                self.assertGreaterEqual(spec['vconcat'][0]['layer'][0]['encoding']['y']['axis']['labelLineHeight'],p['font_size']+2)
                svg=export_figure(spec,'svg');png=export_figure(spec,'png',1)
                base=OUT/f'{tag}_panel{index+1}_{width}x{height}'
                base.with_suffix('.svg').write_bytes(svg);base.with_suffix('.png').write_bytes(png)
                root,bars=bars_in(svg);self.assertEqual((root.get('width'),root.get('height')),(str(width),str(height)))
                self.assertEqual(struct.unpack('>II',png[16:24]),(width,height))
                text=' '.join(root.itertext())
                for required in ['Source: IPEDS','Human Resources','2023-24','SAL2023_IS']:
                    self.assertIn(required,text)
                if p.get('title'):self.assertIn(p['title'],text)
                if p.get('footnote'):self.assertIn(p['footnote'],text)
                names=set(panel['chart'].to_dict()['datasets'][next(k for k,v in panel['chart'].to_dict()['datasets'].items() if v and 'institution' in v[0])][i]['institution'] for i in range(panel['rows']))
                expected=[r for r in result['rows'] if r['institution'] in names and r['status']=='ok']
                self.assertEqual(sorted(int(b['value']) for b in bars),sorted(int(r['value']) for r in expected))
                colors=color_series(result,p)
                for b in bars:self.assertEqual(b['fill'].lower(),colors[b['institution']].lower())
                ordered=sorted(bars,key=lambda b:b['y'])
                if len(ordered)>1:self.assertGreater(min(ordered[i+1]['y']-ordered[i]['y']-ordered[i]['height'] for i in range(len(ordered)-1)),0)
                legends=[g for g in root.findall('.//s:g',NS) if 'role-legend' in g.get('class','')]
                if p['legend']=='none':self.assertFalse(legends)
                elif len(names)>1:
                    self.assertTrue(legends)
                    legend_text=' '.join(' '.join(g.itertext()) for g in legends)
                    for name in names:self.assertIn(name,legend_text)
                checks.append({'file':str(base.relative_to(ROOT)),'values':len(bars),'colors_match':True,'no_bar_overlap':True,'canvas':[width,height]})
        return checks

    def test_whole_salary_workflow_ui_and_exports(self):
        from streamlit.testing.v1 import AppTest
        from prototype import chart_controls
        start=time.perf_counter();answer=deepcopy(self.answer);result=answer['result'];rid=result['result_id'];events=[];exports=[]
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        app.session_state['use_ai']=False  # Explicit offline path; AI routing has separate tests.
        app.session_state['main_page']='Ask & Analyze';app.session_state['history']=[{'question':example_by_id('faculty-salaries')['question'],'answer':answer}];app.run()
        def button(label):return next(b for b in reversed(app.button) if b.label==label)
        def state():return {**DEFAULTS,**app.session_state['history'][-1]['answer']['presentation'],**app.session_state.get('chart_formats',{}).get(rid,{})}
        def check(label):
            self.assertFalse(app.exception);self.assertFalse(app.session_state.get('request_error'))
            self.assertEqual(app.session_state['history'][-1]['answer']['result']['rows'],self.original['rows'])
            p=state();expected=color_series(result,p)
            pickers={w.label:w.value for w in app.color_picker if w.label!='Background color'}
            named={'green':'#008000'}
            self.assertEqual(pickers,{k:named.get(v,v) for k,v in expected.items()})
            actual=[]
            for widget in app.get('vega_lite_chart'):
                s=json.loads(widget.proto.spec)
                def scan(n):
                    mark=n.get('mark',{});kind=mark.get('type') if isinstance(mark,dict) else mark
                    if kind in {'bar','line'}:
                        c=n.get('encoding',{}).get('color',{});scale=c.get('scale',{})
                        if scale.get('domain'):actual.append(dict(zip(scale['domain'],scale['range'])))
                        if kind=='bar' and n.get('encoding',{}).get('yOffset'):
                            self.assertEqual(n['encoding']['yOffset']['scale']['domain'],scale['domain'])
                    for layer in n.get('layer',[]):scan(layer)
                scan(s)
            self.assertEqual({k:v for d in actual for k,v in d.items()},expected)
            events.append(label)
        with patch('prototype.ui.ask',side_effect=AssertionError('Formatting must not plan')),patch('prototype.query_engine.execute',side_effect=AssertionError('Formatting must not execute data queries')):
            button('Format chart').click().run();check('initial grouping/legend/three pickers')
            self.assertFalse(any(w.label in {'Year label angle','Reporting-period label angle'} for w in app.selectbox))
            exports+=self.assert_export(result,state(),'default')
            next(w for w in app.color_picker if w.label=='Harvard University').set_value('#112233').run();check('picker recolors Harvard only')
            next(w for w in app.text_input if w.label=='Chart title').set_value('Faculty salary comparison').run()
            next(w for w in app.text_area if w.label=='Footnote').set_value('Nine-month equivalent; medical-school staff excluded.').run()
            next(w for w in app.slider if w.label=='Bar width').set_value(40).run()
            next(w for w in app.number_input if w.label=='Axis and legend font size').set_value(18).run();check('title footnote large bars and font')
            next(w for w in app.selectbox if w.label=='Legend').set_value('none').run();check('hide legend keeps color controls')
            exports+=self.assert_export(result,state(),'edited_hidden_legend')
            button('Undo').click().run();check('undo restores legend')
            self.assertEqual(state()['legend'],'top')
            next(w for w in app.checkbox if w.label=='Separate series into panels').check().run();check('separate panels retain institutional colors')
            self.assertEqual(len(app.get('vega_lite_chart')),3)
            domains=[json.loads(w.proto.spec)['layer'][0]['encoding']['x']['scale']['domain'] for w in app.get('vega_lite_chart')]
            self.assertTrue(all(d==domains[0] for d in domains))
            exports+=self.assert_export(result,state(),'separate_panels')
            next(w for w in app.checkbox if w.label=='Separate series into panels').uncheck().run()
            next(w for w in app.selectbox if w.label=='Chart type').set_value('line').run();check('line type exposes nine actual series controls')
            self.assertEqual(len([w for w in app.color_picker if w.label!='Background color']),9)
            self.assertFalse(any(w.label in {'Year label angle','Reporting-period label angle'} for w in app.selectbox))
            next(w for w in app.selectbox if w.label=='Chart type').set_value('bar').run();check('bar restores three controls and hides period angle')
            self.assertFalse(any(w.label=='Reporting-period label angle' for w in app.selectbox))
            app.chat_input(key='followup_question').set_value('Make Princeton green').run()
            button('Format chart').click().run();check('prompt preserves Harvard and changes Princeton')
            self.assertEqual(state()['series_colors']['Harvard University'],'#112233')
            self.assertEqual(state()['series_colors']['Princeton University'],'green')
            exports+=self.assert_export(result,state(),'prompt_edited')
            preview_state=deepcopy(state())
            button('Preview & download chart').click().run()
            self.assertFalse(app.exception);self.assertFalse(app.error)
            self.assertEqual(len(app.get('dialog')),1)
            # AppTest widget.run performs full-script reruns, unlike browser
            # fragment reruns. Reinvoke the actual preview in a dedicated harness
            # with the exact edited result/settings to keep its dialog available.
            preview_exports=[]
            def capture_export(spec,kind='png',scale=2):
                data=export_figure(spec,kind,scale)
                w=spec['usermeta']['canvas_width'];h=spec['usermeta']['canvas_height']
                if kind=='png':self.assertEqual(struct.unpack('>II',data[16:24]),(w*scale,h*scale))
                else:
                    _,marks=bars_in(data);self.assertEqual(len(marks),9)
                    self.assertEqual(sorted(int(b['value']) for b in marks),sorted(int(v) for v in self.expected.values()))
                    for b in marks:self.assertEqual(b['fill'].lower(),color_series(result,preview_state)[b['institution']].lower())
                (OUT/f'actual_preview_{w}x{h}.{kind}').write_bytes(data)
                preview_exports.append({'kind':kind,'canvas':[w,h],'scale':scale})
                return data
            chart_controls.image_bytes.clear()
            dialog=AppTest.from_string("from prototype.chart_controls import preview\nimport streamlit as st\npreview(st.session_state['workflow_result'],st.session_state['workflow_settings'],'workflow_dialog')",default_timeout=60)
            dialog.session_state['workflow_result']=deepcopy(result);dialog.session_state['workflow_settings']=preview_state
            with patch('prototype.chart_controls.export_figure',side_effect=capture_export):
                dialog.run()
                next(w for w in dialog.selectbox if w.label=='File type').set_value('SVG').run()
                next(w for w in dialog.selectbox if w.label=='Slide layout').set_value('Half slide · 4:3').run()
                self.assertFalse(dialog.exception);self.assertFalse(dialog.error);self.assertTrue(dialog.get('download_button'))
            self.assertEqual({(x['kind'],tuple(x['canvas'])) for x in preview_exports},{('png',(1200,675)),('svg',(1200,675)),('png',(800,600)),('svg',(800,600))})
            events.append('actual preview function PNG/SVG and full/half-slide controls with exact edited state')
            app.run()
            latest_editor=next(b for b in reversed(app.button) if b.label in {'Format chart','Close formatting'})
            if latest_editor.label=='Format chart':latest_editor.click().run()
            button('Reset formatting').click().run();check('reset defaults')
            self.assertIsNone(state()['title']);self.assertEqual(state()['bar_size'],18)
            button('Undo').click().run();check('undo reset restores edited state')
            self.assertEqual(state()['title'],'Faculty salary comparison')
            button('Reset formatting').click().run();check('final reset')
            exports+=self.assert_export(result,state(),'reset')
        (OUT/'whole_workflow_verification.json').write_text(json.dumps({'events':events,'exports':exports,'actual_preview_exports':preview_exports,'preview_harness_note':'Main app preview-open click tested; dialog controls use the actual preview function with the same edited state because AppTest full-script widget reruns dismiss button-opened dialogs.','independent_source_values':len(self.expected),'source_rows_unchanged':True,'formatting_model_calls':0,'formatting_data_queries':0,'elapsed_seconds':time.perf_counter()-start},indent=2),encoding='utf-8')

    def test_missing_category_and_long_label_exports(self):
        variants=[]
        missing=deepcopy(self.original);missing['rows'][0].update(value=None,status='missing');variants.append(('missing_value',missing))
        absent=deepcopy(self.original);absent['rows'].pop(0);variants.append(('absent_category',absent))
        long=deepcopy(self.original)
        for row in long['rows']:
            row['groups']=[g+' — extended category wording for layout verification' for g in row['groups']]
        variants.append(('long_labels',long))
        checks=[]
        for name,result in variants:
            p={**DEFAULTS,**self.answer['presentation'],'bar_size':40,'font_size':18,'label_size':18}
            before=deepcopy(result['rows']);checks+=self.assert_export(result,p,name)
            self.assertEqual(result['rows'],before)
        (OUT/'edge_case_verification.json').write_text(json.dumps({'scope':'Synthetic presentation fixtures derived from the salary result; not new statistical findings.','checks':checks},indent=2),encoding='utf-8')

if __name__=='__main__':unittest.main()
