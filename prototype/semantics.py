"""Source-grounded field descriptions and calculation proofs, independent of IDs.

These are conservative text parsers, not an assertion that arbitrary natural
language has been understood. Unrecognized/ambiguous meanings remain unknown.
No model-provided label or interpretation is accepted as calculation evidence.
"""
from copy import deepcopy
import re

VERSION=3
AXES={
    'gender':{'another gender':r'\banother gender\b','gender unknown':r'\bgender unknown\b',
              'women':r'\bwomen\b|\bfemales?\b','men':r'\bmen\b|\bmales?\b'},
    'race':{'American Indian or Alaska Native':r'\bamerican indian(?: or alaska native)?\b',
            'Native Hawaiian or Other Pacific Islander':r'\bnative hawaiian(?: or other pacific islander)?\b',
            'Asian':r'\basian\b','Black':r'\bblack(?: or african american)?\b',
            'Hispanic':r'\bhispanic(?: or latino)?\b','White':r'\bwhite\b',
            'Two or more races':r'\btwo or more races\b','Unknown':r'\brace[/ ]ethnicity unknown\b',
            'Nonresident':r'\b(?:u\.?s\.? )?nonresidents?\b|\bnonresident aliens?\b'},
    'attendance':{'full-time':r'\bfull[ -]time\b','part-time':r'\bpart[ -]time\b'},
    'medium':{'physical':r'\bphysical\b','electronic':r'\b(?:digital[/ -])?electronic\b|\bdigital\b'},
    'liquidity':{'current':r'\bcurrent\b','noncurrent':r'\bnoncurrent\b'},
}


def words(text):
    return ' '.join(re.findall(r'[a-z0-9]+',text.casefold()))


def count_unit(population):
    if re.search(r'\b(?:awards?|degrees?)\b.{0,30}\b(?:conferred|awarded)\b|\bcompletions\b|\b(?:number of|total) awards\b',population,re.I):return 'awards'
    if re.search(r'\b(employees|staff)\b',population,re.I):return 'employees'
    if re.search(r'\b(students?|enrollment|admissions|cohort)\b',population,re.I):return 'students'
    return 'unknown'


def _describe_field_legacy(d,table):
    """Expose both established facts and unresolved meaning, with source references."""
    title=d['title'];description=d['long_description'];lower=title.casefold()
    # Parenthetical lists enumerate included items, not additional dimensions.
    core=re.sub(r'\([^)]*\)','',lower)
    dimensions={};spans=[]
    for axis,values in AXES.items():
        matches=[(name,m) for name,pattern in values.items() for m in re.finditer(pattern,core)]
        if matches:
            names=list(dict.fromkeys(name for name,_ in matches))
            dimensions[axis]=names[0] if len(names)==1 else 'all' if 'total' in core else 'ambiguous'
            spans.extend((m.start(),m.end()) for _,m in matches)
    chars=list(core)
    for start,end in spans:chars[start:end]=' '*(end-start)
    base=words(''.join(chars))
    base=' '.join(w for w in base.split() if w not in {'grand','total','number','of','the','all'})
    population=' '.join(t.get('description','') for t in table.get('population_evidence',[]))
    kind='continuous' if d.get('format')=='Cont' and d.get('data_type')=='N' else 'coded_or_other'
    nonadditive=bool(re.search(r'\b(average|mean|median|percent|percentage|rate|ratio|per student|per employee|per fte)\b',lower))
    if re.search(r'percent|percentage',lower):unit='percent'
    elif re.search(r'\b(fte|full.time equivalent)',lower):unit='FTE'
    elif re.search(r'\b(dollars?|expenditures?|expenses?|revenues?|assets?|liabilities|salaries|salary|wages?|tuition|fees)\b',lower) or re.search(r'\bamount\b',lower) and re.search(r'\b(grants?|loans?|aid|scholarships?)\b',lower):unit='monetary amount'
    elif re.search(r'\b(collections?|books?|media|circulations?|databases?|serials)\b',lower):unit='items' if 'circulation' not in lower else 'transactions'
    elif kind=='continuous' and (dimensions or re.search(r'\b(number|count|headcount|completers|exclusions)\b',lower)):
        unit=count_unit(population)
    elif kind=='continuous' and 'total' in lower and (not base or re.search(r'\b(applicants?|admissions?|enrolled|students?|graduates?|degrees?|awards?|employees|staff)\b',lower)):
        unit=count_unit(population)
    else:unit='unknown'
    unit_basis=None
    # Some wide count tables label columns only by rank ("Professors"),
    # while the table definition explicitly establishes the count unit.
    # Require both pieces of source evidence; a model-authored label or a
    # rank name in a mixed salary table cannot establish employee counts.
    rank_title=re.fullmatch(r'(?:all ranks|no academic rank|(?:(?:associate|assistant) )?professors?|instructors?|lecturers?)',lower.strip())
    count_statement=re.search(r'each record contains counts of staff by academic rank',population,re.I)
    if unit=='unknown' and kind=='continuous' and not nonadditive and rank_title and count_statement:
        unit='employees';unit_basis=count_statement.group(0)
    # Multi-purpose tables can mention a student/staff ratio alongside retention.
    # A field's own explicit student/cohort wording outranks that table-wide hint.
    if kind=='continuous' and not nonadditive and unit not in {'monetary amount','FTE'} and re.search(r'\b(students?|undergraduates?|cohort|applicants?|completers)\b',lower):
        unit='students'
    if kind=='continuous' and unit not in {'monetary amount','FTE','percent'} and re.match(r'\s*(?:the )?(?:number|count)\b',description,re.I):
        first=description.split('.')[0]
        unit='employees' if re.search(r'\b(staff|employees|professors|faculty)\b',first,re.I) else 'students' if re.search(r'\bstudents?\b',first,re.I) else 'awards' if re.search(r'\b(awards?|degrees?)\b',first,re.I) else unit
    periods=[e.get('year_coverage') for e in table.get('period_evidence',[]) if e.get('year_coverage')]
    # Title-specific dates/balance positions must agree; incidental historical
    # prose in long descriptions is not treated as the observation period.
    time_qualifiers=re.findall(r'\b(?:19|20)\d{2}(?:[-–/]\d{2,4})?\b|\bbeginning\b|\bending\b|\bprior year\b|\bprevious year\b',lower)
    return {'version':VERSION,'record_id':d['record_id'],'release_id':d['release_id'],'table':d['table_name'],
        'variable':d['variable_name'],'source_title':title,'measure_base':base,'dimensions':dimensions,
        'unit':unit,'numeric_kind':kind,'additive':kind=='continuous' and not nonadditive and unit not in {'unknown','percent','FTE'},
        'total_scope':bool(re.search(r'\b(total|all)\b',core)),
        'reporting_periods':periods,'field_time_qualifiers':time_qualifiers,
        'population_evidence':[{'record_id':e['record_id'],'description':e.get('description','')[:600]} for e in table.get('population_evidence',[])],
        'required_row_selectors':[k for k in table.get('profile',{}).get('candidate_key',[]) if k.upper()!='UNITID'],
        'missing_policy':'Propagate missing/zero denominators; no zero substitution or inferred imputation status.',
        'category_overlap_warning':bool(re.search(r'allocated|allocation|not mutually exclusive',description,re.I)),
        'evidence':{'variable_record_id':d['record_id'],'table_record_ids':[e['record_id'] for e in table.get('population_evidence',[])],
                    'title_excerpt':title,'definition_excerpt':description[:400],'unit_basis_excerpt':unit_basis},
        'readiness':'described' if unit!='unknown' else 'partial_unit_unknown','execution_approved':False}


def describe_field(d,table):
    """Retain population/dimension proofs; obtain units from the shared catalog."""
    item=_describe_field_legacy(d,table)
    assignment=resolve(d,table)
    item['unit']=assignment['unit'];item['unit_metadata']=assignment
    if assignment['quantity_type'] in {'category','identifier','coordinate'}:
        item['numeric_kind']='coded_or_other'
    nonadditive=bool(re.search(r'\b(average|mean|median|percent|percentage|rate|ratio|per student|per employee|per fte)\b',d['title'],re.I))
    item['additive']=item['numeric_kind']=='continuous' and not nonadditive and assignment['status']=='verified' and assignment['quantity_type'] in {'count','currency','duration'}
    item['readiness']='described' if assignment['status']=='verified' else 'partial_unit_unknown'
    item['evidence']['unit_basis_excerpt']=assignment['evidence'][0]['excerpt']
    return item


def formula_text(calc,definitions):
    names=[definitions[rid]['variable_name'] for rid in calc['input_record_ids']]
    if calc['operator'] in {'percent','ratio'}:
        den=definitions[calc['denominator_record_id']]['variable_name']
        return ('100 × ' if calc['operator']=='percent' else '')+names[0]+' / '+den+' for the same selected source row.'
    return (' + ' if calc['operator']=='sum' else ' − ').join(names)+' for the same selected source row.'


def compatible(a,b):
    if a['release_id']!=b['release_id'] or a['table'].casefold()!=b['table'].casefold():
        return False,'Different source tables or releases require an explicit population/period alignment; no implicit join is allowed.'
    if a['unit']=='unknown' or a['unit']!=b['unit']:return False,'The source units are unknown or incompatible.'
    am=a.get('unit_metadata',{});bm=b.get('unit_metadata',{})
    if a['unit']=='monetary amount' and (am.get('scale')!=bm.get('scale') or am.get('currency') and bm.get('currency') and am['currency']!=bm['currency']):
        return False,'Currency or reporting scales differ; no implicit conversion is allowed.'
    if not a['additive'] or not b['additive']:return False,'Averages, rates, FTEs and other non-additive fields cannot be treated as category counts or amounts.'
    if a['reporting_periods']!=b['reporting_periods'] or a['field_time_qualifiers']!=b['field_time_qualifiers']:
        return False,'The fields have different or unresolved reporting periods.'
    if any(v=='ambiguous' for v in list(a['dimensions'].values())+list(b['dimensions'].values())):
        return False,'A source title contains unresolved overlapping categories.'
    return True,''


def subset(a,b,raw_a,raw_b):
    ok,reason=compatible(a,b)
    if not ok:return False,reason,None
    # Category containment requires the same measure after category words are
    # removed; "Applicants" and "Admissions" never become interchangeable.
    if a['measure_base']==b['measure_base']:
        strict=False
        for axis in set(a['dimensions'])|set(b['dimensions']):
            av=a['dimensions'].get(axis,'all' if a['total_scope'] else None)
            bv=b['dimensions'].get(axis,'all' if b['total_scope'] else None)
            if av==bv and av is not None:continue
            if av not in {None,'all'} and bv=='all':strict=True;continue
            return False,'The numerator and denominator category scopes do not establish containment.',None
        if strict:return True,'Source category is contained in the corresponding source total.',{'kind':'category_containment','axes':list(a['dimensions'])}
    # Explicit source decomposition is a second, independent proof: the total's
    # own definition says it is a sum and names this exact component. Neither a
    # model assertion nor a conveniently small numerical value is a proof.
    component=words(re.sub(r'\([^)]*\)','',raw_a['title']))
    component=' '.join(w for w in component.split() if w not in {'the','of'})
    total_text=words(raw_b['long_description']);total_text=' '.join(w for w in total_text.split() if w not in {'the','of'})
    if len(component.split())>=3 and re.search(r'\bsum of\b',raw_b['long_description'],re.I) and re.search(r'\b'+re.escape(component)+r'\b',total_text):
        return True,'The denominator definition explicitly names the numerator as a component of its sum.',{'kind':'explicit_source_decomposition','excerpt':raw_b['long_description'][:600]}
    return False,'The codebook evidence does not yet establish that this numerator belongs to this denominator.',None


def disjoint(a,b):
    ok,_=compatible(a,b)
    if not ok or a['measure_base']!=b['measure_base']:return False
    if a['category_overlap_warning'] or b['category_overlap_warning']:return False
    differing=[axis for axis in set(a['dimensions'])|set(b['dimensions']) if a['dimensions'].get(axis)!=b['dimensions'].get(axis)]
    if len(differing)!=1:return False
    axis=differing[0];av=a['dimensions'].get(axis);bv=b['dimensions'].get(axis)
    # Unknown/another gender can be allocated into Men/Women source counts.
    if axis=='gender' and {av,bv}-{'men','women'}:return False
    return av is not None and bv is not None and av not in {'all','ambiguous'} and bv not in {'all','ambiguous'}


def validate_calculation(calc,definitions,descriptors):
    ids=calc['input_record_ids'];den_id=calc['denominator_record_id'];op=calc['operator']
    result={'label':calc['label'],'operator':op,'approved':False,'input_record_ids':ids,'denominator_record_id':den_id,'evidence_record_ids':ids+([den_id] if den_id else [])}
    def reject(reason):return {**result,'reason':reason}
    if len(ids)!=len(set(ids)):return reject('Duplicate inputs would double-count an observation.')
    if calc['group_by_record_ids']:return reject('Grouped arithmetic needs a separate reporting-unit and subtotal policy.')
    fields=[descriptors[i] for i in ids]
    if any(f['numeric_kind']!='continuous' for f in fields):return reject('Arithmetic inputs must be documented continuous numerical observations.')
    if op in {'percent','ratio'}:
        if len(ids)!=1 or den_id is None:return reject('Each ratio/percentage requires exactly one numerator and one denominator.')
        den=descriptors[den_id]
        ok,reason,proof=subset(fields[0],den,definitions[ids[0]],definitions[den_id])
        if not ok:
            # A requested ratio of sibling categories is valid but is not a
            # percentage share and is not constrained to 0–1.
            if op=='ratio' and disjoint(fields[0],den):proof={'kind':'sibling_category_ratio'}
            else:return reject(reason)
        return {**result,'approved':True,'reason':'Source population, row selection, period, units and relationship agree.',
                'proof':proof,'unit':'percent' if op=='percent' else 'ratio','bounded_share':proof['kind']!='sibling_category_ratio'}
    if op=='sum':
        if len(ids)<2:return reject('A sum needs at least two non-overlapping components.')
        if not all(disjoint(a,b) for i,a in enumerate(fields) for b in fields[i+1:]):return reject('The inputs are not proven disjoint categories of the same source measure; totals/subtotals may overlap.')
        return {**result,'approved':True,'reason':'Source categories are disjoint and have compatible units and scope.','proof':{'kind':'disjoint_category_sum'},'unit':fields[0]['unit']}
    if op=='difference':
        if len(ids)!=2:return reject('A difference requires an ordered pair of observations.')
        ok,reason=compatible(*fields)
        if not ok:return reject(reason)
        contained=subset(fields[1],fields[0],definitions[ids[1]],definitions[ids[0]])[0]
        if not contained and not disjoint(*fields):return reject('The difference lacks a compatible source category or total/component relationship.')
        return {**result,'approved':True,'reason':'Compatible source category comparison.','proof':{'kind':'total_minus_component' if contained else 'category_difference'},'unit':fields[0]['unit']}
    return reject('This operation needs additional evidence about weighting or row-count meaning; no default was inferred.')


def normalize_plan(plan,question,definitions):
    """Repair representation mistakes without changing the requested scope."""
    p=deepcopy(plan);notes=[]
    fixed={f['record_id'] for f in p['filters'] if f['operator']=='eq' and len(f['values'])==1}
    for s in p['selections']:
        if s['role']=='dimension' and s['record_id'] in fixed:
            s['role']='identifier';notes.append('An equality-filtered dimension is constant; retained as a selector rather than a grouped output.')
    p['group_by_record_ids']=[rid for rid in p['group_by_record_ids'] if rid not in fixed]
    calculations=[]
    for c in p['calculations']:
        split=(c['operator']=='percent' and len(c['input_record_ids'])>1 and re.search(r'break\s*down|breakdown|\beach\b|\bby (gender|sex|race|ethnicity)',question,re.I)
               and not re.search(r'combined|together|\bsum\b|\bboth\b',question,re.I))
        if split:
            for rid in c['input_record_ids']:
                calculations.append({**c,'input_record_ids':[rid],'label':definitions[rid]['title']+' as percent of '+definitions[c['denominator_record_id']]['title'],
                    'interpretation':'100 × '+definitions[rid]['variable_name']+' / '+definitions[c['denominator_record_id']]['variable_name']+' on the same selected population row.'})
            notes.append('Split the category-share request into one numerator per output; no categories or denominator changed.')
        else:calculations.append(c)
    unique=[];seen=set()
    for c in calculations:
        signature=(c['operator'],tuple(c['input_record_ids']),c['denominator_record_id'],tuple(c['group_by_record_ids']))
        if signature in seen:
            notes.append('Collapsed duplicate outputs with the identical source calculation.');continue
        seen.add(signature);unique.append(c)
    p['calculations']=unique
    return p,notes


# ===== merged from units.py (consolidation) =====
"""Source-backed display units. Never rescale values or change analytical units."""
from copy import deepcopy
import re

MONEY={'monetary amount','dollars','USD','USD (thousands)','USD (millions)'}
UNVERIFIED='Currency/scale unverified'
# Reviewed IPEDS reporting conventions, applied only to documented monetary
# fields in these source families. A model-authored label is never evidence.
RULES=[
    (r'SAL\d{4}_(?:IS|NIS)', 'https://nces.ed.gov/ipeds/use-the-data/download-survey-material/2024/human%20resources/package_1_44.pdf'),
    (r'F\d{4}_F[123]A?', 'https://nces.ed.gov/ipeds/use-the-data/download-survey-material/2023/finance/package_5_12.pdf'),
    (r'COST[12]_\d{4}', 'https://nces.ed.gov/ipeds/use-the-data/download-survey-material/2024/cost%20i/package_11_73.pdf'),
    (r'IC\d{4}_AY', 'https://ceds.ed.gov/connectReport.aspx?uid=31034'),
    (r'SFA\d{4}(?:_P[12])?', 'https://nces.ed.gov/ipeds/use-the-data/download-survey-material/2024/student%20financial%20aid/package_7_20.pdf'),
]


def is_currency(unit):
    return unit in {'dollars','USD','USD (thousands)','USD (millions)'}


def currency_text(value,unit,decimals=2):
    text=f'{value:,.{decimals}f}'
    if decimals:text=text.rstrip('0').rstrip('.')
    return '$'+text+({'USD (thousands)':' thousand','USD (millions)':' million'}.get(unit,''))


def unit_title(unit):
    return {'USD':'US dollars (USD)','dollars':'US dollars (USD)',
            'USD (thousands)':'Thousands of US dollars (USD)',
            'USD (millions)':'Millions of US dollars (USD)',
            'monetary amount':UNVERIFIED}.get(unit,unit)


def monetary_evidence(row,result):
    """Resolve actual executed source evidence, including legacy saved results."""
    if row.get('unit') not in MONEY:return None
    docs=[(s,d) for s in result.get('sources',[]) if s.get('metric')==row['metric']
          and s.get('year')==row.get('observation_year')
          and (row.get('unitid') is None or s.get('unitid') in {None,row['unitid']})
          for d in s.get('codebook_evidence',[])]
    candidates=[];conflict=False
    def currency_ids(meta):
        ids={meta['record_id']} if meta.get('quantity_type')=='currency' and meta.get('status')=='verified' and meta.get('record_id') else set()
        for item in meta.get('inputs',[]):ids.update(currency_ids(item))
        return ids
    proven_ids=currency_ids(row.get('unit_metadata',{}))
    for source,doc in docs:
        title=doc.get('title','');text=title+' '+doc.get('long_description','')
        if doc.get('record_id') not in proven_ids and not re.search(r'\b(salary|salaries|wages|tuition|fees?|expenses?|expenditures?|revenues?|assets?|liabilities|amount|dollars?)\b',title,re.I):continue
        # Percentages and ratios in a financial table are not currency evidence.
        if re.search(r'percent|percentage|ratio',title,re.I):continue
        million=bool(re.search(r'\bin millions?\b|\bmillions?(?: of)? (?:U\.?S\.? )?dollars\b|\bUSD\s*\(millions?\)',text,re.I))
        thousand=bool(re.search(r'\bin thousands?\b|\bthousands?(?: of)? (?:U\.?S\.? )?dollars\b|\$\s*0{3}\b|\bUSD\s*\(thousands?\)',text,re.I))
        scale=1000000 if million else 1000 if thousand else 1
        if million and thousand:conflict=True
        explicit=bool(re.search(r'\b(?:U\.?S\.? dollars|USD|dollars?)\b|\$',text,re.I))
        # Foreign currencies must not inherit a US reporting convention.
        if re.search(r'\b(?:Canadian|Australian|euros?|pounds sterling|CAD|AUD|EUR)\b',text,re.I):
            conflict=True;continue
        policy=next((url for pattern,url in RULES if re.fullmatch(pattern,source.get('table',''),re.I)),None)
        if explicit or policy:
            candidate={'currency':'USD','scale':scale,'record_id':doc.get('record_id'),
                               'table':source.get('table'),'variable':doc.get('variable_name'),
                               'basis':'Field dollar definition' if explicit else 'Reviewed IPEDS reporting convention',
                               'reference':policy,'source_title':title}
            if candidate not in candidates:candidates.append(candidate)
    pairs={(e['currency'],e['scale']) for e in candidates}
    if len(pairs)==1 and not conflict:
        currency,scale=next(iter(pairs))
        return {'unit':{1:'USD',1000:'USD (thousands)',1000000:'USD (millions)'}[scale],
                'currency':currency,'scale':scale,'evidence':candidates}
    # Reviewed measure mappings already carry an explicit dollar unit.
    if not docs and not conflict and row['unit']=='dollars':
        return {'unit':'USD','currency':'USD','scale':1,'evidence':[{'basis':'Existing reviewed dollar unit'}]}
    return {'unit':UNVERIFIED,'currency':None,'scale':None,'evidence':candidates}


def display_result(result):
    """A presentation copy: originals, calculations and saved results stay intact."""
    out={**result,'rows':[],'display_units':[]}
    for row in result['rows']:
        r=dict(row)
        if r.get('result_type') in {'categorical','text','identifier','bounded'}:
            out['rows'].append(r);continue
        # Idempotent for a presentation copy passed through several renderers.
        if 'source_unit' in r:
            out['rows'].append(r);continue
        assignment=restore_direct(r,result)
        if assignment:
            r['unit_metadata']=assignment
            if r['unit']!=assignment['unit']:
                r['source_unit']=r['unit'];r['unit']=assignment['unit']
                out['display_units'].append({'metric':r['metric'],'year':r.get('observation_year'),'unit':r['unit'],
                    'basis':'Source-verified unit migration; values unchanged','unit_metadata':assignment})
        row_assignment=resolve_row(r)
        if row_assignment:
            r['source_unit']=r.get('source_unit',r['unit']);r['unit']=row_assignment['unit'];r['unit_metadata']=row_assignment
            out['display_units'].append({'metric':r['metric'],'year':r.get('observation_year'),'unit':r['unit'],'unit_metadata':row_assignment})
        info=monetary_evidence(r,result)
        if info:
            r.update(source_unit=r.get('source_unit',r['unit']),unit=info['unit'],currency=info['currency'],currency_scale=info['scale'])
            entry={'metric':r['metric'],'year':r.get('observation_year'),**info}
            if entry not in out['display_units']:out['display_units'].append(entry)
        out['rows'].append(r)
    if result.get('display_units'):out['display_units']=deepcopy(result['display_units'])
    return out


# ===== merged from unit_metadata.py (consolidation) =====
"""Versioned, source-evidenced quantity units, shared by execution and preparation.

No network/model calls. Population text may establish what a count counts, but
cannot turn hours, scores, ratios, identifiers or codes into population counts.
"""
import re
import hashlib,json,sqlite3
from pathlib import Path
from functools import lru_cache

from .catalog import DATA
CATALOG=DATA/'unit_catalog.sqlite'


@lru_cache(maxsize=8192)
def _source_section(record_id,stamp):
    source=CATALOG.parent/'metadata_catalog.sqlite'
    with sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True) as db:
        row=db.execute('SELECT r.release_id,r.table_name,r.variable_name,r.body,v.title,v.long_description FROM records r JOIN variable_docs v USING(record_id) WHERE record_id=?',(record_id,)).fetchone()
    if not row:return None
    match=re.search(r'^sectiontitle:\s*(.+)$',row[3],re.M|re.I)
    return {'release_id':row[0],'table_name':row[1],'variable_name':row[2],'record_id':record_id,'excerpt':match[0],
            'title':row[4],'definition_sha256':hashlib.sha256(row[5].encode()).hexdigest()} if match else None


def source_section(d):
    if not d.get('record_id') or not re.fullmatch(r'F\d{4}_F[123]A?',d.get('table_name',''),re.I):return None
    source=CATALOG.parent/'metadata_catalog.sqlite'
    section=_source_section(d['record_id'],source.stat().st_mtime_ns)
    return section if section and all(section[k]==d.get(k) for k in ['release_id','table_name','variable_name','title']) and section['definition_sha256']==hashlib.sha256(d.get('long_description','').encode()).hexdigest() else None


def fingerprint(d,table):
    return hashlib.sha256(json.dumps({'field':{k:d.get(k) for k in ['record_id','release_id','table_name','variable_name','title','long_description','format','data_type','category_count']},
        'population':(table or {}).get('population_evidence',[]),'source_section':source_section(d),'version':VERSION},sort_keys=True,default=str).encode()).hexdigest()


@lru_cache(maxsize=4096)
def prepared_record(record_id,stamp):
    with sqlite3.connect(CATALOG.resolve().as_uri()+'?mode=ro',uri=True) as db:
        row=db.execute('SELECT fingerprint,assignment FROM units WHERE record_id=?',(record_id,)).fetchone()
        return (row[0],json.loads(row[1])) if row else None


@lru_cache(maxsize=4096)
def record_assignment(record_id,stamp):
    """Re-read original metadata for legacy direct results; never query values."""
    from analysis_catalog.catalog import connection,table_context
    with connection() as db:
        row=db.execute('SELECT d.*,v.title,v.long_description,v.format,v.data_type FROM definitions d JOIN source.variable_docs v USING(record_id) WHERE d.record_id=?',(record_id,)).fetchone()
    if row is None:return None
    d=dict(row)
    return resolve(d,table_context(d['release_id'],d['table_name']))


def restore_direct(row,result):
    """Presentation-only migration; the original row and audit stay intact."""
    existing=row.get('unit_metadata')
    def changed_inputs(meta):
        for item in meta.get('inputs',[]):
            if item.get('record_id') and item.get('version',0)<VERSION:
                source=CATALOG.parent/'metadata_catalog.sqlite'
                current=record_assignment(item['record_id'],source.stat().st_mtime_ns)
                if current and (current['unit']!=item.get('unit') or current['status']!='verified'):return True
            if changed_inputs(item):return True
        return False
    if existing and not existing.get('record_id') and changed_inputs(existing):
        return {'version':VERSION,'unit':'unknown','status':'requires_revalidation','historical_unit':row.get('unit'),
                'basis':'A saved calculation input has changed unit evidence; rerun to revalidate. Values have not been recalculated.'}
    direct_ref=bool(re.fullmatch(r'f[A-Za-z0-9]+_\d+',row.get('metric','')))
    if existing and (existing.get('version',0)>=VERSION or existing.get('quantity_type')=='reviewed_measure' or
                     not existing.get('record_id') and not direct_ref and existing.get('status')!='unresolved'):
        return existing
    sources=[s for s in result.get('sources',[]) if s.get('metric')==row.get('metric') and s.get('year')==row.get('observation_year')]
    direct=[s for s in sources if s.get('formula')=='direct source observation']
    docs=[d for s in direct for d in s.get('codebook_evidence',[]) if d.get('variable_name')==row.get('metric','').split('::')[-1]]
    ref=re.fullmatch(r'f[A-Za-z0-9]+_(\d+)',row.get('metric',''))
    if ref:
        docs=[d for s in sources if isinstance(s.get('formula'),dict) and not s['formula'].get('expressions') and not s['formula'].get('aggregates')
              for d in s.get('codebook_evidence',[]) if d.get('record_id')==int(ref[1])]
    ids={d.get('record_id') for d in docs if d.get('record_id')}
    if len(ids)!=1:
        if any(isinstance(s.get('formula'),dict) and (s['formula'].get('expressions') or s['formula'].get('typed_calculation') or s['formula'].get('aggregates')) for s in sources):
            return {'version':VERSION,'unit':'unknown','status':'requires_revalidation','historical_unit':row.get('unit'),
                    'basis':'Saved calculation predates verified unit metadata; rerun to revalidate. Values have not been recalculated.'}
        return None
    source=DATA/'metadata_catalog.sqlite'
    assignment=record_assignment(next(iter(ids)),source.stat().st_mtime_ns)
    if assignment and all(d.get('variable_name')==assignment['variable'] for d in docs):return assignment
    return None


def resolve(d,table=None,reviewed_unit=None,_prepared=True):
    table=table or {}
    if _prepared and not reviewed_unit and d.get('record_id') and CATALOG.exists():
        hit=prepared_record(d['record_id'],CATALOG.stat().st_mtime_ns)
        if hit and hit[0]==fingerprint(d,table):return json.loads(json.dumps(hit[1]))
    title=d.get('title','');description=d.get('long_description',d.get('definition','')) or ''
    population=table.get('population_evidence',[])
    text=title+' '+description
    def found(pattern,value):
        m=re.search(pattern,value,re.I)
        return m.group(0) if m else None
    def result(unit,kind,basis,excerpt,status='verified'):
        assignment={'version':VERSION,'release_id':d.get('release_id'),'table':d.get('table_name'),
                'variable':d.get('variable_name'),'record_id':d.get('record_id'),
                'unit':unit,'quantity_type':kind,'status':status,'basis':basis,
                'evidence':[{'record_id':d.get('record_id'),'excerpt':excerpt}]+[
                    {'record_id':p.get('record_id'),'excerpt':p.get('description','')[:2200]} for p in population],
                'scale':None if kind=='currency' else 1,'currency':None,
                'population':None,'rule_version':VERSION}
        if kind=='currency':
            million=bool(found(r'\bin millions?\b|\bmillions? of (?:US |U\.S\. )?dollars\b',text))
            thousand=bool(found(r'\bin thousands?\b|\bthousands? of (?:US |U\.S\. )?dollars\b',text))
            assignment['scale']=1000000 if million else 1000 if thousand else 1
            assignment['scale_basis']='Explicit source magnitude' if million or thousand else 'Unscaled source amount; display checks reporting convention'
            assignment['currency']='CAD' if found(r'Canadian dollars|\bCAD\b',text) else 'AUD' if found(r'Australian dollars|\bAUD\b',text) else 'EUR' if found(r'\beuros?|EUR\b',text) else 'USD' if found(r'\b(?:USD|dollars?)\b|\$',text) else None
            assignment['currency_status']='explicit' if assignment['currency'] else 'requires reporting-convention verification'
            if million and thousand:assignment.update(unit='unknown',status='conflicting',basis='Conflicting source magnitudes')
        return assignment
    if reviewed_unit:
        return result(reviewed_unit,'reviewed_measure','Reviewed measure definition and formula',description or title)
    if found(r'\b(?:UNITID|institution (?:ID|identifier)|ID (?:number|of)|identification number|longitude|latitude)\b',title):
        if found(r'longitude|latitude',title):return result('degrees','coordinate','Explicit coordinate definition',text)
        return result('identifier','identifier','Identifier definition',title)
    if d.get('category_count',0) or (d.get('format') and d['format']!='Cont'):
        return result('coded','category','Source coded/non-continuous field',title)
    if found(r'programs offered|programs in a CIP code can be completed',title):
        return result('coded','category','Source program availability indicator',title)
    program=re.fullmatch(r'CIPLGTH([1-6])',d.get('variable_name',''),re.I)
    if program and found(r'\blength\b',title) and found(r'clock or credit|credit or clock',description):
        assignment=result('unknown','duration','Program length unit is selected by the same institution record',description,status='conditional')
        assignment['unit_selector']='PRGMSR'+program[1]
        return assignment
    if program and found(r'\blength\b',title):
        for basis in ['contact','clock','credit']:
            if found(r'(?:in terms of|measured in|program in) '+basis+r' hours',description):
                return result(basis+' hours','duration','Program definition explicitly establishes its hour basis',description)
    if found(r'length.*\bin weeks\b',title):
        return result('weeks','duration','Explicit source week duration',title)
    if found(r'\b(?:percent|percentage)\b',title):return result('percent','percentage','Explicit percentage quantity',title)
    if found(r'\b(?:SAT|ACT)\b',title) and found(r'\bscore\b',title):
        return result('score','score','Source test score definition',title)
    if found(r'\brate\b',title) and not found(r'\b(?:tuition|salary|wage|fees|cost)\b',title):
        if found(r'\b(?:percent|percentage)\b',description+' '+' '.join(p.get('description','') for p in population)):
            return result('percent','percentage','Source rate documentation establishes percentage basis',text)
        return result('unknown','unresolved','Rate scale not established',text[:1800],status='unresolved')
    monetary=found(r'\b(?:dollars?|expenditures?|expenses?|revenues?|assets?|liabilities|salaries|salary|wages?|tuition|fees|discounts|allowances|cost|fringe benefits)\b',title) or (found(r'\bamount\b',title) and found(r'\b(?:grants?|loans?|aid|scholarships?)\b',title))
    if monetary:return result('monetary amount','currency','Monetary source quantity; currency/scale checked separately',title)
    # Population words in a title do not determine the measured quantity.
    if found(r'\b(?:credit|clock|contact) hours?\b',title) and not found(r'\b(?:number|count) of (?:students|staff|employees)\b',title):
        units=[u for u in ['credit','clock','contact'] if found(r'\b'+u+r'\b',title)]
        unit=units[0]+' hours' if len(units)==1 else 'hours (source basis)'
        return result(unit,'duration','Explicit hour quantity and source basis',title)
    if found(r'\b(?:fte|full[ -]time equivalent)\b',title):return result('FTE','fte','Explicit FTE quantity',title)
    if found(r'\bratio\b',title):return result('ratio','ratio','Explicit source ratio',title)
    if found(r'\b(?:allocation factor)\b',title):return result('ratio','ratio','Explicit allocation factor',title)
    pop=' '.join(p.get('description','') for p in population)
    # Short rank labels use the table's explicit count declaration. The SISINST
    # identity and rank glossary establish the documented misspelling as well.
    rank=found(r'^(?:all ranks|no academic rank|(?:(?:associate|assistant) )?professors?|instructors?|lecturers?)$',title.strip())
    rank_typo=(d.get('variable_name')=='SISINST' and found(r'\bInstructor\b',description))
    if (rank or rank_typo) and found(r'each record contains counts of staff by academic rank',pop):
        return result('employees','count','Table explicitly declares staff counts by academic rank',text)
    if found(r'\b(?:collections?|books?|media|circulations?|databases?|serials)\b',title):
        return result('transactions' if found(r'circulation',title) else 'items','count','Documented library quantity',title)
    if found(r'\binterlibrary loans?\b',title):return result('transactions','count','Explicit library transaction quantity',title)
    if found(r'\b(?:number of )?branch(?:es)? (?:and independent )?libraries\b',title):return result('libraries','count','Explicit library location count',title)
    # Explicit count wording or population quantity labels, plus the documented
    # population, establishes counts. Hours/score/ratio cases were handled above.
    count=found(r'\b(?:number|count|headcount|total|enrollment|enrolled|cohort|completers|inclusions|exclusions|gender|students|undergraduates?|applicants|admissions|employees|staff|degrees|awards|men|women|male|female|asian|hispanic|black|white|nonresident)\b',title)
    count=count or found(r'^\s*(?:the )?(?:number|count)\b',description)
    if count:
        opening=re.split(r'(?<=[.!?])\s+',description,maxsplit=1)[0]
        own=title+' '+opening
        # Start with the field's own quantity, then its opening definition.
        # "Applicants" cannot become awards because degree-seeking students
        # happen to be described later in its definition.
        unit=None
        count_clause=found(r'\b(?:counts?|number|head\s?counts?)\s+(?:of\s+)?[^.;]{0,120}',pop) or ''
        for evidence in [title,opening,count_clause]:
            cleaned=re.sub(r"\b(?:bachelor.s )?(?:non[ -])?degree(?:/(?:non[ -])?certificate)?[ -]seeking\b",'',evidence,flags=re.I)
            subject=re.search(r'\b(?:employees|staff|professors|hires|students?|undergraduates?|enrollment|enrolled|applicants?|admissions?|cohort|completers|recipients?|men|women|awards?|degrees?)\b',cleaned,re.I)
            if subject:
                word=subject.group().lower()
                if word in {'men','women'}:
                    person=re.search(r'\b(students?|staff|employees|hires)\b',count_clause,re.I)
                    unit=('students' if person[1].lower().startswith('student') else 'employees') if person else None
                elif word in {'award','awards','degree','degrees'} and found(r'completed|receiving',cleaned[:subject.start()]):continue
                else:unit='employees' if word in {'employees','staff','professors','hires'} else 'awards' if word in {'award','awards','degree','degrees'} else 'students'
            if unit:break
        if unit:return result(unit,'count','Source quantity and documented population',own)
    # Read the field's own definition before declaring a short label unresolved.
    # These patterns describe the measured quantity, not incidental population
    # words elsewhere in a table. Earlier explicit score/hour/count rules win.
    head=description[:900]
    if found(r'\b(?:official|unique) (?:entity )?identifier\b',head):
        return result('identifier','identifier','Field definition explicitly identifies an identifier',head)
    if found(r'\b(?:unique numeric identifier|ID number of the Branch campus)\b',head):
        return result('identifier','identifier','Field definition explicitly identifies an identifier',head)
    if found(r'\bcohort\b',description) and found(r'\bstudents\b',' '.join(p.get('description','') for p in population)):
        return result('students','count','Cohort field and table explicitly describe students',text)
    if found(r'\bhousing capacity\b',title) and found(r'maximum number of students',description):
        return result('students','count','Definition specifies housing capacity in students',description)
    if found(r'number of meals per week',title):
        return result('meals per week','rate','Explicit meal-plan frequency',description)
    if found(r'\boutlays\b',title) and found(r'\bsalary outlays\b',pop):
        return result('monetary amount','currency','Field outlays linked to explicit table salary-outlay definition',text)
    finance=bool(re.fullmatch(r'F\d{4}_F[123]A?',d.get('table_name',''),re.I))
    finance_quantity=r'\b(?:revenues?|expenditures?|expenses?|assets?|liabilities|debt|income|appropriations|endowments?|book value|market value|equity|payments|salary|wages?|amounts?|funds|net position|deferred inflows|deferred outflows)\b'
    if finance and found(finance_quantity,head):
        return result('monetary amount','currency','Finance field definition establishes monetary quantity',head)
    section=source_section(d) if finance else None
    if section and found(r'\b(?:Expenses|Expenditures|Balance sheet|Scholarships|Endowment|Revenues|discounts|allowances|Student grants|Changes in net assets|Statement of financial)\b',section['excerpt']) and not found(r'\b(?:number|count|ratio|percent|percentage|fte|students|employees)\b',title):
        assignment=result('monetary amount','currency','Finance field belongs to an explicit monetary codebook section',head)
        assignment['evidence'].append(section)
        return assignment
    if found(r'^\s*(?:The )?(?:total )?expenditures?\b|amount of money|\b(?:application|housing|food|room|board) (?:fee|charge)s?\b',head):
        return result('monetary amount','currency','Field definition explicitly describes expenditure or charge',head)
    if found(r'\b(?:food and housing|room and board)\b',title) and found(r'Price of attendance|charges assessed|charges for an academic year',head):
        return result('monetary amount','currency','Attendance definition establishes housing/food charges',head)
    # Derived award tables document the exact originating count variable. A
    # degree name alone cannot decide between students and awards.
    if found(r'awarded|conferred',head) and found(r'\bCTOTALT\b',description) and found(r'\bcompletions survey\b',description):
        return result('awards','count','Derived definition names completions award count CTOTALT',description)
    return result('unknown','unresolved','No verified measurement unit established',text[:1800],status='unresolved')


# ===== merged from unit_observations.py (consolidation) =====
"""Resolve source-documented row-dependent units without changing values."""
from functools import lru_cache
import re


@lru_cache(maxsize=4096)
def _program_unit(record_id,unitid,metadata_stamp,data_stamp):
    from .catalog import DATA,readonly,annual_path
    with readonly(DATA/'metadata_catalog.sqlite') as db:
        d=db.execute('SELECT r.release_id,r.table_name,r.variable_name,v.long_description FROM records r JOIN variable_docs v USING(record_id) WHERE record_id=?',(record_id,)).fetchone()
        if not d:return None
        match=re.fullmatch(r'CIPLGTH([1-6])',d['variable_name'],re.I)
        if not match or not re.search(r'clock or credit|credit or clock',d['long_description'],re.I):return None
        selector='PRGMSR'+match[1];table=d['table_name'];year=int(d['release_id'][6:10])
        if not re.fullmatch(r'[A-Za-z0-9_]+',table):return None
        physical=db.execute('SELECT 1 FROM physical_columns WHERE release_id=? AND table_name=? AND column_name=? COLLATE NOCASE',(d['release_id'],table,selector)).fetchone()
        if not physical:return None
        codes=[dict(c) for c in db.execute('SELECT record_id,code_value,value_label FROM code_values WHERE release_id=? AND table_name=? AND variable_name=? COLLATE NOCASE',(d['release_id'],table,selector))]
    sql=f'SELECT "{selector}" FROM "{table}" WHERE UNITID=?'
    with readonly(annual_path(year)) as db:rows=db.execute(sql,[unitid]).fetchmany(2)
    if len(rows)!=1 or rows[0][0] is None:return None
    value=str(rows[0][0]);value=value.removesuffix('.0')
    code=next((c for c in codes if c['code_value']==value and c['value_label'].strip().lower() in {'clock hours','contact hours','credit hours'}),None)
    if not code:return None
    return {'unit':code['value_label'].lower(),'code_record_id':code['record_id'],'code_value':value,
            'selector':selector,'table':table,'source_release':d['release_id'],'unitid':unitid,'sql':sql,'parameters':[unitid]}


def resolve_row(row):
    meta=row.get('unit_metadata',{})
    if meta.get('status')!='conditional' or not meta.get('unit_selector') or row.get('unitid') is None:return None
    from .catalog import DATA,annual_path
    year=int(meta['release_id'][6:10]);path=annual_path(year)
    evidence=_program_unit(meta['record_id'],int(row['unitid']),(DATA/'metadata_catalog.sqlite').stat().st_mtime_ns,path.stat().st_mtime_ns)
    if not evidence:return None
    return {**meta,'unit':evidence['unit'],'status':'verified','basis':'Same-row program unit selector and supplied category definition',
            'unit_selector_evidence':evidence}
