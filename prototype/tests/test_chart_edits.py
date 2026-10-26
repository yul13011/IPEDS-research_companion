"""Verify chat commands change rendered charts, with no analytical request."""
from copy import deepcopy
from pathlib import Path
import json,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.analytics import execute,Plan
from prototype.responses import finalize_answer,adjust_presentation


class ChartEditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=execute(Plan(['total_enrollment'],['166939','167835'],list(range(2015,2025))))
        cls.base=finalize_answer({'intent':'analyze','result':cls.result})
        cls.base['presentation']['title']="compare Mount Holyoke's total enrollment with Smith college"

    def test_axis_wording_quotes_and_range_intent(self):
        for prompt in ['Change x-axis to "Year"','Change x-axis label to Year','Set x axis title to “Year”',"Rename the x-axis to 'Year'",'Please change xaxis to Year']:
            edited=adjust_presentation(prompt,self.base)
            self.assertEqual(edited['intent'],'analyze',prompt)
            self.assertEqual(edited['presentation']['x_label'],'Year',prompt)
            self.assertIs(edited['result'],self.result)
        self.assertEqual(adjust_presentation('Change x-axis to 2015–2024',self.base)['intent'],'clarify')
        self.assertEqual(adjust_presentation('Change x-axis to ""',self.base)['intent'],'clarify')
        edited=adjust_presentation('Set y-axis range from -1,000 to 4,000',self.base)
        self.assertEqual([edited['presentation']['y_min'],edited['presentation']['y_max']],[-1000,4000])
        self.assertIsNone(adjust_presentation('Show Harvard applicants in 2023',self.base))

    def test_all_advertised_edits_reach_the_rendered_chart(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        app.session_state['use_ai']=False  # Explicit offline path; AI routing has separate tests.
        app.session_state['main_page']='Ask & Analyze'
        current=deepcopy(self.base);original=deepcopy(current['result'])

        def send(prompt):
            nonlocal current
            # Keep the current answer's accumulated presentation settings while
            # avoiding rendering every prior copy of the same chart in this matrix.
            app.session_state['history']=[{'question':'Enrollment comparison','answer':current}]
            app.run()
            app.chat_input(key='followup_question').set_value(prompt).run()
            self.assertFalse(app.exception,prompt)
            current=app.session_state['history'][-1]['answer']
            self.assertEqual(current.get('mode'),'presentation adjustment',prompt)
            self.assertEqual(current['result'],original,prompt)
            spec=json.loads(app.get('vega_lite_chart')[-1].proto.spec)
            return spec['layer'][0] if 'layer' in spec else spec

        with patch('prototype.ui.ask',side_effect=AssertionError('Display commands must not call the analytical/model pipeline')):
            chart=send('Change x-axis to "Year"')
            self.assertEqual(chart['encoding']['x']['title'],'Year')
            self.assertEqual(chart['encoding']['x']['axis']['values'],[str(y) for y in range(2015,2025)])
            self.assertTrue({'institution','reporting_period','measure','display_value','status'}<={t['field'] for t in chart['encoding']['tooltip']})
            chart=send('Change y-axis to "Students"')
            self.assertEqual(chart['encoding']['y']['title'],'Students')
            chart=send('Set chart title to "Enrollment comparison"')
            self.assertTrue(any('**Enrollment comparison**'==m.value for m in app.markdown))
            self.assertEqual(chart['encoding']['x']['title'],'Year')
            chart=send('Set y-axis range to 1,000–4,000')
            self.assertEqual(chart['encoding']['y']['scale']['domain'],[1000,4000])
            chart=send('Reset y-axis range')
            self.assertNotEqual(chart['encoding']['y']['scale']['domain'],[1000,4000])
            chart=send('Make the lines blue')
            self.assertEqual(chart['encoding']['color']['value'],'blue')
            chart=send('Make it a bar chart')
            self.assertEqual(chart['mark']['type'],'bar')
            chart=send('Make the bars #24658A')
            self.assertEqual(chart['encoding']['color']['value'],'#24658a')
            chart=send('Use a line chart')
            self.assertEqual(chart['mark']['type'],'line')
            send('Show the table')
            tables=app.chat_message[-1].get('dataframe')
            self.assertTrue(any('Value' in t.value.columns for t in tables))
            app.toggle[-1].set_value(False).run()
            self.assertFalse(any('Value' in t.value.columns for t in app.chat_message[-1].get('dataframe')))
            app.toggle[-1].set_value(True).run()
            next(c for c in reversed(app.checkbox) if c.label=='Show underlying counts and data status').check().run()
            self.assertTrue(any('status' in t.value.columns and 'numerator' in t.value.columns for t in app.chat_message[-1].get('dataframe')))
            send('Hide the table')
            tables=app.chat_message[-1].get('dataframe')
            self.assertFalse(any('Value' in t.value.columns for t in tables))

            # Verify sorting on a comparison with one bar per institution.
            single=execute(Plan(['total_enrollment'],['166939','167835'],[2024]))
            current=finalize_answer({'intent':'analyze','result':single});original=deepcopy(single)
            counts={r['institution']:r['value'] for r in single['rows']}
            for prompt,expected in [('Sort bars in ascending order',sorted(counts,key=counts.get)),('Sort bars in descending order',sorted(counts,key=counts.get,reverse=True)),('Sort bars alphabetically',sorted(counts))]:
                chart=send(prompt)
                self.assertEqual(chart['encoding']['y']['sort'],expected)
            percentage=execute(Plan(['admission_rate'],['166939','167835'],[2024]))
            current=finalize_answer({'intent':'analyze','result':percentage});original=deepcopy(percentage)
            chart=send('Set y-axis range to 0–60')
            self.assertEqual(chart['encoding']['x']['scale']['domain'],[0,60])
            app.chat_input(key='followup_question').set_value('Set y-axis range to 0–200').run()
            self.assertEqual(app.session_state['history'][-1]['answer']['intent'],'clarify')
            self.assertEqual(json.loads(app.get('vega_lite_chart')[-1].proto.spec)['layer'][0]['encoding']['x']['scale']['domain'],[0,60])

    def test_valid_edit_after_rejected_edit_still_uses_the_last_chart(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        app.session_state['use_ai']=False  # Explicit offline path; AI routing has separate tests.
        app.session_state['main_page']='Ask & Analyze';app.session_state['history']=[{'question':'Enrollment comparison','answer':deepcopy(self.base)}]
        app.run()
        with patch('prototype.ui.ask',side_effect=AssertionError('No data/model request for display edits')):
            app.chat_input(key='followup_question').set_value('Change the chart font').run()
            self.assertEqual(app.session_state['history'][-1]['answer']['intent'],'clarify')
            app.chat_input(key='followup_question').set_value('Change x-axis to "Year"').run()
        self.assertFalse(app.exception)
        answer=app.session_state['history'][-1]['answer']
        self.assertEqual(answer['presentation']['x_label'],'Year')
        self.assertEqual(answer['result'],self.result)
        self.assertEqual(json.loads(app.get('vega_lite_chart')[-1].proto.spec)['encoding']['x']['title'],'Year')


if __name__=='__main__':unittest.main()
