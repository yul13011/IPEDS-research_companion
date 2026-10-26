"""Exploratory live IC probes; source expectations captured independently of planner."""
import json
import time
import traceback
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from prototype.catalog import readonly, annual_path
from prototype.institution_confirmation import ask
from prototype.responses import finalize_answer
from prototype.progress import reporting

OUT = Path(os.environ.get('IPEDS_PROBE_OUT','evaluations/ic_categorical_probes'))
OUT.mkdir(exist_ok=True)
CASES = [
 ('calendar', 'What academic calendar system did Smith College use in 2024-25?', ['CALSYS']),
 ('affiliation', 'Compare the religious affiliations of Boston College and Smith College in 2024-25.', ['RELAFFIL','CNTLAFFI']),
 ('open_admission', 'Did Bunker Hill Community College and Smith College have open admission policies in 2024-25?', ['OPENADMP']),
 ('award_levels', "Did Smith College, Mount Holyoke College, and Wellesley College offer bachelor’s and master’s degrees in 2024-25?", ['LEVEL5','LEVEL7']),
 ('combined_services', 'Which Massachusetts degree-granting institutions offered both study abroad and on-campus childcare for students’ children in 2024-25? List their names.', ['SLO6','STUSRV8']),
 ('service_count', 'How many Massachusetts degree-granting institutions offered on-campus childcare for students’ children in 2024-25?', ['STUSRV8']),
 ('distance_distinction', 'Did Wellesley College offer undergraduate distance education courses, complete undergraduate distance education programs, or both in 2024-25?', ['DSTNUGC','DSTNUGP']),
 ('temporal', 'Did Smith College accept Advanced Placement (AP) credits in both 2015-16 and 2024-25?', ['CREDITS3']),
 ('conditional_numeric', 'What percentage of Smith College undergraduates were formally registered with disability services in the 2024-25 Institutional Characteristics release? State the student observation year.', ['DISAB','DISABPCT']),
 ('mixed', 'For Smith College in the 2024-25 Institutional Characteristics release, show its academic calendar system and the percentage of undergraduates formally registered with disability services. State the student observation year.', ['CALSYS','DISAB','DISABPCT']),
 ('code_definition', 'In the 2024-25 Institutional Characteristics codebook, what does “Implied no” mean for on-campus childcare, and how is it different from “Not reported”?', ['STUSRV8']),
 ('quality_gap', 'Using only Institutional Characteristics, which has better academic counseling services in 2024-25: Smith College or Mount Holyoke College?', ['STUSRV2']),
]
FOLLOWON_CASES = [
 ('threshold', 'In 2024-25 IPEDS Institutional Characteristics, what percentage of undergraduates at Bentley University were formally registered with disability services? Explain whether an exact percentage is available.', ['DISAB','DISABPCT']),
 ('definition_rephrase', 'Define the label Implied no for on-campus childcare in the 2024-25 Institutional Characteristics codebook.', ['STUSRV8']),
]

def source_evidence():
    variables=sorted({v for _,_,vs in CASES for v in vs})
    with readonly('data/metadata_catalog.sqlite') as c:
        docs=[dict(r) for r in c.execute("select r.*,f.path as source_file,s.sheet_name from records r join source_files f on r.source_id=f.source_id left join sheets s on r.sheet_id=s.sheet_id where r.kind in ('variable_definition','code_value','table_definition') and r.table_name in ('IC2024','IC2015','HD2024') and (r.variable_name in ("+','.join('?' for _ in variables)+") or r.kind='table_definition')",variables)]
    queries={
        'institutions': 'select h.INSTNM,h.UNITID,'+','.join('i.'+v for v in variables)+' from HD2024 h join IC2024 i on h.UNITID=i.UNITID where h.UNITID in (167835,166939,168218,164924,165112) order by h.INSTNM',
        'combined_services': "select h.UNITID,h.INSTNM from HD2024 h join IC2024 i on h.UNITID=i.UNITID where h.STABBR='MA' and h.DEGGRANT=1 and i.SLO6=1 and i.STUSRV8=1 order by h.INSTNM",
        'service_count': "select h.UNITID,h.INSTNM from HD2024 h join IC2024 i on h.UNITID=i.UNITID where h.STABBR='MA' and h.DEGGRANT=1 and i.STUSRV8=1 order by h.INSTNM",
    }
    with readonly(annual_path(2024)) as c:
        expected={k:{'sql':sql,'rows':[dict(r) for r in c.execute(sql)]} for k,sql in queries.items()}
    with readonly(annual_path(2015)) as c:
        expected['temporal_2015']={'sql':'select UNITID,CREDITS3 from IC2015 where UNITID=167835','rows':[dict(r) for r in c.execute('select UNITID,CREDITS3 from IC2015 where UNITID=167835')]}
    expected['source_documentation']=docs
    (OUT/'source_expectations.json').write_text(json.dumps(expected,indent=2,default=str),encoding='utf-8')

def run_case(case):
    ident,q,variables=case
    events=[]
    def run_turn(tag,question,history=None,previous=None):
        start=time.perf_counter()
        try:
            with reporting(lambda stage: events.append({'elapsed':time.perf_counter()-start,'stage':stage})):
                answer=finalize_answer(ask(question, previous=previous, use_model=True, conversation=history),question)
            item={'id':tag,'question':question,'answer':answer}
        except Exception as exc:
            item={'id':tag,'question':question,'error_type':type(exc).__name__,'error':str(exc),'traceback':traceback.format_exc()}
        item.update(elapsed_seconds=time.perf_counter()-start,events=list(events),expected_variables=variables)
        (OUT/(tag+'.json')).write_text(json.dumps(item,indent=2,default=str),encoding='utf-8')
        print(json.dumps({'id':tag,'seconds':round(item['elapsed_seconds'],2),'intent':item.get('answer',{}).get('intent'),'message':item.get('answer',{}).get('message',item.get('error'))}),flush=True)
        return item
    item=run_turn(ident,q)
    if ident=='calendar' and 'answer' in item:
        a=item['answer'];history=[{'question':q,'answer':a}]
        run_turn('calendar_followup','And Mount Holyoke College?',history,a.get('catalog_plan') or a.get('plan') or a.get('catalog_context'))
    if ident=='distance_distinction' and 'answer' in item:
        a=item['answer'];history=[{'question':q,'answer':a}]
        run_turn('distance_definition_followup','What is the difference between those two categories?',history,a.get('catalog_plan') or a.get('plan') or a.get('catalog_context'))
    return ident

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--followon',action='store_true')
    args=parser.parse_args()
    if args.followon:
        with readonly(annual_path(2024)) as c:
            sql='select UNITID,DISAB,DISABPCT from IC2024 where UNITID=164739'
            rows=[dict(r) for r in c.execute(sql)]
        (OUT/'threshold_source.json').write_text(json.dumps({'sql':sql,'rows':rows},indent=2),encoding='utf-8')
    else:
        source_evidence()
    with ThreadPoolExecutor(max_workers=2 if args.followon else 3) as pool:
        futures=[pool.submit(run_case,c) for c in (FOLLOWON_CASES if args.followon else CASES)]
        for f in as_completed(futures):
            print('COMPLETED',f.result(),flush=True)
