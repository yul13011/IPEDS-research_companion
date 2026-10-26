"""Independently compare saved live answers with annual rows and codebook labels."""
from contextlib import ExitStack
from pathlib import Path
import json
from prototype.catalog import readonly,annual_path

folders=['ic_categorical_acceptance','ic_categorical_final_checks','ic_categorical_after_final']
report=[]
with ExitStack() as stack:
    metadata=stack.enter_context(readonly('data/metadata_catalog.sqlite'))
    annual={y:stack.enter_context(readonly(annual_path(y))) for y in [2015,2024]}
    for folder in folders:
        for path in sorted((Path('evaluations')/folder).glob('*.json')):
            saved=json.loads(path.read_text(encoding='utf-8'));a=saved.get('answer',{});result=a.get('result',{})
            if not result.get('observation_plan'):continue
            checks=0
            for row in result['rows']:
                d=metadata.execute('select r.table_name,r.variable_name,r.release_id,v.long_description from records r join variable_docs v using(record_id) where r.record_id=?',(row['record_id'],)).fetchone()
                assert d is not None
                year=int(d['release_id'][6:10]);db=annual[year]
                raw=db.execute('SELECT "'+d['variable_name']+'" FROM "'+d['table_name']+'" WHERE UNITID=?',(row['unitid'],)).fetchone()
                assert raw is not None,(path,row)
                assert raw[0]==row['raw_code'],(path,row)
                if row['result_type']=='categorical':
                    codes=metadata.execute('select record_id,code_value,value_label from code_values where release_id=? and table_name=? and variable_name=?',(d['release_id'],d['table_name'],d['variable_name'])).fetchall()
                    matches=[c for c in codes if c['code_value']==str(raw[0])]
                    if matches:
                        assert row['response_label']==matches[0]['value_label'],(path,row)
                        assert set(row['category_record_ids'])=={m['record_id'] for m in matches}
                    assert row['value'] is None
                elif row['result_type']=='bounded':
                    selector=db.execute('SELECT DISAB FROM "'+d['table_name']+'" WHERE UNITID=?',(row['unitid'],)).fetchone()[0]
                    code=metadata.execute("select value_label from code_values where release_id=? and table_name=? and variable_name='DISAB' and code_value=?",(d['release_id'],d['table_name'],str(selector))).fetchone()[0]
                    assert row['response_label']==code
                    assert row['value'] is None
                    assert row['reporting_period']=='Fall 2023'
                elif row['result_type']=='quantitative':
                    assert row['value']==float(raw[0])
                    if d['variable_name']=='DISABPCT':assert row['reporting_period']=='Fall 2023'
                checks+=1
            if saved['id'].startswith('original_massachusetts'):
                expected={r[0] for r in annual[2024].execute("select h.UNITID from HD2024 h join IC2024 i on h.UNITID=i.UNITID where h.STABBR='MA' and h.DEGGRANT=1 and i.DSTNCED1=1")}
                assert {r['unitid'] for r in result['rows']}==expected
                assert len(expected)==83
            report.append({'file':str(path),'checked_cells':checks,'source_values_and_labels_match':True})
Path('evaluations/typed_observations_live_source_verification.json').write_text(json.dumps({'answers_checked':len(report),'cells_checked':sum(r['checked_cells'] for r in report),'results':report},indent=2),encoding='utf-8')
print('Checked',len(report),'live answers and',sum(r['checked_cells'] for r in report),'source cells.')
