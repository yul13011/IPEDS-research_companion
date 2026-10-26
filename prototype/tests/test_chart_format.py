"""Presentation edits preserve evidence and reach rendered UI and image exports."""
from pathlib import Path
from copy import deepcopy
import json,struct,sys,unittest,xml.etree.ElementTree as ET
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.analytics import execute,Plan
from prototype.responses import finalize_answer,adjust_presentation,presentation_for
from prototype.charts import panels
from prototype.charts import DEFAULTS,styled,figure_spec,export_figure

class ChartFormatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=execute(Plan(['total_enrollment'],['166939','167835'],list(range(2015,2025))))
        cls.answer=finalize_answer({'result':cls.result})

    def test_compound_prompt_is_atomic_and_preserves_values(self):
        before=deepcopy(self.result)
        edited=adjust_presentation('Make Mount Holyoke blue, Smith gray, label the latest values, and change the title to "Enrollment, 2015–2024"',self.answer)
        p=edited['presentation'];self.assertEqual(p['title'],'Enrollment, 2015–2024')
        self.assertEqual(p['series_colors'],{'Mount Holyoke College':'blue','Smith College':'gray'})
        self.assertEqual(p['value_labels'],'latest');self.assertIs(edited['result'],self.result)
        self.assertEqual(adjust_presentation('Make Mount Holyoke blue and change the font size to 999',self.answer)['intent'],'clarify')
        self.assertEqual(self.result,before)
        self.assertEqual(adjust_presentation('Make College blue',self.answer)['intent'],'clarify')
        # Numeric commas do not split range commands.
        self.assertEqual(adjust_presentation('Set y-axis range to 1,000–4,000',self.answer)['presentation']['y_max'],4000)
        self.assertIsNone(adjust_presentation('Compare Yale, Harvard, and Smith',self.answer))
        self.assertIsNone(adjust_presentation('Show Yale, Harvard and Smith enrollment',self.answer))
        footnote=adjust_presentation('Set footnote to "Prepared for discussion."',self.answer)
        self.assertEqual(footnote['presentation']['footnote'],'Prepared for discussion.')
        self.assertIs(footnote['result'],self.result)
        self.assertEqual(adjust_presentation('Remove footnote',footnote)['presentation']['footnote'],'')
        for prompt,angle in [('rotate x-axis label angle to horizontal',0),('Make x-axis labels horizontal',0),('Set year tick labels to flat',0),('Rotate x-axis tickmark labels to −45°',-45),('Set label angle to 45 degrees',45)]:
            with self.subTest(prompt=prompt):
                edited=adjust_presentation(prompt,self.answer)
                self.assertEqual(edited['intent'],'clarify')
                self.assertIn('rotation is currently unavailable',edited['message'])
                spec=styled(panels(self.result,{**DEFAULTS,**self.answer['presentation']})[0],{**DEFAULTS,**self.answer['presentation'],'label_angle':angle})
                plot=spec['layer'][0] if 'layer' in spec else spec
                self.assertEqual(plot['encoding']['x']['axis']['labelAngle'],-45)

    def test_rendered_style_and_reference_preserve_gaps(self):
        r=deepcopy(self.result);r['rows'][3].update(value=None,status='missing');before=deepcopy(r)
        p={**DEFAULTS,**presentation_for(r),'legend':'direct','value_labels':'latest','markers':False,'font_size':20,'label_angle':0,'series_colors':{'Mount Holyoke College':'#112233'},'reference_value':2500,'reference_label':'Benchmark'}
        spec=styled(panels(r,p)[0],p)
        self.assertFalse(spec['layer'][0]['mark']['point'])
        self.assertEqual(spec['layer'][0]['mark']['invalid'],'break-paths-show-domains')
        self.assertEqual(spec['layer'][0]['encoding']['x']['axis']['values'],[str(y) for y in range(2015,2025)])
        self.assertEqual(spec['config']['axis']['labelFontSize'],20)
        self.assertIn('#112233',spec['layer'][0]['encoding']['color']['scale']['range'])
        self.assertTrue(any(l.get('mark',{}).get('type')=='rule' for l in spec['layer']))
        self.assertEqual(r,before)
        normal=styled(panels(r,{**p,'legend':'top'})[0],{**p,'legend':'top'})
        self.assertIsNone(normal['layer'][0]['encoding']['strokeDash']['legend'])
        p['separate_panels']=True;parts=panels(r,p);self.assertEqual(len(parts),2)
        self.assertEqual(parts[0]['chart'].to_dict()['encoding']['y']['scale']['domain'],parts[1]['chart'].to_dict()['encoding']['y']['scale']['domain'])

    def test_actual_png_svg_include_data_sources_and_exact_canvas(self):
        p={**DEFAULTS,**presentation_for(self.result),'legend':'direct','value_labels':'latest','title':'Enrollment comparison','label_angle':0,'footnote':'Prepared for the board meeting.'}
        before=deepcopy(self.result)
        for width,height in [(1200,675),(800,600)]:
            spec=figure_spec(panels(self.result,p)[0],p,self.result,width,height)
            svg=export_figure(spec,'svg');root=ET.fromstring(svg)
            content=' '.join(root.itertext())
            for expected in ['Prepared for the board meeting.','Enrollment comparison','Mount Holyoke College','Smith College','2,275','2,857','2015','2024','Source: IPEDS','Fall Enrollment','Provisional']:
                self.assertIn(expected,content)
            self.assertTrue(root.findall('.//{http://www.w3.org/2000/svg}path'))
            png=export_figure(spec,'png',2)
            self.assertEqual(png[:8],b'\x89PNG\r\n\x1a\n')
            self.assertEqual(struct.unpack('>II',png[16:24]),(width*2,height*2))
        self.assertEqual(self.result,before)

    def test_bar_formatting_colors_and_hidden_labels(self):
        r=execute(Plan(['admission_rate'],['166939','167835'],[2024]))
        p={**DEFAULTS,**presentation_for(r),'series_colors':{'Mount Holyoke College':'#112233'},'decimals':2}
        spec=styled(panels(r,p)[0],p)
        self.assertEqual(spec['layer'][0]['encoding']['x']['scale']['domain'],[0,100])
        self.assertIn('#112233',spec['layer'][0]['encoding']['color']['scale']['range'])
        self.assertIn('formatted_label',json.dumps(spec))
        p['value_labels']='none';spec=styled(panels(r,p)[0],p)
        self.assertFalse(any(l.get('mark',{}).get('type')=='text' for l in spec['layer']))

    def test_panel_chat_undo_reset_and_preview_through_real_ui(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        app.session_state['use_ai']=False  # Explicit offline path; AI routing has separate tests.
        app.session_state['main_page']='Ask & Analyze'
        app.session_state['history']=[{'question':'Enrollment comparison','answer':deepcopy(self.answer)}]
        app.run()
        def button(label):return next(b for b in reversed(app.button) if b.label==label)
        with patch('prototype.ui.ask',side_effect=AssertionError('Chart formatting must not query data or call a model')):
            button('Format chart').click().run();self.assertFalse(app.exception)
            next(w for w in app.number_input if w.label=='Axis and legend font size').set_value(20).run()
            next(w for w in app.selectbox if w.label=='Legend').select('direct').run()
            next(w for w in app.checkbox if w.label=='Show point markers').uncheck().run()
            self.assertFalse(app.exception)
            p=app.session_state['chart_formats'][self.result['result_id']]
            self.assertEqual(p['font_size'],20);self.assertFalse(p['markers'])
            next(w for w in app.text_area if w.label=='Footnote').set_value('Prepared for discussion.').run()
            p=app.session_state['chart_formats'][self.result['result_id']]
            self.assertEqual(p['footnote'],'Prepared for discussion.')
            self.assertTrue(any(c.value=='Prepared for discussion.' for c in app.caption))
            button('×').click().run();self.assertFalse(app.exception)
            self.assertFalse(any(b.label=='×' for b in app.button))
            self.assertEqual(app.session_state['chart_formats'][self.result['result_id']],p)
            button('Format chart').click().run()
            self.assertEqual(next(w for w in app.number_input if w.label=='Axis and legend font size').value,20)
            spec=json.loads(app.get('vega_lite_chart')[-1].proto.spec)
            self.assertFalse(spec['layer'][0]['mark']['point'])
            app.chat_input(key='followup_question').set_value('Set chart title to "Presentation test"').run()
            self.assertFalse(app.exception)
            p=app.session_state['history'][-1]['answer']['presentation']
            self.assertEqual(p['font_size'],20);self.assertEqual(p['legend'],'direct');self.assertFalse(p['markers'])
            self.assertEqual(app.session_state['history'][-1]['answer']['result'],self.result)
            button('Preview & download chart').click().run();self.assertFalse(app.exception)
            self.assertFalse(app.error,[e.value for e in app.error])
            self.assertTrue(app.get('download_button'))
            # Dismiss the dialog through a full rerun, then undo the title edit.
            app.run();button('Format chart').click().run();button('Undo').click().run();self.assertFalse(app.exception)
            self.assertNotEqual(app.session_state['chart_formats'][self.result['result_id']].get('title'),'Presentation test')
            button('Reset formatting').click().run();self.assertFalse(app.exception)
            self.assertEqual(app.session_state['chart_formats'][self.result['result_id']]['font_size'],13)

if __name__=='__main__':unittest.main()
