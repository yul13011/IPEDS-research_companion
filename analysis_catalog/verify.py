"""Validate derived coverage and produce inspectable readiness/review inventories."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import csv
import json
import sqlite3

from .catalog import connection, decoded, field_context, field_history, convention_evidence

BASE = Path(__file__).resolve().parents[1]


def verify():
    checks = {}
    with connection() as db:
        checks['integrity'] = db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        checks['source_identity_matches'] = True  # enforced by connection()
        checks['foreign_keys'] = not db.execute('PRAGMA foreign_key_check').fetchall()
        checks['all_physical_tables'] = db.execute('SELECT COUNT(*) FROM tables').fetchone()[0] == db.execute('SELECT COUNT(*) FROM source.physical_tables').fetchone()[0]
        checks['all_physical_fields'] = db.execute('SELECT COUNT(*) FROM fields').fetchone()[0] == db.execute('SELECT COUNT(*) FROM source.physical_columns').fetchone()[0]
        checks['all_variable_definitions'] = db.execute('SELECT COUNT(*) FROM definitions').fetchone()[0] == db.execute('SELECT COUNT(*) FROM source.variable_docs').fetchone()[0]
        checks['physical_coverage_identity'] = db.execute('''SELECT COUNT(*) FROM source.physical_columns p
          LEFT JOIN fields f ON p.release_id=f.release_id AND p.table_name=f.table_name COLLATE NOCASE
            AND p.column_name=f.column_name COLLATE NOCASE WHERE f.column_name IS NULL''').fetchone()[0] == 0
        wrong_bindings = 0
        rows = list(db.execute('SELECT * FROM fields'))
        for field in rows:
            for record in json.loads(field['definition_ids_json']):
                doc = db.execute('SELECT * FROM source.variable_docs WHERE record_id=?', (record,)).fetchone()
                if not doc or (doc['release_id'], doc['table_name'].upper(), doc['variable_name'].upper()) != (field['release_id'], field['table_name'].upper(), field['column_name'].upper()):
                    wrong_bindings += 1
        checks['no_silent_definition_relocation'] = wrong_bindings == 0
        checks['all_profiles_completed'] = db.execute("SELECT COUNT(*) FROM tables WHERE json_extract(profile_json,'$.status')='profile_failed'").fetchone()[0] == 0
        checks['profile_row_counts_match'] = db.execute("SELECT COUNT(*) FROM tables WHERE json_extract(profile_json,'$.expected_rows_match')=0").fetchone()[0] == 0
        checks['no_fact_to_fact_joins'] = all(r['to_table'].upper().startswith('HD') for r in db.execute('SELECT * FROM relationships'))
        checks['no_unmatched_join_approved'] = db.execute("SELECT COUNT(*) FROM relationships WHERE status='validated_institution_decoration' AND orphan_institutions!=0").fetchone()[0] == 0
        checks['unique_target_keys_for_joins'] = db.execute('''SELECT COUNT(*) FROM relationships r
          JOIN tables t ON t.release_id=r.release_id AND t.table_name=r.to_table
          WHERE json_extract(t.profile_json,'$.key_status')!='observed_unique_institution_key' ''').fetchone()[0] == 0
        try:
            db.execute("UPDATE fields SET role='invalid'")
            checks['read_only_api'] = False
        except sqlite3.OperationalError:
            checks['read_only_api'] = True
        counts = {t: db.execute('SELECT COUNT(*) FROM ' + t).fetchone()[0]
                  for t in ['tables', 'fields', 'definitions', 'relationships', 'field_history', 'conventions', 'review_queue']}
        counts['source_category_records'] = db.execute('SELECT COUNT(*) FROM source.code_values').fetchone()[0]
        checks['dimensions_have_category_evidence'] = all(
            db.execute('''SELECT 1 FROM source.code_values WHERE release_id=?
              AND table_name=? COLLATE NOCASE AND variable_name=? COLLATE NOCASE LIMIT 1''',
              (r['release_id'],r['table_name'],name)).fetchone()
            for r in db.execute('SELECT release_id,table_name,dimension_fields_json FROM tables')
            for name in json.loads(r['dimension_fields_json']))
        distributions = {}
        for table, field in [('tables', 'kind'), ('fields', 'definition_status'), ('tables', 'readiness'),
                             ('relationships', 'status'), ('review_queue', 'category')]:
            distributions[f'{table}.{field}'] = dict(db.execute(f'SELECT {field},COUNT(*) FROM {table} GROUP BY {field}'))
        distributions['key_status'] = dict(db.execute("SELECT json_extract(profile_json,'$.key_status'),COUNT(*) FROM tables GROUP BY 1"))
        distributions['imputation_status'] = dict(Counter(link['status'] for r in rows for link in json.loads(r['imputation_links_json'])))
        tables = [decoded(r) for r in db.execute('SELECT * FROM tables ORDER BY release_id,table_name')]
        review = [decoded(r) for r in db.execute('SELECT * FROM review_queue ORDER BY category,release_id,table_name')]
        relationships = [decoded(r) for r in db.execute('SELECT * FROM relationships ORDER BY release_id,from_table')]
    release = 'IPEDS_2024-25_Provisional'
    asian = field_context(release, 'EF2024A', 'EFASIAT')
    checks['enrollment_definition_bound'] = len(asian['definitions']) == 1 and 'Asian' in asian['definitions'][0]['title']
    checks['period_and_population_evidence'] = bool(asian['table']['period_evidence'] and asian['table']['population_evidence'])
    checks['missing_imputation_explicit'] = bool(asian['imputation_links']) and all(x['status'] == 'not_in_supplied_schema' for x in asian['imputation_links'])
    evidence = convention_evidence(release, 'imputation')
    checks['imputation_omission_documented'] = any('not included' in r['body'].lower() or 'not available' in r['body'].lower() for r in evidence)
    cats = field_context(release, 'EF2024A', 'EFALEVEL')['categories']
    checks['undergraduate_category_evidence'] = any(x['code'] == '20' and 'undergraduate' in x['label'].lower() for x in cats['codes'])
    history = field_history(release, 'EF2024A', 'EFASIAT')
    checks['ten_release_availability'] = len(history['availability']) == 10
    checks['no_auto_measure_approval'] = asian['approval_status'] == 'evidence_only_not_an_executable_measure'
    result = {'as_of': datetime.now(timezone.utc).isoformat(), 'passed': all(checks.values()),
              'checks': checks, 'counts': counts, 'distributions': distributions,
              'scope': 'Full derived-catalog linkage, observed institution keys/grain, same-release directory join candidates, source guidance and cross-year change evidence. Not a broad question-answer accuracy evaluation or semantic approval of every field.'}
    path = BASE / 'data/analysis_catalog_verification.json'
    path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    with (BASE / 'data/analysis_table_coverage.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['release','table','family','kind','rows','readiness','key_status','candidate_key','period_evidence','source_table_definition_ids'])
        writer.writeheader()
        for t in tables:
            writer.writerow({'release': t['release_id'], 'table': t['table_name'], 'family': t['family'],
                             'kind': t['kind'], 'rows': t['row_count'], 'readiness': t['readiness'],
                             'key_status': t['profile']['key_status'], 'candidate_key': json.dumps(t['profile'].get('candidate_key', [])),
                             'period_evidence': json.dumps(t['period_evidence']), 'source_table_definition_ids': json.dumps(t['table_document_ids'])})
    with (BASE / 'data/analysis_catalog_review_queue.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['release_id','table_name','column_name','category','details'])
        writer.writeheader()
        for r in review:
            writer.writerow({k: json.dumps(r[k]) if k == 'details' else r[k] for k in writer.fieldnames})
    with (BASE / 'data/analysis_relationship_coverage.csv').open('w', encoding='utf-8-sig', newline='') as f:
        names = ['release_id','from_table','to_table','join_fields','cardinality','orphan_institutions','status','rule']
        writer = csv.DictWriter(f, fieldnames=names)
        writer.writeheader()
        for r in relationships:
            writer.writerow({**r, 'join_fields': json.dumps(r['join_fields'])})
    (BASE / 'data/analysis_field_example.json').write_text(json.dumps(asian, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    verify()
