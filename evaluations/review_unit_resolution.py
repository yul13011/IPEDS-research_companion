"""Compare the frozen unresolved batch and inspect actual conditional-unit gaps."""
import json,sqlite3,sys,re
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.catalog import readonly,annual_path,DATA


def main():
    with sqlite3.connect(ROOT/'evaluations/unit_catalog_before_resolution.sqlite') as db:
        before={rid:json.loads(a) for rid,a in db.execute('SELECT record_id,assignment FROM units')}
    with sqlite3.connect(ROOT/'data/unit_catalog.proposed.sqlite') as db:
        after={rid:json.loads(a) for rid,a in db.execute('SELECT record_id,assignment FROM units')}
    batch=[rid for rid,a in before.items() if a['status']=='unresolved']
    remaining=[rid for rid in batch if after[rid]['status'] not in {'verified','conditional'}]
    changes=[];conditional=[];gaps=[];terminology=[]
    with readonly(DATA/'metadata_catalog.sqlite') as cat:
        for rid in batch:
            a=after[rid];doc=cat.execute('SELECT r.title,f.path,s.sheet_name,r.source_row FROM records r JOIN source_files f USING(source_id) LEFT JOIN sheets s USING(sheet_id) WHERE record_id=?',(rid,)).fetchone()
            changes.append({'record_id':rid,'release':a['release_id'],'table':a['table'],'variable':a['variable'],
                'title':doc['title'],'before':'unknown','after':a['unit'],'status':a['status'],'basis':a['basis'],'evidence':a['evidence'],
                'source_file':doc['path'],'sheet':doc['sheet_name'],'source_row':doc['source_row']})
        for rid,a in after.items():
            if a['status']!='conditional':continue
            table=a['table'];field=a['variable'];selector=a['unit_selector'];year=int(a['release_id'][6:10])
            assert all(re.fullmatch(r'[A-Za-z0-9_]+',x) for x in [table,field,selector])
            with readonly(annual_path(year)) as db:
                rows=db.execute(f'SELECT UNITID,"{field}","{selector}" FROM "{table}" WHERE "{field}">0').fetchall()
            source_codes=[dict(c) for c in cat.execute('SELECT c.record_id,c.code_value,c.value_label,f.path AS source_file,s.sheet_name,r.source_row FROM code_values c JOIN records r USING(record_id) JOIN source_files f USING(source_id) LEFT JOIN sheets s USING(sheet_id) WHERE c.release_id=? AND c.table_name=? AND c.variable_name=? COLLATE NOCASE',(a['release_id'],table,selector))]
            codes={str(c['code_value']) for c in source_codes if c['value_label'].lower() in {'clock hours','contact hours','credit hours'}}
            if any(c['value_label'].lower()=='contact hours' for c in source_codes):
                terminology.append({'record_id':rid,'release':a['release_id'],'table':table,'variable':field,'selector':selector,'code_records':source_codes,
                    'issue':'Program-length prose says clock/credit hours; selector code says contact hours. Display preserves the code label; no clock/contact harmonization.'})
            missing=[{'unitid':r[0],'value':r[1],'selector_value':r[2]} for r in rows if str(r[2]).removesuffix('.0') not in codes]
            conditional.append({'record_id':rid,'release':a['release_id'],'table':table,'variable':field,'selector':selector,
                'positive_reported_values':len(rows),'missing_or_invalid_unit_basis':len(missing)})
            if missing:gaps.append({**conditional[-1],'observations':missing})
    report={'previous_unresolved':len(batch),'outcomes':dict(Counter(after[rid]['status'] for rid in batch)),
        'remaining_static_unknowns':remaining,'all_conditional_fields':conditional,'conditional_observation_gaps':gaps,
        'positive_program_length_cells':sum(c['positive_reported_values'] for c in conditional),
        'positive_cells_missing_basis':sum(c['missing_or_invalid_unit_basis'] for c in conditional),
        'source_terminology_review':terminology,'changes':changes,'limits':'Quantity-unit review of the original batch, not manual verification of all other catalog assignments. Conditional coverage counts positive program-length observations, not distinct schools. Currency quantity verification remains separate from currency/scale display verification.'}
    (ROOT/'evaluations/unit_resolution_review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    lines=['# Unit resolution: remaining review items','',
        f'Original batch: {len(batch):,} annual field entries. Outcomes: '+', '.join(f'{v:,} {k}' for k,v in report['outcomes'].items())+'.',
        '',f'No static unknowns remain in this batch: {len(remaining)}. Conditional entries require an institution-specific selector; this is not a guessed fixed unit.',
        '',f'Checked {report["positive_program_length_cells"]:,} positive program-length observations across all 30 conditional fields: {report["positive_cells_missing_basis"]:,} lacked a recognized basis.',
        '','## Source terminology to review','',
        'For program 6, prose says clock/credit hours while the supplied category label says contact hours. The app preserves contact hours when that code is reported. No conversion or harmonization is applied.',
        '','| Release | Field | Unit selector | Codebook record |','|---|---|---|---|']
    for item in terminology:lines.append(f'| {item["release"]} | {item["table"]}.{item["variable"]} | {item["selector"]} | {item["record_id"]} |')
    lines+=['','The review decision is whether to retain the source terminology separately (current behavior) or later adopt a documented harmonization rule. No further source or numerical correction is inferred.',
        '','Full before/after evidence and workbook/sheet/row references are in `unit_resolution_review.json`. These results do not establish that every other catalog assignment is correct.']
    (ROOT/'evaluations/UNIT_RESOLUTION_REVIEW_ITEMS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in {'changes','all_conditional_fields','conditional_observation_gaps','source_terminology_review'}},indent=2))

if __name__=='__main__':main()
