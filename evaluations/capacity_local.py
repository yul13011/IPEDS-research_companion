"""Offline local capacity probe; no provider calls or source-data writes."""
import os, sys, time, json, ctypes, threading, traceback, faulthandler
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.dont_write_bytecode=True
faulthandler.dump_traceback_later(40,repeat=True)

class Counters(ctypes.Structure):
    _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)]+[(n,ctypes.c_size_t) for n in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=ctypes.c_void_p
psapi=ctypes.WinDLL('psapi');psapi.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),ctypes.c_ulong]
def memory():
    c=Counters();c.cb=ctypes.sizeof(c)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(c),c.cb):raise ctypes.WinError()
    return dict(resident_MiB=round(c.WorkingSetSize/2**20,2),private_commit_MiB=round(c.PagefileUsage/2**20,2),process_peak_resident_MiB=round(c.PeakWorkingSetSize/2**20,2))

records=[];retained=[]
REPORT=ROOT/'evaluations'/('capacity_local_startup_results.json' if '--startup' in sys.argv else 'capacity_local_results.json')
def stage(name,fn):
    print('START '+name,flush=True);before=memory();samples=[];stop=threading.Event()
    def monitor():
        while not stop.wait(.02):samples.append(memory())
    thread=threading.Thread(target=monitor,daemon=True);thread.start()
    start=time.perf_counter();cpu=time.process_time()
    try:
        value=fn();status='ok';error=None
    except Exception:
        value=None;status='error';error=traceback.format_exc()
    elapsed=time.perf_counter()-start;cpu_elapsed=time.process_time()-cpu
    stop.set();thread.join();after=memory();samples+=[before,after]
    row=dict(stage=name,status=status,wall_seconds=round(elapsed,4),cpu_seconds=round(cpu_elapsed,4),before=before,after=after,stage_peak_resident_MiB=max(x['resident_MiB'] for x in samples),stage_peak_private_commit_MiB=max(x['private_commit_MiB'] for x in samples))
    if error:row['error']=error
    if isinstance(value,dict) and '_summary' in value:row['summary']=value['_summary']
    records.append(row);print(json.dumps(row),flush=True)
    REPORT.write_text(json.dumps({'platform':sys.platform,'python':sys.version,'logical_cpus':os.cpu_count(),'scope':'Offline Windows single-process probe; query workers approximate simultaneous backend work, not browser sessions. CPU time includes monitor thread. No model calls.','stages':records},indent=2),encoding='utf-8')
    return value

def imports():
    global analytics,exports,catalog,qe,source,plan,field_ref,finalize_answer
    from prototype import analytics,exports,catalog
    from prototype import query_engine as qe
    from prototype.tests.test_query_engine import source,plan,field_ref
    from prototype.responses import finalize_answer
    return {'_summary':{'imports':'Streamlit/pandas/Altair/export/query modules'}}

def basic():return analytics.execute(analytics.Plan(['applicants','admits','admission_rate','matriculants','yield_rate'],['Yale'],[2024]))
def trend():return analytics.execute(analytics.Plan(['graduation_rate'],['Ivy League'],list(range(2015,2025))))
def relational():
    s,d=source('C2024_A',fields=['CTOTALT'],filters={'CIPCODE':'99','MAJORNUM':'1'},groups=['AWLEVEL'])
    return qe.execute(plan([s],[(field_ref(d['CTOTALT'],'s'),'Awards')]),'Yale awards by degree level for July 2023–June 2024')
def exports_for(result):
    blobs={name:fn(result) for name,fn in [('csv',exports.csv_bytes),('excel',exports.excel_bytes),('audit',exports.audit_bytes)]}
    return {'_summary':{name:len(blob) for name,blob in blobs.items()}}
def workload():
    result=trend();exports_for(result);return result

def national():
    from evaluations.run_population_engine_benchmarks import build
    p,_=build(42,2024)
    result=qe.execute(p,'Percentage of students in any distance education in fall 2024')
    return result

if __name__=='__main__':
    print('BASELINE '+json.dumps(memory()),flush=True)
    if '--startup' in sys.argv:
        def empty_ui():
            from streamlit.testing.v1 import AppTest
            app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=30).run()
            if app.exception:raise RuntimeError(str(app.exception))
            retained.append(app)
            return {'_summary':{'retained_UI_sessions':len(retained)}}
        stage('fresh_UI_session_1',empty_ui)
        stage('empty_UI_session_2',empty_ui)
        stage('backend_imports',imports)
        def cycles():
            for i in range(10):
                result=workload()
                retained.append(result)
            return {'_summary':{'completed_cycles':10,'retained_answers':10}}
        stage('ten_sequential_query_export_cycles',cycles)
        faulthandler.cancel_dump_traceback_later()
        raise SystemExit(0 if all(r['status']=='ok' for r in records) else 1)
    stage('imports',imports)
    if records[-1]['status']!='ok':raise SystemExit(1)
    stage('metadata_search',lambda:catalog.search('faculty',limit=25))
    a=stage('single_institution',basic)
    b=stage('eight_institutions_ten_years',trend)
    c=stage('catalog_relational_query',relational)
    if b:stage('csv_excel_audit_exports',lambda:exports_for(b))
    n=stage('national_distance_education',national)
    if n:stage('national_exports',lambda:exports_for(n))
    if '--ui' in sys.argv:
        def render():
            from streamlit.testing.v1 import AppTest
            app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=30).run()
            if app.exception:raise RuntimeError(str(app.exception))
            if b:
                answer=finalize_answer({'intent':'analyze','result':b,'plan':b['plan']},'Ivy League graduation rate trends')
                app.session_state['history']=[{'question':'Ivy League graduation rate trends','answer':answer}]
                app.session_state['main_page']='Ask & Analyze';app.run()
                if app.exception:raise RuntimeError(str(app.exception))
            retained.append(app)
            return {'_summary':{'retained_UI_sessions':len(retained)}}
        stage('UI_session_1',render)
        stage('UI_session_2',render)
    stage('one_active_backend',workload)
    def two():
        with ThreadPoolExecutor(max_workers=2) as pool:
            answers=list(pool.map(lambda _:workload(),range(2)))
        retained.extend(answers)
        return {'_summary':{'answers':len(answers),'rows':[len(r['rows']) for r in answers]}}
    stage('two_active_backends',two)
    def two_national():
        with ThreadPoolExecutor(max_workers=2) as pool:
            answers=list(pool.map(lambda _:national(),range(2)))
        retained.extend(answers)
        return {'_summary':{'answers':len(answers),'rows':[len(r['rows']) for r in answers]}}
    stage('two_active_national_backends',two_national)
    def history():
        import copy
        for user in range(2):retained.append([copy.deepcopy(b) for _ in range(30)])
        return {'_summary':{'simulated_users':2,'independent_retained_answers':60,'rows_per_answer':len(b['rows'])}}
    if b:stage('two_users_30_answers_each',history)
    faulthandler.cancel_dump_traceback_later()
