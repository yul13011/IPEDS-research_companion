"""Materialize source-backed descriptions for every catalog field, not approvals."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
import sys
import time

BASE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(BASE),str(BASE/'.packages')]
from analysis_catalog.catalog import connection
from prototype.field_semantics import describe_field, VERSION


def build():
    start=time.perf_counter();target=BASE/'data/field_semantics.sqlite'
    staging=BASE/'data/field_semantics.build.sqlite'
    with connection() as db:
        identity=json.loads(db.execute("SELECT value_json FROM build_info WHERE key='source_identity_sha256'").fetchone()[0])
        tables={}
        for row in db.execute('SELECT * FROM tables'):
            t=dict(row)
            for key in ['population_evidence','period_evidence','profile']:t[key]=json.loads(t[key+'_json'])
            tables[(t['release_id'],t['table_name'].casefold())]=t
        rows=list(db.execute('SELECT d.*,v.title,v.long_description,v.data_type,v.format FROM definitions d JOIN source.variable_docs v USING(record_id)'))
    counts=Counter();families=Counter()
    with sqlite3.connect(staging) as output:
        output.execute('DROP TABLE IF EXISTS field_semantics');output.execute('DROP TABLE IF EXISTS metadata')
        output.execute('CREATE TABLE field_semantics (record_id INTEGER PRIMARY KEY,release_id TEXT,table_name TEXT,variable_name TEXT,descriptor_json TEXT)')
        output.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY,value_json TEXT)')
        for row in rows:
            d=dict(row);t=tables.get((d['release_id'],d['table_name'].casefold()),{})
            descriptor=describe_field(d,t)
            descriptor['physical_status']=d['physical_status'];descriptor['definition_hash']=d['definition_hash']
            output.execute('INSERT INTO field_semantics VALUES (?,?,?,?,?)',(d['record_id'],d['release_id'],d['table_name'],d['variable_name'],json.dumps(descriptor,ensure_ascii=False)))
            counts[descriptor['readiness']]+=1;families[descriptor['unit']]+=1
        report={'timestamp':datetime.now(timezone.utc).isoformat(),'descriptor_version':VERSION,'source_identity_sha256':identity,
                'fields':len(rows),'description_status':dict(counts),'units':dict(families),'build_seconds':time.perf_counter()-start,
                'policy':'Source-backed descriptions for every variable definition; unknown units remain explicit. This is not semantic or execution approval. Runtime re-derives meanings from current exact source records and row selectors.'}
        for key,value in report.items():output.execute('INSERT INTO metadata VALUES (?,?)',(key,json.dumps(value)))
    output.close()
    staging.replace(target)
    (BASE/'data/field_semantics_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':print(json.dumps(build(),indent=2))
