"""Analytics logging: sharper outcome taxonomy and the derived structured columns.

Offline only — no Google Sheets network. Exercises request_tasks.status / usable and
question_log.fields / _cell / COLUMNS; the sheet append path is not touched here.
"""
import os
os.environ.setdefault('IPEDS_ENGINE', 'v2')
import unittest

from prototype.request_tasks import status, usable, log_outcome
from prototype import question_log as ql


def _result(rows, **extra):
    return {'rows': rows, **extra}


NUMERIC_OK = _result([{'institution': 'Amherst', 'unitid': 1, 'metric': 'DRVC{YEAR}::MASDEG',
                       'value': 0, 'status': 'ok', 'reporting_period': '2023-24'}])
ALL_MISSING = _result([{'institution': 'Amherst', 'unitid': 1, 'metric': 'C{YEAR}_C::CSTOTLT',
                        'value': None, 'status': 'missing', 'reporting_period': '2023-24'}])
LIST_RESULT = _result([{'institution': 'Smith', 'unitid': 2, 'metric': 'IC{YEAR}::DSTNCED1',
                        'value': None, 'status': 'ok', 'response_label': 'Yes'}],
                      result_kind='institution_list', result_schema_version=2)


class OutcomeTests(unittest.TestCase):
    def test_reported_zero_is_answered(self):
        self.assertTrue(usable(NUMERIC_OK))
        self.assertEqual(log_outcome({'intent': 'analyze', 'result': NUMERIC_OK}), 'answered')

    def test_all_missing_is_answered_no_data(self):
        self.assertFalse(usable(ALL_MISSING))
        self.assertEqual(log_outcome({'intent': 'analyze', 'result': ALL_MISSING}), 'answered_no_data')

    def test_institution_list_matches_are_usable(self):
        self.assertTrue(usable(LIST_RESULT))
        self.assertEqual(log_outcome({'intent': 'analyze', 'result': LIST_RESULT}), 'answered')

    def test_refuse_operation_is_refused(self):
        ans = {'intent': 'clarify', 'mode': 'intent clarification',
               'intent_interpretation': {'operation': 'refuse'}}
        self.assertEqual(log_outcome(ans), 'refused')

    def test_clarify_vs_block(self):
        self.assertEqual(log_outcome({'intent': 'clarify', 'mode': 'intent clarification'}), 'needs_clarification')
        self.assertEqual(log_outcome({'intent': 'clarify', 'mode': 'intent validation'}), 'blocked')

    def test_conversation_has_no_result_stays_answered(self):
        self.assertEqual(log_outcome({'intent': 'conversation', 'mode': 'conversation'}), 'answered')

    def test_status_itself_is_unchanged_for_orchestration(self):
        # status() must keep its original values so task_tracking/dependency logic is intact.
        self.assertEqual(status({'intent': 'analyze', 'result': ALL_MISSING}), 'answered')
        self.assertEqual(status({'intent': 'clarify', 'mode': 'intent clarification',
                                 'intent_interpretation': {'operation': 'refuse'}}), 'needs_clarification')


class FieldsTests(unittest.TestCase):
    def _answer(self):
        return {'intent': 'analyze', 'mode': 'catalog language-model planner',
                'resolved_question': 'How many master’s degrees did Amherst award in 2023-24?',
                'narrative_question': 'How many master’s degrees did Amherst award in 2023-24?',
                'intent_interpretation': {'operation': 'fetch', 'relationship': 'new', 'engine': 'v2'},
                'model_usage': {'engine': 'v2', 'model': 'automatic', 'calls': 2, 'estimated_api_usd': 0.01},
                'latency': {'answer_ready_seconds': 3.217},
                'result': NUMERIC_OK}

    def test_fields_cover_every_extra_column(self):
        f = ql.fields(self._answer())
        self.assertEqual(set(f), set(ql.EXTRA_COLUMNS))

    def test_fields_derive_expected_values(self):
        f = ql.fields(self._answer())
        self.assertEqual(f['route'], 'fetch')
        self.assertEqual(f['relationship'], 'new')
        self.assertEqual(f['served_by'], 'catalog language-model planner')
        self.assertEqual(f['engine'], 'v2')
        self.assertEqual(f['model'], 'automatic')
        self.assertEqual(f['est_usd'], 0.01)
        self.assertEqual(f['n_calls'], 2)
        self.assertEqual(f['n_rows'], 1)
        self.assertIs(f['had_value'], True)
        self.assertEqual(f['latency_s'], 3.22)
        self.assertEqual(f['scope'], 'single')
        self.assertEqual(f['topic'], 'completions')
        self.assertIn('Amherst', f['interpreted_as'])

    def test_fields_no_data_answer(self):
        f = ql.fields({'intent': 'analyze', 'result': ALL_MISSING,
                       'intent_interpretation': {'operation': 'fetch'}})
        self.assertIs(f['had_value'], False)
        self.assertEqual(f['n_rows'], 1)

    def test_fields_blank_when_no_answer(self):
        f = ql.fields(None)
        self.assertEqual(set(f), set(ql.EXTRA_COLUMNS))
        self.assertTrue(all(v == '' for v in f.values()))

    def test_fields_never_raises_on_garbage(self):
        for bad in [{}, {'result': None}, {'model_usage': 'x'}, {'latency': None}]:
            self.assertEqual(set(ql.fields(bad)), set(ql.EXTRA_COLUMNS))


class RowShapeTests(unittest.TestCase):
    def test_columns_layout(self):
        self.assertEqual(ql.COLUMNS[:4], ('timestamp', 'session_id', 'question', 'outcome'))
        self.assertEqual(ql.COLUMNS[-1], 'app_version')
        self.assertEqual(ql.COLUMNS[4:-1], ql.EXTRA_COLUMNS)

    def test_cell_coercion(self):
        self.assertEqual(ql._cell(None), '')
        self.assertEqual(ql._cell(True), 'TRUE')
        self.assertEqual(ql._cell(False), 'FALSE')
        self.assertEqual(ql._cell(5), 5)
        self.assertEqual(ql._cell('x'), 'x')

    def test_app_version_is_a_string(self):
        self.assertIsInstance(ql._app_version(), str)


if __name__ == '__main__':
    unittest.main(verbosity=2)
