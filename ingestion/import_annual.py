"""Convert all annual Access sources without modifying originals. No measure tests."""
from pathlib import Path
import concurrent.futures,csv,hashlib,json,subprocess,sys,time,os

BASE=Path(__file__).resolve().parents[1];PROJECT=BASE.parent
ROOT=PROJECT/'IPEDS Data';OUT=BASE/'data'/'annual'
LIB=PROJECT/'outputs'/'access_conversion'
CP=os.pathsep.join(str(p) for p in [BASE/'ingestion',LIB/'jackcess.jar',LIB/'commons-lang3.jar',LIB/'commons-logging.jar',LIB/'sqlite-jdbc.jar',LIB/'slf4j-api.jar',LIB/'slf4j-nop.jar'])
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(path,data):
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,indent=2),encoding='utf-8');tmp.replace(path)
def convert(folder):
    source=next(folder.glob('*.accdb'));release=folder.name;out=OUT/release;out.mkdir(parents=True,exist_ok=True)
    target=out/(source.stem+'.sqlite');report=out/'verification.json'
    source_hash=sha(source);converter_hash=sha(BASE/'ingestion'/'ConvertAnnual.java')
    if report.exists() and target.exists():
        old=json.loads(report.read_text())
        if old['source_sha256']==source_hash and old['converter_sha256']==converter_hash and old['output_sha256']==sha(target):
            return {'release':release,'status':'verified_existing','rows':old['rows'],'tables':old['tables'],'output':str(target)}
        raise RuntimeError('Existing output/version mismatch; preserve it and select a new output location: '+str(target))
    if target.exists():raise RuntimeError('Output exists without verification manifest: '+str(target))
    partial=out/(source.stem+'.sqlite.inprogress')
    if partial.exists():raise RuntimeError('An unfinished conversion exists; inspect its log before retrying: '+str(partial))
    started=time.time()
    with (out/'conversion.log').open('w',encoding='utf-8') as log:
        result=subprocess.run(['java','-Xmx768m','-cp',CP,'ConvertAnnual',str(source),str(partial),str(out)],stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError('Conversion failed; see '+str(out/'conversion.log'))
    if sha(source)!=source_hash:raise RuntimeError('Source changed during conversion: '+str(source))
    checks=list(csv.DictReader((out/'table_checks.csv').open(encoding='utf-8',newline='')))
    if not checks or any(r['verified']!='true' or r['source_values_sha256']!=r['sqlite_values_sha256'] or r['source_rows']!=r['sqlite_rows'] for r in checks):raise RuntimeError('Verification evidence incomplete')
    partial.replace(target)
    evidence={'release':release,'source':str(source),'source_sha256':source_hash,'source_bytes':source.stat().st_size,'source_unchanged_after_conversion':True,'output':str(target),'output_sha256':sha(target),'converter_sha256':converter_hash,'tables':len(checks),'rows':sum(int(r['sqlite_rows']) for r in checks),'integrity_check':'ok','all_table_value_hashes_match':True,'per_column_null_counts_match':True,'elapsed_seconds':round(time.time()-started,1),'type_policy':'Access integer -> INTEGER; floating point -> REAL; NUMERIC/MONEY -> exact decimal TEXT; TEXT/MEMO -> TEXT. Unsupported types fail. No analytical transformations.'}
    save(report,evidence)
    return {'release':release,'status':'complete','tables':evidence['tables'],'rows':evidence['rows'],'output':str(target)}
if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True);folders=sorted(f for f in ROOT.iterdir() if f.is_dir() and list(f.glob('*.accdb')))
    state={'started_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'source_root':str(ROOT),'results':[],'expected_releases':len(folders)}
    save(OUT/'import_status.json',state)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        jobs={pool.submit(convert,f):f.name for f in folders}
        for job in concurrent.futures.as_completed(jobs):
            try:r=job.result()
            except Exception as e:r={'release':jobs[job],'status':'failed','error':str(e)}
            state['results'].append(r);save(OUT/'import_status.json',state);print(json.dumps(r),flush=True)
    failed=[r for r in state['results'] if r['status']=='failed']
    state['complete']=len(state['results'])==len(folders) and not failed;save(OUT/'import_status.json',state)
    sys.exit(1 if failed else 0)
