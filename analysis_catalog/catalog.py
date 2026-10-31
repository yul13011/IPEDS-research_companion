"""Read-only evidence API for future catalog-driven planning. Does not execute plans."""
from contextlib import contextmanager
from pathlib import Path
from hashlib import sha256
from functools import lru_cache
import argparse
import json
import os
import re
import sqlite3

BASE = Path(__file__).resolve().parents[1]
# Mirror prototype.catalog: data dir is the repo's data/ by default, or IPEDS_DATA_DIR on a server.
DATA = Path(os.environ.get('IPEDS_DATA_DIR', BASE / 'data'))
TARGET = DATA / 'analysis_catalog.sqlite'
SOURCE = DATA / 'metadata_catalog.sqlite'


@lru_cache(maxsize=4)
def _check_source_identity(source_signature, derived_signature):
    # Cached per file version, never merely per process. Source metadata is immutable
    # in normal operation; rebuilding either catalog invalidates this cache key.
    db = sqlite3.connect(SOURCE.resolve().as_uri() + '?mode=ro', uri=True)
    derived = sqlite3.connect(TARGET.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        counts = {t: db.execute('SELECT COUNT(*) FROM ' + t).fetchone()[0]
                  for t in ['physical_tables','physical_columns','variable_docs','code_values','issues']}
        identity = {'schema': list(db.execute('SELECT type,name,sql FROM sqlite_master ORDER BY type,name')),
                    'files': list(db.execute('SELECT path,sha256 FROM source_files ORDER BY path')),
                    'counts': counts}
        actual = sha256(json.dumps(identity, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
        stored = derived.execute("SELECT value_json FROM build_info WHERE key='source_identity_sha256'").fetchone()
        if not stored or json.loads(stored[0]) != actual:
            raise ValueError('Analytical catalog is stale relative to source metadata; rebuild before using its evidence.')
    finally:
        db.close()
        derived.close()


@contextmanager
def connection():
    _check_source_identity((SOURCE.stat().st_size, SOURCE.stat().st_mtime_ns),
                           (TARGET.stat().st_size, TARGET.stat().st_mtime_ns))
    db = sqlite3.connect(TARGET.resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('ATTACH DATABASE ? AS source', (SOURCE.resolve().as_uri() + '?mode=ro',))
    db.execute('PRAGMA query_only=ON')
    try:
        yield db
    finally:
        db.close()


def decoded(row):
    if row is None:
        return None
    result = {}
    for key in row.keys():
        result[key[:-5] if key.endswith('_json') else key] = json.loads(row[key]) if key.endswith('_json') else row[key]
    return result


def source_record(db, record_id):
    row = db.execute('''SELECT r.record_id,r.release_id,r.kind,r.table_name,r.variable_name,
      r.title,r.body,f.path AS source_file,f.sha256 AS source_sha256,s.sheet_name,r.source_row
      FROM source.records r JOIN source.source_files f USING(source_id)
      LEFT JOIN source.sheets s USING(sheet_id) WHERE r.record_id=?''', (record_id,)).fetchone()
    if row is None:
        raise ValueError(f'Missing source record {record_id}')
    return dict(row)


def table_context(release, table):
    with connection() as db:
        row = db.execute('SELECT * FROM tables WHERE release_id=? AND table_name=? COLLATE NOCASE', (release, table)).fetchone()
        if row is None:
            raise ValueError('Table is not in the supplied physical catalog for this release.')
        context = decoded(row)
        context['source_definitions'] = [source_record(db, i) for i in context['table_document_ids']]
        context['fields'] = [decoded(r) for r in db.execute('''SELECT column_name,physical_type,
          null_count,definition_status,role,semantic_review FROM fields
          WHERE release_id=? AND table_name=? COLLATE NOCASE ORDER BY column_name''', (release, table))]
        context['institution_relationships'] = [decoded(r) for r in db.execute(
            'SELECT * FROM relationships WHERE release_id=? AND from_table=? COLLATE NOCASE', (release, table))]
        context['warnings'] = [dict(r) for r in db.execute('SELECT * FROM source.issues WHERE release_id=? AND table_name=? COLLATE NOCASE', (release, table))]
        context['period_policy'] = 'Use source year_coverage plus variable-specific definitions. Release year is not necessarily observation year. Cohort and multi-period columns require explicit binding.'
        context['population_policy'] = 'Use table and field definitions plus coded row selectors. Category totals/subtotals may overlap; never sum all rows by default.'
        context['aggregation_policy'] = 'No universal additive/ratio/average rule is approved by catalog membership or observed row uniqueness.'
        return context


def categories(release, table, variable, offset=0, limit=100):
    if not 1 <= limit <= 250 or offset < 0:
        raise ValueError('Use a nonnegative offset and category page size 1–250.')
    with connection() as db:
        count = db.execute('''SELECT COUNT(*) FROM source.code_values
          WHERE release_id=? AND table_name=? COLLATE NOCASE AND variable_name=? COLLATE NOCASE''',
                           (release, table, variable)).fetchone()[0]
        rows = db.execute('''SELECT record_id,code_value,value_label FROM source.code_values
          WHERE release_id=? AND table_name=? COLLATE NOCASE AND variable_name=? COLLATE NOCASE
          ORDER BY record_id LIMIT ? OFFSET ?''', (release, table, variable, limit, offset)).fetchall()
        return {'total': count, 'offset': offset, 'limit': limit,
                'next_offset': offset + len(rows) if offset + len(rows) < count else None,
                'codes': [{'code': r['code_value'], 'label': r['value_label'],
                           'evidence': source_record(db, r['record_id'])} for r in rows],
                'policy': 'Source codes are preserved as strings. Missing/not-applicable labels are field-specific; unknown race is not a numeric missing sentinel.'}


def field_context(release, table, column):
    with connection() as db:
        row = db.execute('''SELECT * FROM fields WHERE release_id=?
          AND table_name=? COLLATE NOCASE AND column_name=? COLLATE NOCASE''', (release, table, column)).fetchone()
        if row is None:
            raise ValueError('Physical field not found. Use documented_field() to inspect documentation-only fields.')
        context = decoded(row)
        context['definitions'] = []
        for record_id in context['definition_ids']:
            doc = dict(db.execute('SELECT * FROM source.variable_docs WHERE record_id=?', (record_id,)).fetchone())
            doc['evidence'] = source_record(db, record_id)
            context['definitions'].append(doc)
        context['candidate_definitions'] = [source_record(db, i) for i in context['candidate_definition_ids']]
        context['warnings'] = [dict(db.execute('SELECT * FROM source.issues WHERE issue_id=?', (i,)).fetchone()) for i in context['issue_ids']]
        context['null_policy'] = 'Preserve SQL NULL; no zero substitution. Do not infer not-collected, suppressed, not-applicable or imputed solely from a null or numeric sign.'
        context['unit_policy'] = 'Unit hints are retrieval aids only. Read source definitions for units, scale, denominator and precision; decimal TEXT requires explicit numeric conversion.'
        context['approval_status'] = 'evidence_only_not_an_executable_measure'
    context['categories'] = categories(release, table, column)
    context['table'] = table_context(release, table)
    return context


def documented_field(release, table, variable):
    with connection() as db:
        rows = db.execute('''SELECT * FROM definitions WHERE release_id=?
          AND table_name=? COLLATE NOCASE AND variable_name=? COLLATE NOCASE''', (release, table, variable)).fetchall()
        return [{**decoded(r), 'evidence': source_record(db, r['record_id'])} for r in rows]


def field_history(release, table, variable):
    with connection() as db:
        row = db.execute('SELECT family FROM tables WHERE release_id=? AND table_name=? COLLATE NOCASE', (release, table)).fetchone()
        if not row:
            raise ValueError('Unknown physical table.')
        # Continuity family drops the _P1/_P2 part and consolidation suffix, so a variable
        # chains as one series across the 2022-23 SFA P1/P2 reorganization and the SFA2324
        # consolidation instead of fragmenting by the table label it happened to carry.
        base = re.sub(r'_P\d+$', '', row['family'])
        changes = [decoded(r) for r in db.execute('''SELECT * FROM field_history
          WHERE family=? AND variable_name=? COLLATE NOCASE ORDER BY from_release,to_release''', (base, variable))]
        availability = []
        for r in db.execute('SELECT release_id,collection_cycle FROM source.releases ORDER BY collection_cycle'):
            rows_ = db.execute('''SELECT d.record_id,d.table_name,d.physical_status,
              d.physical_locations_json,t.family AS tfam FROM definitions d
              JOIN tables t ON t.release_id=d.release_id AND t.table_name=d.table_name COLLATE NOCASE
              WHERE d.release_id=? AND d.variable_name=? COLLATE NOCASE''',
                (r['release_id'], variable)).fetchall()
            matches = [{k: v for k, v in decoded(x).items() if k != 'tfam'}
                       for x in rows_ if re.sub(r'_P\d+$', '', x['tfam']) == base]
            availability.append({'release': r['release_id'], 'collection_cycle': r['collection_cycle'],
                                 'status': 'documented' if matches else 'not_documented_in_matched_physical_family',
                                 'matches': matches})
        return {'family': row['family'], 'continuity_family': base, 'variable': variable,
                'availability': availability, 'changes': changes,
                'policy': 'Family/name matching proposes cross-year candidates only. No detected change is not proof of comparability; renamed fields require a reviewed crosswalk.'}


def convention_evidence(release, topic):
    if topic not in {'imputation', 'missing_not_applicable', 'revision_comparability'}:
        raise ValueError('Unknown convention topic.')
    with connection() as db:
        return [source_record(db, r[0]) for r in db.execute(
            'SELECT record_id FROM conventions WHERE release_id=? AND topic=? ORDER BY record_id', (release, topic))]


def search(query, release=None, limit=20):
    """Literal keyword discovery, enriched with availability rather than query approval."""
    if not 1 <= limit <= 100:
        raise ValueError('Search limit must be 1–100.')
    tokens = re.findall(r'[A-Za-z][A-Za-z0-9_]*', query)[:16]
    if not tokens:
        return []
    expression = ' OR '.join('"' + token + '"' for token in tokens)
    with connection() as db:
        conditions = ['search_index MATCH ?', "r.kind IN ('table_definition','variable_definition')"]
        args = [expression]
        if release:
            conditions.append('r.release_id=?')
            args.append(release)
        args.append(limit)
        rows = db.execute('''SELECT r.record_id,r.release_id,r.table_name,r.variable_name,r.kind
          FROM source.search_index JOIN source.records r ON r.record_id=search_index.record_id
          WHERE ''' + ' AND '.join(conditions) + ' ORDER BY bm25(search_index),r.record_id LIMIT ?', args).fetchall()
        result = []
        for row in rows:
            item = source_record(db, row['record_id'])
            if row['kind'] == 'variable_definition':
                status = db.execute('SELECT physical_status FROM definitions WHERE record_id=?', (row['record_id'],)).fetchone()
                item['physical_status'] = status[0] if status else 'not_classified'
            else:
                status = db.execute('SELECT readiness FROM tables WHERE release_id=? AND table_name=? COLLATE NOCASE',
                                    (row['release_id'], row['table_name'])).fetchone()
                item['table_readiness'] = status[0] if status else 'documented_table_not_physical'
            item['approval_status'] = 'discovery_evidence_not_executable_measure'
            result.append(item)
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', required=True)
    parser.add_argument('--table', required=True)
    parser.add_argument('--field')
    parser.add_argument('--history', action='store_true')
    args = parser.parse_args()
    result = (field_history(args.release, args.table, args.field) if args.history and args.field else
              field_context(args.release, args.table, args.field) if args.field else table_context(args.release, args.table))
    print(json.dumps(result, ensure_ascii=True, indent=2))
