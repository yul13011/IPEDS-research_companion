"""Natural chart-edit paraphrases, atomicity, and separation from data requests."""
from copy import deepcopy
from pathlib import Path
import json,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.analytics import Plan,execute
from prototype.responses import adjust_presentation,finalize_answer

CASES=[
 ('Make it a bar chart',{'chart_type':'bar'}),
 ('Can you make it a bar chart?',{'chart_type':'bar'}),
 ('Could you please use a line chart?',{'chart_type':'line'}),
 ('Switch this to a bar chart',{'chart_type':'bar'}),
 ('Change the chart to a line chart',{'chart_type':'line'}),
 ('Please hide the legend',{'legend':'none'}),
 ('Can you move the legend to the bottom?',{'legend':'bottom'}),
 ('Show the legend at the top',{'legend':'top'}),
 ('Remove the gridlines',{'gridlines':False}),
 ('Show the point markers',{'markers':True}),
 ('Hide the point markers',{'markers':False}),
 ('Label the latest values',{'value_labels':'latest'}),
 ('Show labels for all points',{'value_labels':'all'}),
 ('Make Smith red',{'series_colors':{'Smith College':'red'}}),
 ("Make Smith's line red",{'series_colors':{'Smith College':'red'}}),
 ('Change the color of Smith to red',{'series_colors':{'Smith College':'red'}}),
 ('Set the font size to 18',{'font_size':18}),
 ('Please set the font size to 18',{'font_size':18}),
 ('Set the background to white',{'background':'white'}),
 ('Change x-axis label to Year',{'x_label':'Year'}),
 ('Can you rename the x-axis to Year?',{'x_label':'Year'}),
 ('Set y-axis range to 1,000–4,000',{'y_min':1000,'y_max':4000}),
 ('Could you set the y-axis range to 1,000–4,000?',{'y_min':1000,'y_max':4000}),
 ('Reset the y-axis range',{'y_min':None,'y_max':None}),
 ('Change the title to "Enrollment, 2015–2024"',{'title':'Enrollment, 2015–2024'}),
 ("Change the title to 'Enrollment, 2015–2024'",{'title':'Enrollment, 2015–2024'}),
 ('Change the title to "Enrollment and show table"',{'title':'Enrollment and show table'}),
 ('Set subtitle to "Students and hide legend"',{'subtitle':'Students and hide legend'}),
 ('Set footnote to "Source: IPEDS; show markers"',{'footnote':'Source: IPEDS; show markers'}),
 ("Set footnote to 'Source: IPEDS; show markers'",{'footnote':'Source: IPEDS; show markers'}),
 ('Make Smith red and move the legend to bottom',{'series_colors':{'Smith College':'red'},'legend':'bottom'}),
 ('Make Smith red and rename the x-axis to Year',{'series_colors':{'Smith College':'red'},'x_label':'Year'}),
 ('Hide the legend and show the table',{'legend':'none','show_table':True}),
 ('Please show the table',{'show_table':True}),
 ('Please hide the table',{'show_table':False}),
 ('Make the lines blue',{'color':'blue'}),
]
REJECT=[
 'Make Smith red and set font size to 999',
 'Can you make the lines dashed?',
 'Please rotate the x-axis labels by 45 degrees',
 'Could you increase the chart font?',
 'Set y-axis range to 4000–1000',
 'Make College red',
]
DATA=[
 'Show Harvard applicants in 2023',
 'Compare Yale, Harvard, and Smith',
 'Show a ten-year trend for Harvard enrollment',
 'Add Princeton to this comparison',
]

def base_answer():
    return finalize_answer({'intent':'analyze','result':execute(Plan(['total_enrollment'],['166939','167835'],list(range(2015,2025))))})

def evaluate(base):
    out=[]
    for prompt,expected in CASES:
        try:
            answer=adjust_presentation(prompt,base)
            actual=(answer or {}).get('presentation',{})
            passed=bool(answer and answer.get('mode')=='presentation adjustment' and answer.get('result') is base['result'])
            passed=passed and all(all(actual.get(k,{}).get(n)==v for n,v in value.items()) if isinstance(value,dict) else actual.get(k)==value for k,value in expected.items())
            # Text in quoted content must not trigger a hidden setting change.
            if 'and show table' in prompt:passed=passed and actual.get('show_table')==base['presentation']['show_table']
            if 'and hide legend' in prompt:passed=passed and actual.get('legend')==base['presentation'].get('legend')
            if 'show markers' in prompt:passed=passed and actual.get('markers')==base['presentation'].get('markers')
            out.append(dict(prompt=prompt,kind='supported',passed=passed,intent=(answer or {}).get('intent'),expected=expected,actual=actual))
        except Exception as exc:out.append(dict(prompt=prompt,kind='supported',passed=False,error=repr(exc)))
    for kind,prompts in [('unsupported_or_invalid',REJECT),('new_data',DATA)]:
        for prompt in prompts:
            try:
                answer=adjust_presentation(prompt,base)
                passed=(answer or {}).get('intent')=='clarify' if kind!='new_data' else answer is None
                out.append(dict(prompt=prompt,kind=kind,passed=passed,intent=(answer or {}).get('intent')))
            except Exception as exc:out.append(dict(prompt=prompt,kind=kind,passed=False,error=repr(exc)))
    return out

class ChartLanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.base=base_answer()
    def test_language_matrix(self):
        before=deepcopy(self.base)
        for case in evaluate(self.base):
            with self.subTest(prompt=case['prompt']):self.assertTrue(case['passed'],case)
        self.assertEqual(self.base,before)

    def test_rejected_compound_and_quotes_do_not_change_chart(self):
        original=deepcopy(self.base)
        for prompt in REJECT:
            answer=adjust_presentation(prompt,self.base)
            self.assertEqual(answer['intent'],'clarify',prompt)
            self.assertNotIn('result',answer)
        self.assertEqual(self.base,original)

    def test_parsed_font_legend_and_quoted_title_reach_export(self):
        from prototype.charts import DEFAULTS,styled,figure_spec,export_figure
        from prototype.charts import panels
        import xml.etree.ElementTree as ET
        answer=adjust_presentation('Please set the font size to 18',self.base)
        answer=adjust_presentation('Hide the legend',answer)
        answer=adjust_presentation('Label the latest values',answer)
        answer=adjust_presentation("Set title to 'Enrollment, 2015–2024'",answer)
        p={**DEFAULTS,**answer['presentation']};panel=panels(answer['result'],p)[0]
        spec=styled(panel,p)
        self.assertEqual(spec['config']['axis']['labelFontSize'],18)
        plot=spec['layer'][0] if 'layer' in spec else spec
        self.assertIsNone(plot['encoding']['color']['legend'])
        svg=export_figure(figure_spec(panel,p,answer['result']),'svg')
        text=' '.join(ET.fromstring(svg).itertext())
        for expected in ['Enrollment, 2015–2024','Source: IPEDS','2,275','2,857']:self.assertIn(expected,text)
        self.assertEqual(answer['result'],self.base['result'])

    def test_ui_language_edits_do_not_call_analytical_pipeline(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        app.session_state['use_ai']=False  # Explicit offline path; AI routing has separate tests.
        app.session_state['main_page']='Ask & Analyze'
        app.session_state['history']=[{'question':'Enrollment','answer':deepcopy(self.base)}]
        app.run();original=deepcopy(self.base['result'])
        with patch('prototype.ui.ask',side_effect=AssertionError('Chart edit reached the data/model route')):
            for prompt in ['Please hide the legend','Can you make it a bar chart?',"Change title to 'Enrollment, 2015–2024'",'Make Smith red and rename the x-axis to Year']:
                app.chat_input(key='followup_question').set_value(prompt).run()
                self.assertFalse(app.exception,prompt);self.assertFalse(app.session_state.get('request_error'),prompt)
                answer=app.session_state['history'][-1]['answer']
                self.assertEqual(answer.get('mode'),'presentation adjustment',prompt)
                self.assertEqual(answer['result'],original)
            app.chat_input(key='followup_question').set_value('Can you make the lines dashed?').run()
            self.assertFalse(app.session_state.get('request_error'))
            self.assertEqual(app.session_state['history'][-1]['answer']['intent'],'clarify')
        spec=json.loads(app.get('vega_lite_chart')[-1].proto.spec)
        self.assertIn('red',json.dumps(spec))

    def test_horizontal_admission_rate_x_range_and_reset_in_ui(self):
        from streamlit.testing.v1 import AppTest
        answer=finalize_answer({'intent':'analyze','result':execute(Plan(['admission_rate'],['Ivy League'],[2024]))})
        original=deepcopy(answer['result'])
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        app.session_state['use_ai']=False  # Explicit offline path; AI routing has separate tests.
        app.session_state['main_page']='Ask & Analyze'
        app.session_state['history']=[{'question':'Compare Ivy League admission rates in fall 2024.','answer':answer}]
        app.run()
        with patch('prototype.ui.ask',side_effect=AssertionError('Range edit must not query data')):
            for prompt,domain in [('Set x-axis range to 0–10',[0,10]),('Reset x-axis range',[0,100]),('reset x-axis range to 0-10',[0,10]),('Reset x-axis range',[0,100])]:
                app.chat_input(key='followup_question').set_value(prompt).run()
                self.assertFalse(app.exception);self.assertFalse(app.session_state.get('request_error'))
                edited=app.session_state['history'][-1]['answer']
                self.assertEqual(edited['mode'],'presentation adjustment')
                self.assertEqual(edited['result'],original)
                spec=json.loads(app.get('vega_lite_chart')[-1].proto.spec)
                plot=spec['layer'][0] if 'layer' in spec else spec
                self.assertEqual(plot['encoding']['x']['scale']['domain'],domain)
                if domain==[0,10]:self.assertNotIn('values',plot['encoding']['x']['axis'])
            app.chat_input(key='followup_question').set_value('Set x-axis range to 0–200').run()
            self.assertEqual(app.session_state['history'][-1]['answer']['intent'],'clarify')
        for prompt in ['Set x-axis range to 2015–2024','Reset x-axis range','reset x-axis range to 0-10']:
            self.assertEqual(adjust_presentation(prompt,self.base)['intent'],'clarify')

if __name__=='__main__':
    if '--evaluate' in sys.argv:
        records=evaluate(base_answer());suffix=sys.argv[-1] if sys.argv[-1] not in {'--evaluate'} else 'baseline'
        path=ROOT/'evaluations'/('chart_language_'+suffix+'.json')
        path.write_text(json.dumps({'cases':records,'passed':sum(c['passed'] for c in records),'total':len(records)},indent=2),encoding='utf-8')
        print(json.dumps({'passed':sum(c['passed'] for c in records),'total':len(records),'failures':[c['prompt'] for c in records if not c['passed']]}))
    else:unittest.main()
