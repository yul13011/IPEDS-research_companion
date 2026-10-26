"""Integration and boundary tests against the complete locally derived catalog."""
import json
import sqlite3
import unittest

from .build import family, ident, profile
from .catalog import (connection, field_context, table_context, documented_field,
                      categories, field_history, search, convention_evidence)

RELEASE = 'IPEDS_2024-25_Provisional'


class AnalyticalCatalogTests(unittest.TestCase):
    def test_duplicate_selectors_do_not_become_a_valid_key(self):
        db = sqlite3.connect(':memory:')
        try:
            db.execute('CREATE TABLE sample(UNITID INTEGER,EFALEVEL INTEGER,value INTEGER)')
            db.executemany('INSERT INTO sample VALUES(?,?,?)', [(1,20,10),(1,20,12)])
            result = profile(db,'sample',['UNITID','EFALEVEL','VALUE'],['EFALEVEL'],2)
            self.assertEqual(result['key_status'], 'unresolved')
            self.assertEqual(result['candidate_key'], [])
        finally:
            db.close()

    def test_grain_separates_counts_from_dimensions(self):
        table = table_context(RELEASE, 'EF2024A')
        self.assertIn('EFALEVEL', table['dimension_fields'])
        self.assertNotIn('EFASIAT', table['dimension_fields'])
        self.assertEqual(table['profile']['candidate_key'], ['UNITID', 'EFALEVEL'])
        self.assertEqual(field_context(RELEASE, 'EF2024A', 'EFASIAT')['role'], 'continuous_field')

    def test_definition_source_and_missing_flags(self):
        context = field_context(RELEASE, 'ef2024a', 'efasiat')
        self.assertEqual(len(context['definitions']), 1)
        self.assertEqual(context['definitions'][0]['title'], 'Asian total')
        self.assertTrue(context['definitions'][0]['evidence']['source_sha256'])
        self.assertEqual(context['imputation_links'][0]['status'], 'not_in_supplied_schema')
        self.assertTrue(convention_evidence(RELEASE, 'imputation'))

    def test_key_is_empirical_not_measure_approval(self):
        table = table_context(RELEASE, 'C2024_A')
        self.assertEqual(table['profile']['key_status'], 'observed_unique_candidate_review_required')
        self.assertIn('CIPCODE', table['profile']['candidate_key'])
        self.assertIn('MAJORNUM', table['profile']['candidate_key'])
        self.assertNotEqual(table['readiness'], 'approved')

    def test_categories_paginate_and_preserve_unknown(self):
        page = categories(RELEASE, 'C2024_A', 'CIPCODE', limit=2)
        self.assertEqual(len(page['codes']), 2)
        self.assertEqual(page['next_offset'], 2)
        following = categories(RELEASE, 'C2024_A', 'CIPCODE', offset=2, limit=2)
        self.assertNotEqual(page['codes'][0]['evidence']['record_id'], following['codes'][0]['evidence']['record_id'])
        unknown = field_context(RELEASE, 'EF2024A', 'EFUNKNT')
        self.assertIn('unknown', unknown['definitions'][0]['title'].lower())
        self.assertNotIn('suppressed', unknown['definitions'][0]['title'].lower())

    def test_documentation_conflicts_never_relocated(self):
        with connection() as db:
            row = db.execute("SELECT * FROM definitions WHERE physical_status='candidate_other_location' LIMIT 1").fetchone()
        docs = documented_field(row['release_id'], row['table_name'], row['variable_name'])
        self.assertEqual(docs[0]['physical_status'], 'candidate_other_location')
        self.assertTrue(docs[0]['physical_locations'])
        self.assertEqual(docs[0]['evidence']['table_name'], row['table_name'])

    def test_change_evidence_and_availability_not_harmonization(self):
        history = field_history(RELEASE, 'C2024_A', 'CIPCODE')
        self.assertEqual(len(history['availability']), 10)
        self.assertTrue(any('category_codes_or_labels' in x['changes'] for x in history['changes']))
        self.assertIn('not proof', history['policy'])
        self.assertEqual(family('F2324_F2', 2024), family('F2223_F2', 2023))
        self.assertEqual(family('DRVEF122024', 2024), 'DRVEF12{YEAR}')

    def test_only_directory_decoration_joins(self):
        with connection() as db:
            rows = list(db.execute('SELECT * FROM relationships'))
        self.assertTrue(rows)
        self.assertTrue(all(r['to_table'] == 'HD' + r['release_id'][6:10] for r in rows))
        for r in rows:
            if r['status'] == 'validated_institution_decoration':
                self.assertEqual(r['orphan_institutions'], 0)

    def test_comparison_group_identifiers_and_unmatched_ids_visible(self):
        table = table_context(RELEASE, 'CUSTOMCGIDS2024')
        self.assertEqual(table['profile']['candidate_key'], ['UNITID','CGUNITID'])
        self.assertEqual(field_context(RELEASE,'CUSTOMCGIDS2024','CGUNITID')['role'], 'entity_identifier')
        self.assertTrue(any(r['status']=='unmatched_identifiers_review_required'
                            and r['orphan_institutions']>0 for r in table['institution_relationships']))

    def test_query_inputs_cannot_become_sql(self):
        with self.assertRaises(ValueError):
            table_context(RELEASE, "EF2024A'; DROP TABLE fields;--")
        with self.assertRaises(ValueError):
            categories(RELEASE, 'EF2024A', 'EFALEVEL', limit=1000)
        with connection() as db:
            with self.assertRaises(sqlite3.OperationalError):
                db.execute('DELETE FROM tables')
            with self.assertRaises(sqlite3.OperationalError):
                db.execute('DELETE FROM source.variable_docs')
        self.assertEqual(ident('a"b'), '"a""b"')

    def test_enriched_search_and_planner_entry_point(self):
        result = search('EFASIAT', release=RELEASE, limit=3)
        self.assertTrue(result)
        self.assertEqual(result[0]['variable_name'], 'EFASIAT')
        self.assertEqual(result[0]['physical_status'], 'documented_location_present')
        from prototype.catalog import analytical_context
        context = analytical_context(RELEASE, 'EF2024A', 'EFASIAT')
        self.assertEqual(len(context['cross_year_evidence']['availability']), 10)
        self.assertEqual(context['approval_status'], 'evidence_only_not_an_executable_measure')


if __name__ == '__main__':
    unittest.main()
