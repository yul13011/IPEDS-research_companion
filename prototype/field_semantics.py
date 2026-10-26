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
    from .unit_metadata import resolve
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
