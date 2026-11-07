"""Read-only access to source documentation and annual data locations."""
from contextlib import contextmanager
from pathlib import Path
import re
import sqlite3
import time
import json
import os
from hashlib import sha256

BASE = Path(__file__).resolve().parents[1]
# Data dir is the local repo's data/ by default; on a server set IPEDS_DATA_DIR to a path
# (e.g. a persistent disk) that data_bootstrap.ensure_data() has populated from the HF dataset.
DATA = Path(os.environ.get("IPEDS_DATA_DIR", BASE / "data"))


def evidence_hash(items):
    return sha256(json.dumps(items,sort_keys=True,ensure_ascii=False).encode('utf-8')).hexdigest()


@contextmanager
def readonly(path,deadline_seconds=20):
    db = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    deadline = time.monotonic() + deadline_seconds
    db.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
    try:
        yield db
    finally:
        db.close()


def annual_path(year):
    paths = list((DATA / "annual").glob(f"IPEDS_{year}-*/*.sqlite"))
    if len(paths) != 1:
        raise ValueError(f"No unique annual database for {year}; available observation years are 2015–2024.")
    return paths[0]


def evidence(db, release, table, columns):
    """Read original definitions, physical locations and issues before any data query."""
    items = []
    for column in columns:
        physical = db.execute(
            "SELECT 1 FROM physical_columns WHERE release_id=? AND table_name=? AND column_name=?",
            (release, table, column),
        ).fetchone()
        if not physical:
            raise ValueError(f"Missing physical column: {release}.{table}.{column}")
        docs = db.execute("""SELECT v.record_id,v.table_name AS documented_table,v.variable_name,
            v.title,v.long_description,f.path AS source_file,s.sheet_name,r.source_row
            FROM variable_docs v JOIN records r USING(record_id)
            JOIN source_files f ON f.source_id=r.source_id LEFT JOIN sheets s ON s.sheet_id=r.sheet_id
            WHERE v.release_id=? AND v.variable_name=? COLLATE NOCASE
            ORDER BY CASE WHEN v.table_name=? COLLATE NOCASE THEN 0 ELSE 1 END,v.record_id""",
            (release, column, table)).fetchall()
        if not docs:
            raise ValueError(f"No codebook definition for {release}.{column}")
        same = [r for r in docs if r['documented_table'].lower() == table.lower()]
        if not same:
            # Only the reviewed SFA location correction is eligible for this prototype.
            if column not in {'SCUGRAD', 'UAGRNTN', 'UAGRNTP'} or not table.lower().startswith('sfa'):
                raise ValueError(f"Unreviewed documentation location conflict for {column}")
            docs = [r for r in docs if r['documented_table'].lower().startswith('sfa')]
        else:
            docs = same
        if len(docs) != 1:
            raise ValueError(f"Ambiguous codebook definition for {release}.{column}")
        item = dict(docs[0])
        item.update(physical_table=table, location_override=not bool(same))
        item['issues'] = [dict(r) for r in db.execute(
            "SELECT issue_type,description,status FROM issues WHERE source_record_id=?", (item['record_id'],))]
        item['codes'] = [dict(r) for r in db.execute(
            "SELECT record_id,code_value,value_label FROM code_values WHERE release_id=? AND table_name=? COLLATE NOCASE AND variable_name=? COLLATE NOCASE",
            (release, item['documented_table'], column))]
        items.append(item)
    return items


def search(query, years=None, limit=25, kinds=None):
    """Tokenize user text rather than exposing FTS syntax. Search all document kinds."""
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_]{1,}", query)[:20]
    stop = {'what','data','have','does','about','which','there','with','from','the','and','for','information','tell','know','ipeds','yale','university','students'}
    words = [w for w in tokens if w.lower() not in stop] or tokens[:3]
    synonyms = {'faculty':'instructional staff', 'admissions':'applicants admissions',
                'graduate':'graduate enrollment', 'aid':'financial grant scholarship',
                'graduation':'graduation cohort completers', 'sat':'SATVR SATMT SAT'}
    terms = list(dict.fromkeys(words + [x for w in words for x in synonyms.get(w.lower(), '').split()]))
    if not terms:
        return []
    fts = ' OR '.join('"' + t + '"' for t in terms)
    params = [fts]
    condition = ''
    if years:
        releases = [annual_path(y).parent.name for y in years]
        condition = ' AND r.release_id IN (' + ','.join('?' for _ in releases) + ')'
        params.extend(releases)
    if kinds:
        allowed={'table_definition','variable_definition','code_value','release_note','supplementary_change','metadata_definition','introduction'}
        if not set(kinds)<=allowed:raise ValueError('Unknown codebook record type.')
        condition+=' AND r.kind IN ('+','.join('?' for _ in kinds)+')'
        params.extend(kinds)
    # Exact identifiers should lead to their definition, not a document mentioning them.
    identifier=query.strip().upper()
    params.extend([identifier,identifier,identifier,min(max(int(limit), 1), 100)])
    with readonly(DATA / 'metadata_catalog.sqlite') as db:
        rows = db.execute("""SELECT r.record_id,r.release_id,r.kind,r.table_name,r.variable_name,
            r.title,substr(r.body,1,2000) AS definition,f.path AS source_file,s.sheet_name,r.source_row
            FROM search_index JOIN records r ON r.record_id=search_index.record_id
            JOIN source_files f ON f.source_id=r.source_id LEFT JOIN sheets s ON s.sheet_id=r.sheet_id
            WHERE search_index MATCH ?""" + condition + """ ORDER BY
            CASE WHEN upper(r.variable_name)=? AND r.kind='variable_definition' THEN 0
                 WHEN upper(r.table_name)=? AND r.kind='table_definition' THEN 1
                 WHEN upper(r.table_name)=? THEN 2 ELSE 3 END,
            bm25(search_index),r.record_id LIMIT ?""", params).fetchall()
        output = []
        for row in rows:
            item = dict(row)
            item['issues'] = [dict(x) for x in db.execute(
                "SELECT issue_type,description,status FROM issues WHERE source_record_id=?", (row['record_id'],))]
            item['physical_column_present'] = bool(db.execute(
                "SELECT 1 FROM physical_columns WHERE release_id=? AND table_name=? AND column_name=?",
                (row['release_id'], row['table_name'], row['variable_name'])).fetchone()) if row['variable_name'] else None
            output.append(item)
        return output


def definition_detail(record_id):
    """Full readable definition and categories for a selected source record."""
    with readonly(DATA/'metadata_catalog.sqlite') as db:
        row=db.execute("""SELECT r.record_id,r.release_id,r.kind,r.table_name,r.variable_name,r.title,
            coalesce(nullif(v.long_description,''),r.body) AS definition,
            f.path AS source_file,s.sheet_name,r.source_row
            FROM records r LEFT JOIN variable_docs v USING(record_id)
            JOIN source_files f ON f.source_id=r.source_id LEFT JOIN sheets s ON s.sheet_id=r.sheet_id
            WHERE r.record_id=?""",(record_id,)).fetchone()
        if row is None:raise ValueError('This source record no longer exists. Search again.')
        item=dict(row)
        item['codes']=[dict(r) for r in db.execute(
            'SELECT code_value,value_label FROM code_values WHERE release_id=? AND table_name=? COLLATE NOCASE AND variable_name=? COLLATE NOCASE ORDER BY record_id',
            (row['release_id'],row['table_name'],row['variable_name']))] if row['kind']=='variable_definition' else []
        return item


def analytical_context(release, table, variable=None):
    """Explicit entry point for the next planning stage; does not expand query approval.

    Keep ordinary definition search lightweight. Planners/review tools can request
    the derived grain, periods, categories, missingness and change evidence here.
    """
    from analysis_catalog.catalog import field_context, table_context, field_history
    if not (DATA/'analysis_catalog.sqlite').exists():
        raise ValueError('Analytical catalog has not been built; run python -m analysis_catalog.build.')
    result=field_context(release,table,variable) if variable else table_context(release,table)
    if variable:result['cross_year_evidence']=field_history(release,table,variable)
    return result


# ── Single-institution shortcuts ──────────────────────────────────────────────
# THE one place to add a school nickname. Map a lowercase nickname to a
# (value, kind) pair, where kind is one of:
#   • 'confirm' — value is an int UNITID for ONE unambiguous institution. It
#     resolves automatically (no dropdown) and is honored on the direct, execution
#     and offline paths. Use only when the bare nickname can mean nothing else.
#   • 'alias'   — value is an int UNITID, but the bare word is ambiguous or common
#     (e.g. "Columbia", "Penn"). It is honored on the execution and offline paths,
#     where the surrounding question disambiguates, but a bare mention still asks
#     the user to confirm an exact UNITID (it does NOT auto-resolve).
#   • 'search'  — value is a str phrase for a colloquial form that only seeds the
#     disambiguation dropdown; the user always confirms an exact UNITID.
# For multi-school groups (Ivy League, Seven Sisters, …) use GROUPS below instead.
INSTITUTION_SHORTCUTS = {
    'yale':(130794,'confirm'),'harvard':(166027,'confirm'),'princeton':(186131,'confirm'),
    'dartmouth':(182670,'confirm'),'upenn':(215062,'confirm'),
    'mit':(166683,'confirm'),'ucla':(110662,'confirm'),
    'brown':(217156,'alias'),'columbia':(190150,'alias'),'penn':(215062,'alias'),
    'university of pennsylvania':(215062,'alias'),'cornell':(190415,'alias'),
    'umich':('university of michigan','search'),'uw madison':('university of wisconsin madison','search'),
    'uconn':('university of connecticut','search'),'umass':('university of massachusetts','search'),
    'cal':('university of california berkeley','search'),'berkeley':('university of california berkeley','search'),
    'ut austin':('university of texas austin','search'),'georgia tech':('georgia institute of technology','search'),
    'virginia tech':('virginia polytechnic institute','search'),'ole miss':('university of mississippi','search'),
    'penn state':('pennsylvania state university','search'),
}
# Derived views — do not edit directly; add entries to INSTITUTION_SHORTCUTS above.
# SAFE_ALIASES: nicknames that auto-resolve on the direct path (resolve()).
# ALIASES:      nicknames honored on the execution/offline paths (auto-resolve + alias).
# NICKNAME_SEARCH: colloquial forms that only expand the disambiguation dropdown.
SAFE_ALIASES = {k:v for k,(v,kind) in INSTITUTION_SHORTCUTS.items() if kind=='confirm'}
ALIASES = {k:v for k,(v,kind) in INSTITUTION_SHORTCUTS.items() if kind in ('confirm','alias')}
NICKNAME_SEARCH = {k:v for k,(v,kind) in INSTITUTION_SHORTCUTS.items() if kind=='search'}
IVY = [130794,166027,186131,217156,190150,215062,182670,190415]
# Barnard, Bryn Mawr, Mount Holyoke, Smith, Vassar, Wellesley (Radcliffe merged into Harvard).
SEVEN_SISTERS = [189097,211273,166939,167835,197133,168218]
# The eight Ivies plus MIT, Stanford, Johns Hopkins, University of Chicago.
IVY_PLUS = IVY + [166683,243744,162928,144050]

# Named institution groups — the single place common higher-ed terms live. Add an entry
# here (a canonical label, the member UNITIDs, and a word-boundary match pattern) and every
# resolver that calls group_ids/group_label expands it; no other file needs editing.
GROUPS = {
    'Ivy League':    {'ids': IVY,           'match': r'\bivy\s+league\b|\bivies\b'},
    'Ivy Plus':      {'ids': IVY_PLUS,      'match': r'\bivy\s*\+|\bivy[\s-]+plus\b'},
    'Seven Sisters': {'ids': SEVEN_SISTERS, 'match': r'\bseven\s+sisters?\b'},
}


def group_label(text):
    """Canonical group name if the text names a known institution group, else None.
    A bare 'ivy' maps to the Ivy League, but a mere 'ivy' substring (e.g. Ivy Tech) does not."""
    t = str(text).casefold().strip()
    if t == 'ivy':
        return 'Ivy League'
    for name, g in GROUPS.items():
        if re.search(g['match'], t):
            return name
    return None


def group_ids(text):
    """Member UNITIDs if the text names a known institution group, else None."""
    name = group_label(text)
    return list(GROUPS[name]['ids']) if name else None


def institutions(names, year):
    ids = []
    with readonly(annual_path(year)) as db:
        for name in names:
            text = str(name).strip().lower()
            from .institution_confirmation import resolve,annotated_id
            if annotated_id(str(name)) is not None:
                confirmed=resolve(str(name),{})
                if confirmed is not None:text=str(confirmed)
            group = group_ids(text)
            if group is not None:
                ids.extend(group)
                continue
            if text in ALIASES:
                ids.append(ALIASES[text])
                continue
            if text.isdigit():
                rows = db.execute(f'SELECT UNITID,INSTNM FROM HD{year} WHERE UNITID=?', (int(text),)).fetchall()
            else:
                rows = db.execute(f'SELECT UNITID,INSTNM FROM HD{year} WHERE INSTNM=? COLLATE NOCASE', (name,)).fetchall()
                if not rows:
                    escaped = text.replace('\\','\\\\').replace('%',r'\%').replace('_',r'\_')
                    rows = db.execute(f"SELECT UNITID,INSTNM FROM HD{year} WHERE INSTNM LIKE ? ESCAPE '\\' LIMIT 12", ('%'+escaped+'%',)).fetchall()
            if len(rows) != 1:
                choices = ', '.join(f"{r['INSTNM']} ({r['UNITID']})" for r in rows)
                raise ValueError(f"Institution '{name}' needs clarification. " + (f"Candidates: {choices}" if choices else 'No matching institution in this year.'))
            ids.append(rows[0]['UNITID'])
    if not ids or len(set(ids)) > 30:
        raise ValueError('Select between 1 and 30 institutions for this prototype.')
    from .institution_confirmation import AUTHORIZED
    authorized=AUTHORIZED.get()
    if authorized is not None and not set(ids)<=authorized:
        raise ValueError('Institution needs clarification. Please confirm the institution name or UNITID before analysis; a model-selected campus is not confirmation.')
    return list(dict.fromkeys(ids))
