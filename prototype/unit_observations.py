"""Resolve source-documented row-dependent units without changing values."""
from functools import lru_cache
import re


@lru_cache(maxsize=4096)
def _program_unit(record_id,unitid,metadata_stamp,data_stamp):
    from .catalog import DATA,readonly,annual_path
    with readonly(DATA/'metadata_catalog.sqlite') as db:
        d=db.execute('SELECT r.release_id,r.table_name,r.variable_name,v.long_description FROM records r JOIN variable_docs v USING(record_id) WHERE record_id=?',(record_id,)).fetchone()
        if not d:return None
        match=re.fullmatch(r'CIPLGTH([1-6])',d['variable_name'],re.I)
        if not match or not re.search(r'clock or credit|credit or clock',d['long_description'],re.I):return None
        selector='PRGMSR'+match[1];table=d['table_name'];year=int(d['release_id'][6:10])
        if not re.fullmatch(r'[A-Za-z0-9_]+',table):return None
        physical=db.execute('SELECT 1 FROM physical_columns WHERE release_id=? AND table_name=? AND column_name=? COLLATE NOCASE',(d['release_id'],table,selector)).fetchone()
        if not physical:return None
        codes=[dict(c) for c in db.execute('SELECT record_id,code_value,value_label FROM code_values WHERE release_id=? AND table_name=? AND variable_name=? COLLATE NOCASE',(d['release_id'],table,selector))]
    sql=f'SELECT "{selector}" FROM "{table}" WHERE UNITID=?'
    with readonly(annual_path(year)) as db:rows=db.execute(sql,[unitid]).fetchmany(2)
    if len(rows)!=1 or rows[0][0] is None:return None
    value=str(rows[0][0]);value=value.removesuffix('.0')
    code=next((c for c in codes if c['code_value']==value and c['value_label'].strip().lower() in {'clock hours','contact hours','credit hours'}),None)
    if not code:return None
    return {'unit':code['value_label'].lower(),'code_record_id':code['record_id'],'code_value':value,
            'selector':selector,'table':table,'source_release':d['release_id'],'unitid':unitid,'sql':sql,'parameters':[unitid]}


def resolve_row(row):
    meta=row.get('unit_metadata',{})
    if meta.get('status')!='conditional' or not meta.get('unit_selector') or row.get('unitid') is None:return None
    from .catalog import DATA,annual_path
    year=int(meta['release_id'][6:10]);path=annual_path(year)
    evidence=_program_unit(meta['record_id'],int(row['unitid']),(DATA/'metadata_catalog.sqlite').stat().st_mtime_ns,path.stat().st_mtime_ns)
    if not evidence:return None
    return {**meta,'unit':evidence['unit'],'status':'verified','basis':'Same-row program unit selector and supplied category definition',
            'unit_selector_evidence':evidence}
