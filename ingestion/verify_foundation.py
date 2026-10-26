"""Infrastructure checks only; no analytical question or measure tests."""
from pathlib import Path
import argparse,csv,hashlib,json,sqlite3,zipfile,xml.etree.ElementTree as ET
import openpyxl
BASE=Path(__file__).resolve().parents[1];DATA=BASE/'data';CATALOG=DATA/'metadata_catalog.sqlite'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def require(condition,message):
    if not condition:raise RuntimeError(message)
def metadata_check():
    db=sqlite3.connect('file:'+CATALOG.as_posix()+'?mode=ro',uri=True);report=[]
    try:
        for sid,release,role,path,digest in db.execute("SELECT source_id,release_id,role,path,sha256 FROM source_files WHERE role IN ('codebook','release_notes') ORDER BY source_id").fetchall():
            p=Path(path);require(sha(p)==digest,'Source hash changed: '+path)
            if role=='codebook':
                w=openpyxl.load_workbook(p,read_only=True,data_only=False);sheet_count=0;row_count=0
                for s in w:
                    sidrow=db.execute('SELECT sheet_id FROM sheets WHERE source_id=? AND sheet_name=?',(sid,s.title)).fetchone();require(sidrow is not None,'Sheet absent '+s.title)
                    saved=dict(db.execute('SELECT row_number,values_json FROM sheet_rows WHERE sheet_id=?',(sidrow[0],)).fetchall());seen=0
                    for n,row in enumerate(s.iter_rows(values_only=True),1):
                        if not any(x is not None for x in row):continue
                        expected=json.loads(json.dumps(row,default=str,ensure_ascii=False))
                        require(n in saved and json.loads(saved[n])==expected,f'Workbook cell mismatch {release}/{s.title}/{n}');seen+=1
                    require(seen==len(saved),'Unexpected saved rows '+release+'/'+s.title);row_count+=seen;sheet_count+=1
                w.close();report.append({'release':release,'role':role,'sheets':sheet_count,'nonempty_rows_exactly_matched':row_count,'source_sha256_matches':True})
            else:
                ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                with zipfile.ZipFile(p) as z:root=ET.fromstring(z.read('word/document.xml'))
                paragraphs=[''.join(t.text or '' for t in para.findall('.//w:t',ns)) for para in root.findall('.//w:p',ns)]
                expected={n:t for n,t in enumerate(paragraphs,1) if t.strip()}
                actual=dict(db.execute('SELECT r.source_row,n.text FROM release_notes n JOIN records r ON r.record_id=n.record_id WHERE r.source_id=?',(sid,)).fetchall())
                require(expected==actual,'Release-note paragraph mismatch '+release)
                report.append({'release':release,'role':role,'paragraphs_exactly_matched':len(actual),'source_sha256_matches':True})
        require(len(report)==20,'Expected ten codebooks and ten release notes')
    finally:db.close()
    (DATA/'metadata_source_verification.json').write_text(json.dumps({'passed':True,'sources':report},indent=2),encoding='utf-8');print('Exact codebook-cell and release-note checks passed for all 20 document sources.')
def annual_check():
    status=json.loads((DATA/'annual'/'import_status.json').read_text());require(status.get('complete') is True,'Annual import is incomplete')
    db=sqlite3.connect('file:'+CATALOG.as_posix()+'?mode=ro',uri=True);summary=[]
    try:
        for release, in db.execute('SELECT release_id FROM releases ORDER BY release_id').fetchall():
            folder=DATA/'annual'/release;m=json.loads((folder/'verification.json').read_text());out=Path(m['output'])
            require(sha(out)==m['output_sha256'],'Output file hash mismatch '+release)
            require(m['integrity_check']=='ok' and m['all_table_value_hashes_match'] and m['per_column_null_counts_match'],'Conversion verification failed '+release)
            require(db.execute('SELECT sha256 FROM source_files WHERE release_id=? AND role=?',(release,'access_database')).fetchone()[0]==m['source_sha256'],'Catalog source hash differs '+release)
            source_tables=list(csv.DictReader((folder/'table_checks.csv').open(encoding='utf-8',newline='')))
            annual=sqlite3.connect('file:'+out.as_posix()+'?mode=ro',uri=True)
            try:
                actual={r[0] for r in annual.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
                require(actual=={r['table'] for r in source_tables},'Table inventory mismatch '+release)
                require(db.execute('SELECT COUNT(*) FROM physical_tables WHERE release_id=?',(release,)).fetchone()[0]==len(source_tables),'Physical catalog table count mismatch '+release)
                for t in source_tables:
                    quoted='"'+t['table'].replace('"','""')+'"'
                    count=annual.execute('SELECT COUNT(*) FROM '+quoted).fetchone()[0]
                    require(count==int(t['source_rows'])==int(t['sqlite_rows']),'Independent row-count mismatch '+release+'/'+t['table'])
                    actual_cols=[r[1] for r in annual.execute('PRAGMA table_info('+quoted+')')]
                    expected_cols=[r[0] for r in db.execute('SELECT column_name FROM physical_columns WHERE release_id=? AND table_name=? COLLATE NOCASE ORDER BY ordinal',(release,t['table']))]
                    require(actual_cols==expected_cols,'Catalog physical columns differ '+release+'/'+t['table'])
            finally:annual.close()
            summary.append({'release':release,'tables':m['tables'],'rows':m['rows'],'all_values_verified':True,'output_sha256':m['output_sha256'],'independent_row_counts_and_catalog_schema_match':True})
        require(len(summary)==10,'Expected ten annual copies')
        # This checks known documentation/physical disagreement handling, not a measure answer.
        warnings=db.execute("SELECT COUNT(*) FROM issues WHERE release_id='IPEDS_2023-24_Final' AND issue_type='documented_column_absent'").fetchone()[0]
        require(warnings==344,'Known SFA placement discrepancies not captured')
        require(db.execute('PRAGMA foreign_key_check').fetchall()==[],'Catalog foreign keys failed')
        report={'passed':True,'annual_copies':summary,'total_tables':sum(r['tables'] for r in summary),'total_rows':sum(r['rows'] for r in summary),'known_2023_documentation_placement_warnings':warnings,'scope':'Faithful conversion and comprehensive searchable metadata only. No measure mappings or analytical benchmark questions tested.'}
    finally:db.close()
    (DATA/'foundation_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--metadata-only',action='store_true');parser.add_argument('--annual-only',action='store_true');args=parser.parse_args()
    if not args.annual_only:metadata_check()
    if not args.metadata_only:annual_check()
