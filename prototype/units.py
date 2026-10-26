"""Source-backed display units. Never rescale values or change analytical units."""
from copy import deepcopy
import re

MONEY={'monetary amount','dollars','USD','USD (thousands)','USD (millions)'}
UNVERIFIED='Currency/scale unverified'
# Reviewed IPEDS reporting conventions, applied only to documented monetary
# fields in these source families. A model-authored label is never evidence.
RULES=[
    (r'SAL\d{4}_(?:IS|NIS)', 'https://nces.ed.gov/ipeds/use-the-data/download-survey-material/2024/human%20resources/package_1_44.pdf'),
    (r'F\d{4}_F[123]A?', 'https://nces.ed.gov/ipeds/use-the-data/download-survey-material/2023/finance/package_5_12.pdf'),
    (r'COST[12]_\d{4}', 'https://nces.ed.gov/ipeds/use-the-data/download-survey-material/2024/cost%20i/package_11_73.pdf'),
    (r'IC\d{4}_AY', 'https://ceds.ed.gov/connectReport.aspx?uid=31034'),
    (r'SFA\d{4}(?:_P[12])?', 'https://nces.ed.gov/ipeds/use-the-data/download-survey-material/2024/student%20financial%20aid/package_7_20.pdf'),
]


def is_currency(unit):
    return unit in {'dollars','USD','USD (thousands)','USD (millions)'}


def currency_text(value,unit,decimals=2):
    text=f'{value:,.{decimals}f}'
    if decimals:text=text.rstrip('0').rstrip('.')
    return '$'+text+({'USD (thousands)':' thousand','USD (millions)':' million'}.get(unit,''))


def unit_title(unit):
    return {'USD':'US dollars (USD)','dollars':'US dollars (USD)',
            'USD (thousands)':'Thousands of US dollars (USD)',
            'USD (millions)':'Millions of US dollars (USD)',
            'monetary amount':UNVERIFIED}.get(unit,unit)


def monetary_evidence(row,result):
    """Resolve actual executed source evidence, including legacy saved results."""
    if row.get('unit') not in MONEY:return None
    docs=[(s,d) for s in result.get('sources',[]) if s.get('metric')==row['metric']
          and s.get('year')==row.get('observation_year')
          and (row.get('unitid') is None or s.get('unitid') in {None,row['unitid']})
          for d in s.get('codebook_evidence',[])]
    candidates=[];conflict=False
    def currency_ids(meta):
        ids={meta['record_id']} if meta.get('quantity_type')=='currency' and meta.get('status')=='verified' and meta.get('record_id') else set()
        for item in meta.get('inputs',[]):ids.update(currency_ids(item))
        return ids
    proven_ids=currency_ids(row.get('unit_metadata',{}))
    for source,doc in docs:
        title=doc.get('title','');text=title+' '+doc.get('long_description','')
        if doc.get('record_id') not in proven_ids and not re.search(r'\b(salary|salaries|wages|tuition|fees?|expenses?|expenditures?|revenues?|assets?|liabilities|amount|dollars?)\b',title,re.I):continue
        # Percentages and ratios in a financial table are not currency evidence.
        if re.search(r'percent|percentage|ratio',title,re.I):continue
        million=bool(re.search(r'\bin millions?\b|\bmillions?(?: of)? (?:U\.?S\.? )?dollars\b|\bUSD\s*\(millions?\)',text,re.I))
        thousand=bool(re.search(r'\bin thousands?\b|\bthousands?(?: of)? (?:U\.?S\.? )?dollars\b|\$\s*0{3}\b|\bUSD\s*\(thousands?\)',text,re.I))
        scale=1000000 if million else 1000 if thousand else 1
        if million and thousand:conflict=True
        explicit=bool(re.search(r'\b(?:U\.?S\.? dollars|USD|dollars?)\b|\$',text,re.I))
        # Foreign currencies must not inherit a US reporting convention.
        if re.search(r'\b(?:Canadian|Australian|euros?|pounds sterling|CAD|AUD|EUR)\b',text,re.I):
            conflict=True;continue
        policy=next((url for pattern,url in RULES if re.fullmatch(pattern,source.get('table',''),re.I)),None)
        if explicit or policy:
            candidate={'currency':'USD','scale':scale,'record_id':doc.get('record_id'),
                               'table':source.get('table'),'variable':doc.get('variable_name'),
                               'basis':'Field dollar definition' if explicit else 'Reviewed IPEDS reporting convention',
                               'reference':policy,'source_title':title}
            if candidate not in candidates:candidates.append(candidate)
    pairs={(e['currency'],e['scale']) for e in candidates}
    if len(pairs)==1 and not conflict:
        currency,scale=next(iter(pairs))
        return {'unit':{1:'USD',1000:'USD (thousands)',1000000:'USD (millions)'}[scale],
                'currency':currency,'scale':scale,'evidence':candidates}
    # Reviewed measure mappings already carry an explicit dollar unit.
    if not docs and not conflict and row['unit']=='dollars':
        return {'unit':'USD','currency':'USD','scale':1,'evidence':[{'basis':'Existing reviewed dollar unit'}]}
    return {'unit':UNVERIFIED,'currency':None,'scale':None,'evidence':candidates}


def display_result(result):
    """A presentation copy: originals, calculations and saved results stay intact."""
    out={**result,'rows':[],'display_units':[]}
    for row in result['rows']:
        r=dict(row)
        if r.get('result_type') in {'categorical','text','identifier','bounded'}:
            out['rows'].append(r);continue
        # Idempotent for a presentation copy passed through several renderers.
        if 'source_unit' in r:
            out['rows'].append(r);continue
        from .unit_metadata import restore_direct
        assignment=restore_direct(r,result)
        if assignment:
            r['unit_metadata']=assignment
            if r['unit']!=assignment['unit']:
                r['source_unit']=r['unit'];r['unit']=assignment['unit']
                out['display_units'].append({'metric':r['metric'],'year':r.get('observation_year'),'unit':r['unit'],
                    'basis':'Source-verified unit migration; values unchanged','unit_metadata':assignment})
        from .unit_observations import resolve_row
        row_assignment=resolve_row(r)
        if row_assignment:
            r['source_unit']=r.get('source_unit',r['unit']);r['unit']=row_assignment['unit'];r['unit_metadata']=row_assignment
            out['display_units'].append({'metric':r['metric'],'year':r.get('observation_year'),'unit':r['unit'],'unit_metadata':row_assignment})
        info=monetary_evidence(r,result)
        if info:
            r.update(source_unit=r.get('source_unit',r['unit']),unit=info['unit'],currency=info['currency'],currency_scale=info['scale'])
            entry={'metric':r['metric'],'year':r.get('observation_year'),**info}
            if entry not in out['display_units']:out['display_units'].append(entry)
        out['rows'].append(r)
    if result.get('display_units'):out['display_units']=deepcopy(result['display_units'])
    return out
