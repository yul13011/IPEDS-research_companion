"""Build a derived analytical catalog without modifying source metadata or annual data.

Run from agent-redesign: python -m analysis_catalog.build
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import argparse
import json
import re
import sqlite3
import time

BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE / 'data/metadata_catalog.sqlite'
TARGET = BASE / 'data/analysis_catalog.sqlite'


def js(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def digest(value):
    return sha256(js(value).encode('utf-8')).hexdigest()


def connect(path):
    db = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    db.execute('PRAGMA temp_store=MEMORY')
    return db


def ident(name):
    # Identifiers originate in the physical inventory; quote rather than interpolate raw.
    return '"' + name.replace('"', '""') + '"'


def family(name, year):
    name = name.upper()
    # Year-pair naming is used for Finance and SFA, unlike ordinary survey suffixes.
    name = re.sub(r'^(SFA|SFAV|F)' + str(year - 1)[2:] + str(year)[2:], r'\1{YYPAIR}', name)
    name = name.replace(str(year), '{YEAR}')
    name = re.sub(r'(?<=_)' + str(year)[2:] + r'$', '{YY}', name)
    return name


def survey_base(name, year):
    # Survey + year-pair identity, ignoring the _P1/_P2 part suffix, so a column can be
    # matched to a sibling part of the same survey when the documentation and the physical
    # data disagree on which part holds it.
    return re.sub(r'_P\d+$', '', family(name, year))


def normalize_text(text, year):
    text = ' '.join((text or '').lower().split())
    # Preserve substantive changes, including CIP editions, rather than masking every date.
    return text.replace(str(year), '{year}').replace(str(year - 1), '{previous_year}')


def time_hint(text):
    text = text.lower()
    hints = []
    for label, pattern in [('fall_snapshot', r'\bfall\b|october 15'),
                           ('fiscal_year', r'fiscal year'),
                           ('july_june_period', r'july.*june'),
                           ('academic_year', r'academic year'),
                           ('cohort_outcome', r'cohort|august 31')]:
        if re.search(pattern, text):
            hints.append(label)
    return hints


def unit_hint(doc):
    title = doc['title'].lower()
    text = title + ' ' + doc['long_description'].lower()
    if re.search(r'\b(percent|percentage)\b', title):
        return 'percent'
    if re.search(r'\b(dollars?|salary|salaries|tuition|expenditures?|revenues?)\b', title):
        return 'currency_or_currency_related'
    if re.search(r'\b(students?|enrollment|graduates?|applicants?|staff|employees?)\b', title):
        return 'people_or_people_related'
    if re.search(r'\b(ratio|rate|average)\b', title):
        return 'ratio_or_average_requires_definition'
    if re.search(r'\bdollars?\b', text):
        return 'currency_related_requires_definition'
    return 'not_inferred'


DDL = '''
PRAGMA foreign_keys=ON;
CREATE TABLE build_info(key TEXT PRIMARY KEY,value_json TEXT NOT NULL);
CREATE TABLE tables(
 release_id TEXT,table_name TEXT COLLATE NOCASE,family TEXT,year INTEGER,kind TEXT,
 row_count INTEGER,table_document_ids_json TEXT,period_evidence_json TEXT,
 time_hints_json TEXT,population_evidence_json TEXT,dimension_fields_json TEXT,
 profile_json TEXT,issues_json TEXT,readiness TEXT,
 PRIMARY KEY(release_id,table_name));
CREATE TABLE fields(
 release_id TEXT,table_name TEXT COLLATE NOCASE,column_name TEXT COLLATE NOCASE,
 physical_type TEXT,null_count INTEGER,definition_status TEXT,definition_ids_json TEXT,
 candidate_definition_ids_json TEXT,role TEXT,unit_hints_json TEXT,
 imputation_links_json TEXT,issue_ids_json TEXT,semantic_review TEXT,
 PRIMARY KEY(release_id,table_name,column_name),
 FOREIGN KEY(release_id,table_name) REFERENCES tables);
CREATE TABLE definitions(
 record_id INTEGER PRIMARY KEY,release_id TEXT,table_name TEXT,variable_name TEXT,
 physical_status TEXT,physical_locations_json TEXT,imputation_variable TEXT,
 category_count INTEGER,definition_hash TEXT,normalized_hash TEXT,category_hash TEXT);
CREATE TABLE relationships(
 release_id TEXT,from_table TEXT,to_table TEXT,join_fields_json TEXT,
 cardinality TEXT,orphan_institutions INTEGER,status TEXT,rule TEXT,
 PRIMARY KEY(release_id,from_table,to_table));
CREATE TABLE field_history(
 family TEXT,variable_name TEXT,from_release TEXT,to_release TEXT,
 from_record_id INTEGER,to_record_id INTEGER,changes_json TEXT,status TEXT);
CREATE TABLE conventions(
 release_id TEXT,topic TEXT,record_id INTEGER,scope TEXT,
 PRIMARY KEY(release_id,topic,record_id));
CREATE TABLE review_queue(
 review_id INTEGER PRIMARY KEY,release_id TEXT,table_name TEXT,column_name TEXT,
 category TEXT,details_json TEXT);
CREATE INDEX field_lookup ON fields(column_name,release_id);
CREATE INDEX definition_lookup ON definitions(variable_name,release_id);
CREATE INDEX history_lookup ON field_history(family,variable_name);
CREATE INDEX review_scope ON review_queue(release_id,table_name);
'''


def query_deadline(db, seconds=20):
    deadline = time.monotonic() + seconds
    db.set_progress_handler(lambda: int(time.monotonic() > deadline), 20000)


def profile(db, table, columns, dimensions, expected_rows, candidate_seconds=20):
    """Observed key evidence is never promoted to a semantic key automatically."""
    if 'UNITID' not in columns:
        return {'status': 'no_institution_identifier', 'key_status': 'not_profiled',
                'candidate_key': [], 'query_count': 0}
    q = ident(table)
    query_deadline(db)
    n, distinct_ids, null_ids = db.execute(
        f'SELECT COUNT(*),COUNT(DISTINCT UNITID),SUM(UNITID IS NULL) FROM {q}').fetchone()
    result = {'rows': n, 'distinct_institutions': distinct_ids,
              'null_institution_ids': null_ids or 0, 'expected_rows_match': n == expected_rows,
              'status': 'profiled', 'candidate_key': [], 'key_status': 'unresolved',
              'query_count': 1}
    if not n:
        result['key_status'] = 'empty_table_no_empirical_key'
        return result
    if n == distinct_ids and not null_ids:
        result.update(candidate_key=['UNITID'], key_status='observed_unique_institution_key')
        return result
    # Small code-defined dimensions are a bounded candidate search, not an assertion
    # that all categorical fields are part of a record key.
    dims = [d for d in dimensions if d != 'UNITID' and d in columns]
    dims.sort(key=lambda d: (d in {'LINE', 'SECTION', 'LSTUDY'}, d))
    selectors = ['EFALEVEL','EFLEVEL','EFBAGE','EFCSTATE','EFDELEV','EFFYALEV','EFFYLEV','EFFYDLEV','PSGRTYPE','OMCHRT','GRTYPE','AWLEVELC','ARANK']
    candidates = [['UNITID', d] for d in selectors if d in dims]
    if 0 < len(dims) <= 10:
        candidates.append(['UNITID'] + dims)
    # Named entity selectors are documented identifiers, not category code sets.
    for selector in ['CGUNITID', 'CAMPUSID']:
        if selector in columns:
            candidates.insert(0, ['UNITID', selector])
    for key in candidates[:13]:
        try:
            query_deadline(db, candidate_seconds)
            names = ','.join(ident(k) for k in key)
            result['query_count'] += 1
            duplicate = db.execute(
                f'SELECT 1 FROM {q} GROUP BY {names} HAVING COUNT(*)>1 LIMIT 1').fetchone()
            if duplicate:
                continue
            query_deadline(db)
            nulls = db.execute(f'SELECT COUNT(*) FROM {q} WHERE ' +
                               ' OR '.join(ident(k) + ' IS NULL' for k in key)).fetchone()[0]
            if nulls:
                continue
            result.update(candidate_key=key, key_status='observed_unique_candidate_review_required')
            break
        except sqlite3.OperationalError as exc:
            result.setdefault('candidate_errors', []).append({'key': key, 'error': str(exc)})
    return result


def build(target=TARGET):
    src = connect(SOURCE)
    target = Path(target)
    temporary = target.with_suffix('.building.sqlite')
    if temporary.exists():
        raise ValueError(f'Unfinished build exists: {temporary}')
    out = sqlite3.connect(temporary)
    out.executescript(DDL)
    docs = [dict(r) for r in src.execute('SELECT * FROM variable_docs')]
    table_docs = defaultdict(list)
    for r in src.execute('SELECT * FROM table_docs'):
        table_docs[(r['release_id'], r['table_name'].upper())].append(dict(r))
    direct, by_name, category_codes = defaultdict(list), defaultdict(list), defaultdict(list)
    for d in docs:
        direct[(d['release_id'], d['table_name'].upper(), d['variable_name'].upper())].append(d)
        by_name[(d['release_id'], d['variable_name'].upper())].append(d)
    for r in src.execute('SELECT * FROM code_values ORDER BY record_id'):
        category_codes[(r['release_id'], r['table_name'].upper(), r['variable_name'].upper())].append(dict(r))
    columns, locations = defaultdict(list), defaultdict(list)
    for r in src.execute('SELECT * FROM physical_columns ORDER BY ordinal'):
        r = dict(r)
        columns[(r['release_id'], r['table_name'].upper())].append(r)
        locations[(r['release_id'], r['column_name'].upper())].append(r['table_name'])
    issues = defaultdict(list)
    for r in src.execute('SELECT * FROM issues'):
        issues[(r['release_id'], r['table_name'].upper())].append(dict(r))
    years = {r['release_id']: int(r['collection_cycle'][:4]) for r in src.execute('SELECT * FROM releases')}
    missing_flags = Counter()
    histories = defaultdict(list)
    for d in docs:
        release, tab, var = d['release_id'], d['table_name'].upper(), d['variable_name'].upper()
        exact = [p for p in locations[(release, var)] if p.upper() == tab]
        candidates = locations[(release, var)]
        stored_table, relocated = d['table_name'], None
        if exact:
            status = 'documented_location_present'
        elif candidates:
            status = 'candidate_other_location'
            # Documentation/data label disagreement: when the column is absent from its
            # documented table but physically present in exactly one table of the same
            # survey + year-pair (differing only by part number), the IPEDS dictionary
            # label is wrong, not the data. Correct the stored table to the verified
            # physical location rather than blocking. Origin: the 2022-23 SFA P1/P2
            # reorganization, where varTable labels were transposed vs the Access file.
            unique = sorted({p for p in candidates}, key=str.upper)
            if len(unique) == 1 and survey_base(unique[0], years[release]) == survey_base(tab, years[release]):
                stored_table, status, relocated = unique[0], 'documented_location_present', unique[0]
        else:
            status = 'not_in_supplied_schema'
        codes = category_codes[(release, tab, var)]
        # Frequencies are not definition changes; preserve code/label pairs only.
        cat_hash = digest(sorted(set((c['code_value'], c['value_label']) for c in codes)))
        raw_def = [d['title'], d['long_description'], d['data_type'], d['format'], d['imputation_variable']]
        norm = [normalize_text(x, years[release]) for x in raw_def]
        out.execute('INSERT INTO definitions VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                    (d['record_id'], release, stored_table, d['variable_name'], status,
                     js(exact or candidates), d['imputation_variable'], len(codes), digest(raw_def), digest(norm), cat_hash))
        # Key the cross-year chain on the continuity family (part/consolidation suffix
        # dropped) so a variable links as one series when IPEDS moves it between parts or
        # merges them — e.g. the 2022-23 SFA P1/P2 reorganization and the SFA2324 consolidation.
        histories[(survey_base(tab, years[release]), var)].append((years[release], d, norm, cat_hash, status))
        if relocated:
            out.execute('INSERT INTO review_queue VALUES(NULL,?,?,?,?,?)',
                        (release, d['table_name'], var, 'relocated_to_single_physical_candidate',
                         js({'record_id': d['record_id'], 'documented_table': d['table_name'],
                             'physical_table': relocated, 'candidate_locations': candidates,
                             'automatic_relocation_allowed': True,
                             'basis': 'single same-survey physical candidate; IPEDS dictionary table label corrected to the verified physical location'})))
        elif status != 'documented_location_present':
            out.execute('INSERT INTO review_queue VALUES(NULL,?,?,?,?,?)',
                        (release, d['table_name'], var, status,
                         js({'record_id': d['record_id'], 'candidate_locations': candidates,
                             'automatic_relocation_allowed': False})))
    table_results = []
    current_release, annual = None, None
    physical = list(src.execute('SELECT * FROM physical_tables ORDER BY release_id,table_name'))
    for index, item in enumerate(physical):
        release, table = item['release_id'], item['table_name']
        if release != current_release:
            if annual:
                annual.close()
            annual = connect(item['sqlite_path'])
            current_release = release
        tc = columns[(release, table.upper())]
        names = [c['column_name'].upper() for c in tc]
        td = table_docs[(release, table.upper())]
        kind = 'institution_data' if 'UNITID' in names else 'source_metadata' if not td else 'noninstitution_data_review_required'
        dims = sorted({k[2] for k in category_codes if k[:2] == (release, table.upper()) and category_codes[k] and k[2] in names})
        try:
            observed = profile(annual, table, names, dims, item['sqlite_rows'])
        except sqlite3.OperationalError as exc:
            observed = {'status': 'profile_failed', 'error': str(exc), 'key_status': 'unresolved', 'candidate_key': []}
        tab_issues = issues[(release, table.upper())]
        periods = [{'record_id': d['record_id'], 'year_coverage': d['year_coverage'],
                    'release_status': d['release_status'], 'release_date': d['release_date']} for d in td]
        population = [{'record_id': d['record_id'], 'title': d['title'], 'description': d['description']} for d in td]
        hints = sorted(set(h for d in td for h in time_hint(d['year_coverage'] + ' ' + d['title'])))
        readiness = ('metadata_only' if kind == 'source_metadata' else
                     'evidence_linked_review_required' if td and observed['status'] == 'profiled' else 'unresolved')
        out.execute('INSERT INTO tables VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (release, table, family(table, years[release]), years[release], kind,
                     item['sqlite_rows'], js([d['record_id'] for d in td]), js(periods),
                     js(hints), js(population), js(dims), js(observed),
                     js([i['issue_id'] for i in tab_issues]), readiness))
        if observed['key_status'] not in {'observed_unique_institution_key', 'not_profiled'}:
            out.execute('INSERT INTO review_queue VALUES(NULL,?,?,?,?,?)',
                        (release, table, '', 'record_grain_review', js(observed)))
        for col in tc:
            name = col['column_name'].upper()
            dd = direct[(release, table.upper(), name)]
            alternatives = [] if dd else by_name[(release, name)]
            status = 'exact_definition' if len(dd) == 1 else 'ambiguous_definition' if dd else 'shared_identifier' if name == 'UNITID' else 'candidate_other_location' if alternatives else 'no_definition'
            flags, hints = [], []
            for d in dd:
                hints.append({'record_id': d['record_id'], 'hint': unit_hint(d), 'status': 'not_validated_unit'})
                flag = d['imputation_variable']
                if flag:
                    loc = locations[(release, flag.upper())]
                    fstatus = 'present_same_table' if any(t.upper() == table.upper() for t in loc) else 'other_location_review_required' if loc else 'not_in_supplied_schema'
                    flags.append({'record_id': d['record_id'], 'variable': flag, 'status': fstatus, 'locations': loc})
                    missing_flags[fstatus] += 1
            role = ('institution_identifier' if name == 'UNITID' else
                    'entity_identifier' if name in {'CGUNITID', 'CAMPUSID', 'OLDUNITID'} and dd else
                    'coded_field' if category_codes.get((release, table.upper(), name)) else
                    'source_metadata_field' if kind == 'source_metadata' else
                    'continuous_field' if dd and any(d['format'].lower().startswith('cont') for d in dd) else
                    'text_or_unclassified_field')
            ids = [i['issue_id'] for i in tab_issues if i['variable_name'].upper() in {'', name}]
            review = 'identifier_only' if name == 'UNITID' else 'requires_semantic_review'
            out.execute('INSERT INTO fields VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (release, table, col['column_name'], col['sqlite_type'], col['null_count'], status,
                         js([d['record_id'] for d in dd]), js([d['record_id'] for d in alternatives]),
                         role, js(hints), js(flags), js(ids), review))
            if kind != 'source_metadata' and status not in {'exact_definition', 'shared_identifier'}:
                out.execute('INSERT INTO review_queue VALUES(NULL,?,?,?,?,?)',
                            (release, table, name, 'field_definition_review', js({'definition_status': status})))
        table_results.append({'release': release, 'table': table, 'kind': kind, **observed})
        if index % 10 == 0:
            print(f'Profiled {index+1}/{len(physical)} tables: {release}.{table}', flush=True)
    if annual:
        annual.close()
    # Only institution decoration joins are prepared. No fact-to-fact or cross-year
    # join is inferred merely because identifiers share names.
    for release in years:
        entries = [r for r in table_results if r['release'] == release]
        hd = next((r for r in entries if r['table'].upper() == f'HD{years[release]}'), None)
        if not hd or hd.get('key_status') != 'observed_unique_institution_key':
            continue
        path = next(r['sqlite_path'] for r in physical if r['release_id'] == release)
        db = connect(path)
        for r in entries:
            if r['kind'] != 'institution_data' or r['table'] == hd['table']:
                continue
            try:
                query_deadline(db)
                orphan = db.execute(f'SELECT COUNT(DISTINCT f.UNITID) FROM {ident(r["table"])} f '
                                    f'WHERE NOT EXISTS (SELECT 1 FROM {ident(hd["table"])} h WHERE h.UNITID=f.UNITID)').fetchone()[0]
                status = 'validated_institution_decoration' if orphan == 0 and not r.get('null_institution_ids', 1) else 'unmatched_identifiers_review_required'
            except sqlite3.OperationalError:
                orphan, status = None, 'validation_incomplete'
            out.execute('INSERT INTO relationships VALUES(?,?,?,?,?,?,?,?)',
                        (release, r['table'], hd['table'], js(['UNITID']),
                         'one_to_one' if r.get('key_status') == 'observed_unique_institution_key' else 'many_to_one',
                         orphan, status, 'Same-release LEFT JOIN for institution attributes only. Preserve all source rows; do not infer aggregation, branch consolidation or fact-to-fact joins.'))
        db.close()
    for (fam, var), observations in histories.items():
        by_year = defaultdict(list)
        for x in observations:
            by_year[x[0]].append(x)
        ordered = sorted(by_year)
        for y1, y2 in zip(ordered, ordered[1:]):
            for a in by_year[y1]:
                for b in by_year[y2]:
                    _, da, na, ca, sa = a
                    _, db, nb, cb, sb = b
                    changes = []
                    if da['title'] != db['title']: changes.append('label')
                    if na != nb: changes.append('normalized_definition_or_type')
                    if ca != cb: changes.append('category_codes_or_labels')
                    if sa != sb: changes.append('physical_availability')
                    if y2 != y1 + 1: changes.append('release_gap')
                    if len(by_year[y1]) > 1 or len(by_year[y2]) > 1: changes.append('ambiguous_family_match')
                    out.execute('INSERT INTO field_history VALUES(?,?,?,?,?,?,?,?)',
                                (fam, var, da['release_id'], db['release_id'], da['record_id'], db['record_id'], js(changes),
                                 'changes_require_review' if changes else 'no_detected_change_not_equivalence_proof'))
    # Preserve source guidance at release scope. A keyword hit is evidence to inspect,
    # not an automatic sentinel decoder or an institution/variable-specific rule.
    for r in src.execute("SELECT * FROM records WHERE kind IN ('metadata_definition','introduction','release_note','supplementary_change')"):
        for topic, pattern in [('imputation', r'imput'), ('missing_not_applicable', r'not applicable|missing|not reported|suppres'),
                               ('revision_comparability', r'revis|comparab|chang|CIP')]:
            if re.search(pattern, r['body'] or '', re.I):
                out.execute('INSERT INTO conventions VALUES(?,?,?,?)', (r['release_id'], topic, r['record_id'], 'release_source_guidance_not_automatic_field_rule'))
    source_counts = {t: src.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
                     for t in ['physical_tables', 'physical_columns', 'variable_docs', 'code_values', 'issues']}
    source_identity = {'schema': [tuple(r) for r in src.execute('SELECT type,name,sql FROM sqlite_master ORDER BY type,name')],
                       'files': [tuple(r) for r in src.execute('SELECT path,sha256 FROM source_files ORDER BY path')],
                       'counts': source_counts}
    info = {'built_at': datetime.now(timezone.utc).isoformat(), 'version': 1,
            'source_catalog': str(SOURCE.resolve()), 'source_identity_sha256': digest(source_identity),
            'source_counts': source_counts, 'imputation_link_counts': dict(missing_flags),
            'policy': 'Evidence preparation only. No field or candidate key automatically authorizes a statistical plan. No generic sentinel decoding, aggregation or longitudinal harmonization.'}
    for key, val in info.items():
        out.execute('INSERT INTO build_info VALUES(?,?)', (key, js(val)))
    out.commit()
    check = out.execute('PRAGMA integrity_check').fetchone()[0]
    fk = out.execute('PRAGMA foreign_key_check').fetchall()
    if check != 'ok' or fk:
        raise ValueError(f'Invalid derived catalog: {check}, foreign keys {fk}')
    out.close()
    src.close()
    # Atomic publication of a rebuild; originals and prior source catalog are untouched.
    temporary.replace(target)
    print(js({'output': str(target), **info}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=TARGET)
    build(parser.parse_args().output)
