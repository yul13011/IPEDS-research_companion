"""NCES comparisons through the production population query engine."""
from pathlib import Path
from collections import Counter
import datetime,json,sys,time,re,csv
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from evaluations.run_nces_aggregate_benchmarks import spec,source_year
from prototype.tests.test_query_engine import source,plan,expr,join
from prototype.query_engine import execute,field_ref
from prototype.populations import default_population

OUT=ROOT/'evaluations/nces_aggregates'

def build(q,y):
    if q in {110}:raise ValueError('Source method/selected categories pending; no inferred aggregate.')
    if q==200:
        table,cols,filters,op,nums,dens,scale,extra=(f'OM{y}',['OMAWDN8','OMACHRT'],{'OMCHRT':'50'},'ratio',['OMAWDN8'],['OMACHRT'],1,'')
    elif q==8:
        clarification=json.loads((OUT/'benchmark_clarifications.json').read_text(encoding='utf-8'))['8']
        if clarification['age_category']!='25 and above':raise ValueError('Q8 age selection requires review')
        table,cols,filters,op,nums,dens,scale,extra=(f'EF{y}B',['EFAGE09'],{'EFBAGE':'7','LSTUDY':'1','LINE':'999'},'sum',['EFAGE09'],[],1,'')
    elif q==43:
        table,cols,filters,op,nums,dens,scale,extra=(f'DRVEF12{y}',['FTE12MN'],{},'sum',['FTE12MN'],[],1,'')
    else:table,cols,filters,op,nums,dens,scale,extra=spec(q,y)
    if q==42:cols=cols+['EFDENON']
    if q==15:cols=nums=['F2D16']
    if q==17:cols=nums=['F3D09']
    if q==1:cols=nums=['INSTNM'];op='count'
    ppop=default_population(administrative_offices=q in {13,15,17,39,40,41,50,51,30})
    if q in {12,51,50,200}:ppop['degree_granting']=True
    if q in {13,39,205,207}:ppop['controls']=[1]
    if q in {15,40}:ppop['controls']=[2]
    if q in {17,41}:ppop['controls']=[3]
    if q in {206,208}:ppop['controls']=[2,3]
    if q in {19,20}:ppop['levels']=[1]
    if q==21:ppop['levels']=[2]
    if q==22:ppop['levels']=[3]
    if q==2 and y>=2020:filters={'EFFYALEV':'1'}
    if q==51:filters={**filters,'ARANK':'0','FACSTAT':'0'}
    sources=[];steps=[];joins=[]
    if op=='gr':
        nc,dc={19:('3','2'),20:('12','8'),21:('30','29')}[q]
        den,dd=source(table,y,'d',cols,{'GRTYPE':dc});num,dn=source(table,y,'n',cols,{'GRTYPE':nc})
        sources=[den,num];joins=[join('d','n')]
        steps=[expr('numerator','sum',[field_ref(dn['GRTOTLT'],'n')]),expr('denominator','sum',[field_ref(dd['GRTOTLT'],'d')]),expr('value','percent',['xnumerator','xdenominator'])]
    elif q==30:
        a,da=source(f'EAP{y}',y,'a',['EAPTOT'],{'EAPCAT':'10000','FACSTAT':'0','OCCUPCAT':'100'})
        g,dg=source(f'EAP{y}',y,'g',['EAPTOT'],{'EAPCAT':'40000','FACSTAT':'0','OCCUPCAT':'400'})
        sources=[a,g];joins=[join('a','g')]
        steps=[expr('staff','sum',[field_ref(da['EAPTOT'],'a')]),expr('assistants','sum',[field_ref(dg['EAPTOT'],'g')]),expr('value','add',['xstaff','xassistants'])]
    else:
        s,d=source(table,y,'s',cols,filters)
        if q==42:s['reconcile_distance_partition']=True
        # Complete cohort/amount pairs are explicit numeric domains; missing
        # inputs cannot contribute only to a denominator or only to a numerator.
        if op in {'ratio','mean'} and q!=42:
            for col in cols:
                s['filters'].append({'record_id':d[col],'operator':'gte','values':['0'],'code_record_ids':[]})
        if q in {205,206,207,208}:
            hd,dh=source(f'HD{y}',y,'h',[],{'RPTMTH':['1','3']})
            sources=[hd,s];joins=[join('h','s')]
        else:sources=[s]
        refs=[field_ref(d[c],'s') for c in nums]
        value=refs[0]
        for i,ref in enumerate(refs[1:]):
            steps.append(expr('row'+str(i),'add',[value,ref]));value='xrow'+str(i)
        if op=='ratio':
            steps += [expr('numerator','sum',[value]),expr('denominator','sum',[field_ref(d[dens[0]],'s')]),
                      expr('value','percent' if q in {32,33,34,35,37,42,102,103,22,200} else 'divide',['xnumerator','xdenominator'])]
        else:steps.append(expr('value','mean' if op=='mean' else 'count' if op=='count' else 'sum',[value]))
    p=plan(sources,[('xvalue','Aggregate')],joins=joins,expressions=steps,institutions=[],missing='complete_cases')
    p['population']=ppop
    return p,scale

def main():
    from prototype.population_review import EVALUATING
    EVALUATING.set(True)
    manifest=json.loads((OUT/'source_manifest.json').read_text(encoding='utf-8'))
    prior={(r['q'],r['period']):r for r in json.loads((OUT/'reference_results.json').read_text(encoding='utf-8'))}
    retry='--retry-timeouts' in sys.argv
    target=int(sys.argv[sys.argv.index('--q')+1]) if '--q' in sys.argv else None
    saved={(r['q'],r['period']):r for r in json.loads((OUT/'population_engine_results.json').read_text(encoding='utf-8'))} if retry or target is not None else {}
    previous_summary=json.loads((OUT/'population_engine_summary.json').read_text(encoding='utf-8')) if saved else None
    cases=[];started=time.perf_counter()
    for file in manifest:
        q=file['q']
        for obs in file['observations']:
            previous=saved.get((q,obs['period']))
            if previous and ((target is not None and q!=target) or (target is None and 'OperationalError: interrupted' not in previous.get('reason',''))):
                cases.append(previous);continue
            old=prior[q,obs['period']];y=source_year(q,obs['period'])
            row={k:old[k] for k in ['q','period','source_year','expected','source_file','source_row','tolerance']};row.update(actual=None,status=None,elapsed_seconds=0)
            if q in {8,42,200}:row['owner_clarification']=json.loads((OUT/'benchmark_clarifications.json').read_text(encoding='utf-8'))[str(q)]
            if not 2015<=y<=2024:row.update(status='outside_local_release_coverage');cases.append(row);continue
            start=time.perf_counter()
            try:
                p,scale=build(q,y);result=execute(p,'Calculate the specified source-bound population aggregate.')
                if len(result['rows'])!=1:raise ValueError('Expected exactly one aggregate observation')
                r=result['rows'][0];actual=r['value']
                if actual is None:raise ValueError('Aggregate has no complete usable observations')
                actual*=scale
                if r['unit']=='percent':actual/=100
                row.update(actual=actual,difference=actual-obs['expected'],status='match' if abs(actual-obs['expected'])<=row['tolerance']+1e-10 else 'mismatch',
                    plan=p,result_id=result['result_id'],numerator=r.get('numerator'),denominator=r.get('denominator'),
                    available_rows=r.get('available_rows'),requested_rows=r.get('requested_rows'),warnings=result['warnings'],
                    audit=[{k:v for k,v in a.items() if k not in {'requested_unitids','missing_unitids'}} for a in result['query_audit']])
            except Exception as e:row.update(status='blocked_definition_or_method',reason=type(e).__name__+': '+str(e))
            row['elapsed_seconds']=time.perf_counter()-start;cases.append(row)
            if previous:row['previous_attempt']={k:v for k,v in previous.items() if k not in {'plan','audit'}}
        (OUT/'population_engine_results.json').write_text(json.dumps(cases,indent=2,ensure_ascii=False),encoding='utf-8')
        print(q,dict(Counter(r['status'] for r in cases if r['q']==q)),flush=True)
    summary={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'observations':len(cases),'status':dict(Counter(r['status'] for r in cases)),
        'wall_seconds':time.perf_counter()-started,'model_calls':0,'estimated_api_usd':0,'scope':'Actual population query executor against independent NCES spreadsheet expectations; no AI planning in this numerical pass.'}
    if previous_summary:summary['previous_full_run']=previous_summary
    if target is not None:summary['targeted_rerun_q']=target
    (OUT/'population_engine_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    from prototype.population_review import fingerprint,POLICY
    blocked={fingerprint(r['plan']):{'q':r['q'],'source_year':r['source_year'],'reason':'Unresolved NCES comparator discrepancy; expected statistical values are not stored in production.'} for r in cases if r['status']=='mismatch'}
    POLICY.write_text(json.dumps({'policy':'Known method/scope discrepancies only; general source-backed aggregate queries remain supported. No benchmark answer values are used by execution.','generated_at':summary['timestamp'],'blocked':blocked},indent=2),encoding='utf-8')
    with (OUT/'population_engine_results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['q','period','source_year','expected','actual','difference','tolerance','status','reason','elapsed_seconds','numerator','denominator'],extrasaction='ignore');w.writeheader();w.writerows(cases)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
