"""Versioned, source-evidenced quantity units, shared by execution and preparation.

No network/model calls. Population text may establish what a count counts, but
cannot turn hours, scores, ratios, identifiers or codes into population counts.
"""
import re
import hashlib,json,sqlite3
from pathlib import Path
from functools import lru_cache

VERSION=3
CATALOG=Path(__file__).resolve().parents[1]/'data/unit_catalog.sqlite'


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
    source=Path(__file__).resolve().parents[1]/'data/metadata_catalog.sqlite'
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
