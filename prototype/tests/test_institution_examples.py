"""IC presets: independent raw-source checks and both shared click surfaces."""
import unittest
from pathlib import Path
from unittest.mock import patch
from prototype.workflows import topics,execute_example
from prototype.catalog import readonly,annual_path


class InstitutionExampleTests(unittest.TestCase):
    def test_presets_match_source_values_labels_and_population(self):
        examples=next(t for t in topics() if t['id']=='institution')['examples']
        self.assertEqual(len({e['purpose'] for e in examples}),3)
        with readonly(annual_path(2024)) as db:
            expected={r[0] for r in db.execute("SELECT h.UNITID FROM HD2024 h JOIN IC2024 i ON h.UNITID=i.UNITID WHERE h.STABBR='MA' AND h.DEGGRANT=1 AND i.DSTNCED1=1")}
            for example in examples:
                a=execute_example(example['id']);rows=a['result']['rows']
                self.assertEqual(a['mode'],'reviewed example')
                self.assertEqual(a['presentation']['chart_type'],'none')
                if example['id']=='institution-distance':
                    self.assertEqual({r['unitid'] for r in rows},expected)
                    self.assertEqual(len(expected),83)
                for row in rows:
                    # Field IDs are bound to exact source variables by execution;
                    # independently compare every resulting raw value and label.
                    from analysis_catalog.catalog import connection
                    with connection() as meta:
                        field=meta.execute('SELECT variable_name,release_id FROM definitions WHERE record_id=?',(row['record_id'],)).fetchone()
                        raw=db.execute('SELECT '+field['variable_name']+' FROM IC2024 WHERE UNITID=?',(row['unitid'],)).fetchone()[0]
                        label=meta.execute("SELECT value_label FROM source.code_values WHERE release_id=? AND table_name='IC2024' AND variable_name=? AND code_value=?",(field['release_id'],field['variable_name'],str(raw))).fetchone()[0]
                    self.assertEqual(row['raw_code'],raw)
                    self.assertEqual(row['response_label'],label)
                    self.assertIsNone(row['value'])

    def test_both_click_surfaces_execute_without_model_planning(self):
        from streamlit.testing.v1 import AppTest
        root=Path(__file__).resolve().parents[2]
        examples=next(t for t in topics() if t['id']=='institution')['examples']
        with patch('prototype.ui.ask',side_effect=AssertionError('Preset must not invoke chat planner')):
            for surface in ['home','ideas']:
                app=AppTest.from_file(str(root/'prototype/app.py'),default_timeout=60).run()
                for example in examples:
                    if surface=='home':
                        app.button(key='nav_explore').click().run()
                        app.button(key='topic_institution').click().run()
                    else:
                        app.button(key='nav_ask').click().run()
                        app.selectbox(key='ideas_topic_widget').set_value('institution').run()
                    app.button(key=surface+'_'+example['id']).click().run()
                    self.assertFalse(app.exception)
                    self.assertFalse(app.session_state.get('request_error'))
                    a=app.session_state['history'][-1]['answer']
                    self.assertEqual(a['mode'],'reviewed example')
                    self.assertEqual(a['result']['result_schema_version'],2)
                    self.assertEqual(app.session_state['history'][-1]['question'],example['question'])


if __name__=='__main__':unittest.main()
