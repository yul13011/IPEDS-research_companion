"""Prepare proposed units and an old/new audit. Does not modify source data."""
import sys,json,sqlite3,csv,re,shutil
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from analysis_catalog.catalog import connection
from prototype.field_semantics import _describe_field_legacy as describe_field
from prototype.unit_metadata import resolve,fingerprint,VERSION


def main():
    target=ROOT/'data/unit_catalog.proposed.sqlite'
    audit=[];counts=Counter();changes=Counter();examples={}
    with connection() as db,sqlite3.connect(target) as out:
        out.execute('DROP TABLE IF EXISTS units')
        out.execute('CREATE TABLE units(record_id INTEGER PRIMARY KEY,release_id TEXT,table_name TEXT,variable_name TEXT,fingerprint TEXT,assignment TEXT)')
        tables={(r['release_id'],r['table_name']):{'population_evidence':json.loads(r['population_evidence_json']),
            'period_evidence':json.loads(r['period_evidence_json']),'profile':json.loads(r['profile_json'])} for r in db.execute('SELECT * FROM tables')}
        for row in db.execute('SELECT d.*,v.title,v.long_description,v.data_type,v.format FROM definitions d JOIN source.variable_docs v USING(record_id) ORDER BY d.record_id'):
            d=dict(row);t=tables.get((d['release_id'],d['table_name']),{})
            old=describe_field(d,t)['unit'];new=resolve(d,t,_prepared=False)
            out.execute('INSERT INTO units VALUES(?,?,?,?,?,?)',(d['record_id'],d['release_id'],d['table_name'],d['variable_name'],fingerprint(d,t),json.dumps(new)))
            counts[new['status']+':'+new['unit']]+=1
            if old!=new['unit']:changes[old+' -> '+new['unit']]+=1
            audit.append({'record_id':d['record_id'],'release':d['release_id'],'table':d['table_name'],'variable':d['variable_name'],
                'title':d['title'],'old_semantic_unit':old,'proposed_unit':new['unit'],'status':new['status'],'basis':new['basis']})
    with (ROOT/'evaluations/unit_catalog_proposal.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(audit[0]));w.writeheader();w.writerows(audit)
    families={}
    for a in audit:families.setdefault((re.sub(r'\d{4}','{YEAR}',a['table']),a['variable']),set()).add(a['proposed_unit'])
    drift=[{'table_family':k[0],'variable':k[1],'units':sorted(v)} for k,v in families.items() if len(v)>1]
    summary={'stage':'proposal; no production integration','version':VERSION,'fields':len(audit),'releases':sorted({a['release'] for a in audit}),
        'counts':dict(counts),'changes':dict(changes),'cross_year_unit_differences':drift,
        'limitations':'Assignments require evidence review; unresolved cases and identifiers are not errors. Cross-year differences are review flags, not proof of drift. Original source data unchanged.'}
    (ROOT/'evaluations/unit_catalog_proposal_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    if '--activate' in sys.argv:
        shutil.copy2(target,ROOT/'data/unit_catalog.sqlite')
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
