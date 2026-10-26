"""A searchable, plain-language guide grounded in the loaded local codebooks.

Editorial explanations are paired with actual table documentation. Runtime checks
refresh in memory when sources change; writing the portable artifacts is explicit.
"""
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
import json,re
from .catalog import DATA,readonly,annual_path

GUIDE_PATH=DATA/'DATA_GUIDE.md'
INDEX_PATH=DATA/'data_guide_index.json'

# Each explanation is supported by the corresponding component's table titles
# and descriptions. Keywords are retrieval aids, not statistical definitions.
AREAS=[
 ('institutions','Institutions, programs and student services',['Institutional Characteristics'],
  'School locations and characteristics, educational offerings, affiliations, special learning opportunities and reported student services.',
  'schools colleges universities campuses location public private ownership programs offerings services childcare counseling distance online mission',
  ['Which Massachusetts colleges offer distance education?','Does Smith College report on-campus childcare?']),
 ('admissions','Admissions and entrance test scores',['Admissions','Admissions and Test Scores'],
  'Applicants, admitted students, entering enrollment, admission considerations, selectivity, admissions yield and reported entrance-test scores.',
  'applications applicants accepted acceptance admission admissions enrolled freshmen first year selectivity yield SAT ACT test scores percentiles median',
  ['Compare Ivy League admission rates in fall 2024.','Which years have SAT median scores?']),
 ('fall_enrollment','Fall enrollment and student backgrounds',['Fall Enrollment'],
  'Fall student counts by level, attendance status and student characteristics, including race/ethnicity, gender, distance education, residence and some age information. Related tables cover retention and student-to-faculty ratios.',
  'students student body enrollment enrolment undergraduates graduates graduate demographics diversity race ethnicity gender age full time part time retention ratio residence migration',
  ["Show Yale's graduate enrollment by race and ethnicity.",'Convert those student counts into percentages of the matching population.']),
 ('annual_enrollment','Enrollment across a full year',['12-month Enrollment'],
  'Twelve-month unduplicated student headcounts, distance education status, dual enrollment and instructional activity. Annual headcounts answer a different question from a fall snapshot.',
  'annual yearly twelve 12 month unduplicated students headcount instructional activity credit hours dual enrollment high school',
  ['How does annual enrollment differ from fall enrollment?','What annual enrollment information is available?']),
 ('completions','Degrees, certificates and fields of study',['Completions'],
  'Awards and degrees by program/field of study, award level and student characteristics; separate tables describe people receiving awards and programs offered. Awards and people are different counts.',
  'degrees certificates awards graduates completions programs majors subjects fields CIP diploma credentials',
  ['Show degrees awarded by field of study.','What does an award level mean?']),
 ('graduation','Graduation rates and defined entering cohorts',['Graduation Rates'],
  'Completion outcomes for specified entering cohorts and completion windows, including source-defined student groups and aid-recipient groups. The collection release and the year students entered are different dates.',
  'graduation graduate completion success finish six year 150 200 percent cohort entering Pell subsidized loan',
  ["Show Yale's six-year bachelor's graduation rate by entering cohort.",'Which entering-cohort years are available?']),
 ('outcomes','Longer-term undergraduate outcomes',['Outcome Measures'],
  'Award and enrollment outcomes at several follow-up points for defined undergraduate entering cohorts, including first-time/non-first-time and full-time/part-time groups.',
  'outcomes outcome measures follow up four six eight years transfer non first time enrolled awards cohort',
  ['What outcomes are recorded eight years after entry?','How do Outcome Measures populations differ from graduation-rate populations?']),
 ('costs','Tuition, fees and college costs',['Cost'],
  'Published tuition and required fees, application fees, food/housing and other student charges, cost-of-attendance estimates and source-defined net-price information. Different charges apply to different student groups.',
  'cost costs price tuition fees expensive affordable room board housing food living books attendance net price',
  ['Compare published tuition at two universities.','What is the difference between sticker price and net price?']),
 ('aid','Student financial assistance',['Student Financial Aid'],
  'Counts and amounts of grants, scholarships and loans from specified sources, including Pell grants and military/veterans benefits. First-time undergraduate and broader undergraduate populations must not be treated as interchangeable.',
  'aid financial assistance help paying grants scholarships loans Pell debt borrowing veterans military benefits funding',
  ['What financial aid information is available?','Explain which students are included in a reported grant measure.']),
 ('staff','Faculty, other employees and salaries',['Human Resources'],
  'Staff counts by occupation, instructional role, rank, faculty/tenure status and demographic categories, plus source-defined salary and contract-period measures.',
  'faculty professors instructors teachers staff employees employment workers workforce jobs hiring rank tenure salaries salary pay wages compensation',
  ['What information is available about faculty?','Compare a clearly defined instructional-staff salary measure.']),
 ('finance','Institution finances',['Finance'],
  'Institutional financial reporting uses different forms for public, private nonprofit and private for-profit institutions. Revenue, expenses and balance-sheet concepts must be interpreted within their source accounting definitions.',
  'finance finances financial revenues revenue expenses expenditures spending assets liabilities accounting budget endowment balance',
  ['What financial reporting information is available for institutions?','Explain the source definition before comparing an expense measure.']),
 ('libraries','Academic libraries',['Academic Libraries'],
  'Library characteristics, collections, expenditures, services and some staffing measures for applicable institutions. Coverage and reporting requirements change across releases.',
  'library libraries books collections electronic digital serials circulation services librarian staffing spending',
  ['What information is available about academic libraries?','Which source periods contain a particular library measure?'])]


def _signature():
    paths=[DATA/'metadata_catalog.sqlite',Path(__file__)]+sorted((DATA/'annual').glob('IPEDS_*/*.sqlite'))
    return tuple((str(p),p.stat().st_size,p.stat().st_mtime_ns) for p in paths if p.exists())


def get():return deepcopy(_build(_signature()))


@lru_cache(maxsize=2)
def _build(signature):
    from .coverage import inventory
    inv=inventory();tables=[]
    with readonly(DATA/'metadata_catalog.sqlite') as db:
        rows=[dict(r) for r in db.execute('''SELECT t.* FROM table_docs t WHERE EXISTS
            (SELECT 1 FROM physical_tables p WHERE p.release_id=t.release_id AND p.table_name=t.table_name COLLATE NOCASE)
            ORDER BY t.release_id,t.table_name''')]
    actual={}
    for year in inv['release_years']:
        with readonly(annual_path(year)) as db:
            actual[year]={r[0].casefold() for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for row in rows:
        year=int(row['release_id'][6:10])
        if row['table_name'].casefold() in actual.get(year,set()):tables.append(row)
    sections=[]
    for identity,title,surveys,summary,keywords,examples in AREAS:
        refs=[r for r in tables if r['survey'] in surveys]
        if not refs:continue
        sections.append({'id':identity,'title':title,'summary':summary,'keywords':keywords,
            'examples':examples,'source_refs':refs,'release_years':sorted({int(r['release_id'][6:10]) for r in refs})})
    known={s for a in AREAS for s in a[2]}
    for survey in sorted({r['survey'] for r in tables}-known):
        refs=[r for r in tables if r['survey']==survey]
        sections.append({'id':'other_'+str(len(sections)),'title':survey,'summary':'Documented tables: '+'; '.join(dict.fromkeys(r['title'] for r in refs[-3:])),
            'keywords':survey,'examples':[],'source_refs':refs,'release_years':sorted({int(r['release_id'][6:10]) for r in refs})})
    fingerprint=sha256(json.dumps(signature).encode()).hexdigest()
    data={'version':1,'source_fingerprint':fingerprint,'releases':inv['releases'],'sections':sections,
        'limits':['This is a guide to institution-level reports, not individual student records.',
            'A documented topic is not a guarantee that every field, year or institution has reported values.',
            'Release labels, fall snapshots, academic/fiscal periods and entering cohorts are different time concepts.',
            'Exact availability and calculation support must be checked against source fields and the coverage service.']}
    lines=['# What information is available in this IPEDS app?',
        'This guide explains the local codebooks in everyday language. It is a starting point for choosing a question, not a promise that every calculation or institution/year combination is available.',
        'Loaded source releases: '+', '.join(r.removeprefix('IPEDS_').replace('_',' ') for r in inv['releases'])+'.',
        '## Before you compare','\n'.join('- '+x for x in data['limits'])]
    for s in sections:
        latest=max(s['release_years']);refs=[r for r in s['source_refs'] if int(r['release_id'][6:10])==latest]
        lines+=['## '+s['title'],s['summary'],'Questions to try:\n'+'\n'.join('- '+x for x in s['examples']),
            'Example source documentation:\n'+'\n'.join('- '+r['release_id']+' · '+r['table_name']+' · '+r['title']+' (catalog record '+str(r['record_id'])+')' for r in refs[:3])]
    lines+=['## Source and refresh information','Built from table descriptions in the local metadata catalog, restricted to tables present in the loaded annual SQLite files. The companion JSON index retains all supporting table descriptions and their release/period labels. Runtime source fingerprint checks refresh this guide in memory if the catalog, annual files or guide definitions change.',
        'Source fingerprint: `'+fingerprint+'`.']
    data['markdown']='\n\n'.join(lines)+'\n'
    return data


def topic_index():
    return [{'id':s['id'],'title':s['title'],'summary':s['summary'],'keywords':s['keywords']} for s in get()['sections']]


def search(topic,limit=3):
    words=set(re.findall(r'[a-z0-9]+',topic.casefold()))-set('what which data information do you we have about on for the a an of available can tell me college colleges university universities'.split())
    if not words:return []
    ranked=[]
    for section in get()['sections']:
        title=set(re.findall(r'[a-z0-9]+',(section['id']+' '+section['title']).casefold()))
        terms=set(re.findall(r'[a-z0-9]+',(section['keywords']+' '+section['summary']).casefold()))
        score=4*len(words&title)+len(words&terms)
        if score:ranked.append((score,section))
    return [s for _,s in sorted(ranked,key=lambda pair:-pair[0])[:limit]]


def answer(topic=''):
    data=get();found=search(topic) if topic else []
    sections=found or data['sections']
    intro=('These are the main data areas documented in the local IPEDS files:' if not topic else
        'These documented data areas may help with your question:' if found else
        'I could not match that term in the introductory guide. This does not prove the information is absent. Here are the main documented data areas:')
    message=intro+'\n\n'+'\n'.join('- **'+s['title']+'** — '+s['summary'] for s in sections)
    message+='\n\nYou can name a school, a topic and a period, or ask me what a term means. For example: “'+sections[0]['examples'][0]+'”' if sections and sections[0]['examples'] else ''
    message+='\n\nThe loaded source releases and the observation periods are different things. Ask “Which years are available for admissions?” for a verified measure-specific answer. Not every field is reported for every institution or year.'
    scope={'question':topic,'plan':{},'measure_ids':[],'field_record_ids':[],'institutions':[],
        'time_basis':'source_release','periods':[],'population_signature':{},'topic':topic,
        'guide_section_ids':[s['id'] for s in found]}
    return {'intent':'guide','mode':'data guide','message':message,
        'guide':{'source_fingerprint':data['source_fingerprint'],'section_ids':[s['id'] for s in sections],
            'source_refs':[{'record_id':r['record_id'],'release_id':r['release_id'],'table':r['table_name'],'title':r['title']} for s in sections for r in s['source_refs']],
            'limits':data['limits']},
        'coverage':{'operation':'overview','status':'answered','scope':scope,'loaded_releases':data['releases'],
            'limits':data['limits']}}


def write_artifacts():
    data=get();GUIDE_PATH.write_text(data['markdown'],encoding='utf-8')
    INDEX_PATH.write_text(json.dumps({k:v for k,v in data.items() if k!='markdown'},indent=2,ensure_ascii=False),encoding='utf-8')
    return {'guide':str(GUIDE_PATH),'index':str(INDEX_PATH),'sections':len(data['sections']),'source_fingerprint':data['source_fingerprint']}


if __name__=='__main__':print(json.dumps(write_artifacts(),indent=2))
