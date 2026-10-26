"""Reader-facing evidence and substantive caveats; full originals stay in audit."""
from pathlib import Path
import re
from .catalog import DATA,readonly

TECHNICAL_PREFIXES=('Source release labels are shown separately from source reporting periods.',
    'Source row domains, missingness policy, join cardinality and typed calculations are retained in the audit.')

def visible_warnings(result):
    assumptions=set(result.get('catalog_plan',{}).get('assumptions',[]))
    output=[]
    for warning in result.get('warnings',[]):
        if ('technical_notes' not in result and warning in assumptions) or warning.startswith(TECHNICAL_PREFIXES):continue
        if warning.startswith('Results use the confirmed reporting institution.'):
            names=list(dict.fromkeys(r['institution'] for r in result['rows']))
            identity=result.get('institution_identity',{})
            mentions=identity.get('original_mentions',[])
            if mentions:
                from .institution_confirmation import needs_reporting_scope_warning,normalized,resolve
                unitids=identity.get('unitids') or list(dict.fromkeys(r.get('unitid') for r in result['rows'] if r.get('unitid')))
                scoped=identity.get('scope_mentions')
                if scoped is None:
                    scoped=[]
                    for text in mentions:
                        selected=identity.get('confirmed_choices',{}).get(normalized(text))
                        if selected in unitids:
                            if needs_reporting_scope_warning(text,selected):scoped.append(text)
                        elif resolve(text,{}) not in unitids and any(needs_reporting_scope_warning(text,uid) for uid in unitids):scoped.append(text)
                if unitids and not scoped:continue
                mentions=scoped or mentions
            if len(names)==1 and len(mentions)==1:warning='Figures are reported by '+names[0]+'; these results do not establish separate figures for '+mentions[0]+'.'
        elif warning.startswith('Complete-case calculations exclude'):warning='This calculation excludes observations with missing values or weights.'
        elif warning.startswith('A source denominator is zero;'):warning='A percentage or ratio could not be calculated because its denominator is zero.'
        if warning not in output:output.append(warning)
    if any(r.get('provisional') for r in result['rows']) and not any('provisional' in w.lower() for w in output):
        output.append('The latest-release figures are provisional and may be revised.')
    if any(r['status']!='ok' for r in result['rows']) and not any(re.search(r'missing|not.reported|not.collected',w,re.I) for w in output):
        output.append('Some requested values are unavailable. Missing values have not been treated as zero.')
    if any(d.get('location_override') for s in result.get('sources',[]) for d in s.get('codebook_evidence',[])):
        output.append('This analysis uses an implementation-reviewed correction to a documented source location. Details are included in the download.')
    return output

def concise(text,limit=300):
    text=re.sub(r'\s+',' ',text).strip()
    text=re.split(r'\b(?:CREDIT\s*[-:]|NOTE[S]?\s*:)',text,maxsplit=1)[0].strip()
    text=text.replace('U.S.','U§S§')
    text=re.split(r'(?<=[.!?])\s+(?=[A-Z])',text,maxsplit=1)[0].replace('U§S§','U.S.')
    if len(text)>limit:text=text[:limit].rsplit(' ',1)[0]+'…'
    return text

def definition_summary(result,metric):
    text=result.get('definitions',{}).get(metric,'')
    parts=[p.strip() for p in re.split(r'\n\s*\n',text) if p.strip() and not p.startswith('Calculation:')]
    return list(dict.fromkeys(concise(p) for p in parts if concise(p)))

def metric_label(result,metric,fallback):
    friendly=fallback
    for source in result.get('sources',[]):
        if source['metric']!=metric:continue
        for doc in source.get('codebook_evidence',[]):
            friendly=re.sub(r'\b'+re.escape(doc['variable_name'])+r'\b',lambda _:doc['title'],friendly)
    if friendly!=fallback:return friendly
    if re.match(r'^[A-Z][A-Z0-9_]{3,}\b',fallback):
        definitions=definition_summary(result,metric)
        if definitions:return definitions[0].split(': ',1)[0]+(' (%)' if next((r['unit'] for r in result['rows'] if r['metric']==metric),'')=='percent' else '')
    return fallback

def documents(result):
    return {d['record_id']:d for s in result.get('sources',[]) for d in s.get('codebook_evidence',[])}

def calculation_summary(result,metric):
    docs=documents(result)
    def name(rid):return docs.get(rid,{}).get('title','selected source value')
    for source in result.get('sources',[]):
        if source['metric']!=metric:continue
        f=source.get('formula')
        if isinstance(f,dict) and f.get('typed_calculation'):
            c=f['typed_calculation'];inputs=[name(rid) for rid in c['input_record_ids']];op=c['operator']
            if op in {'percent','ratio'}:return inputs[0]+' ÷ '+name(c['denominator_record_id'])+(' × 100' if op=='percent' else '')+'.'
            return (' + ' if op=='sum' else ' − ').join(inputs)+'.'
        if isinstance(f,str):
            match=re.fullmatch(r'100(?:\.0)?\*([A-Za-z]\w*)/NULLIF\(([A-Za-z]\w*),0\)',f)
            if match:
                names={d['variable_name']:d['title'] for d in source.get('codebook_evidence',[])}
                if all(v in names for v in match.groups()):return names[match[1]]+' ÷ '+names[match[2]]+' × 100.'
    p=result.get('catalog_plan',{})
    if p.get('version')==2:
        expressions={'x'+e['id']:e for e in p['expressions']}
        aggregates={'a'+s['id']+'_'+a['id']:a for s in p['sources'] for a in s['aggregates']}
        def ref(r,depth=0):
            if depth>4:return 'an intermediate calculation (full formula in download)'
            if re.fullmatch(r'f[a-zA-Z][a-zA-Z0-9_]*_\d+',r):return name(int(r.rsplit('_',1)[1]))
            if r in aggregates:
                a=aggregates[r];op=a['operator'].replace('_',' ')
                return op+' of '+name(a['record_id'])+(' using '+name(a['weight_record_id'])+' as weights' if a.get('weight_record_id') else '')
            if r not in expressions:return 'selected source value'
            e=expressions[r];values=[ref(i,depth+1) for i in e['inputs']];op=e['operator']
            if op in {'add','subtract','multiply','divide','percent','percent_change'}:
                a,b=values
                if op=='percent_change':return '('+a+' − '+b+') ÷ '+b+' × 100'
                return '('+a+{'add':' + ','subtract':' − ','multiply':' × ','divide':' ÷ ','percent':' ÷ '}[op]+b+')'+(' × 100' if op=='percent' else '')
            return op.replace('_',' ')+' of '+values[0]+(' using '+values[1]+' as weights' if op=='weighted_mean' else '')
        if metric in expressions or metric in aggregates:return ref(metric)+'.'
    # Reviewed calculations retain their source documentation without exposing SQL.
    rows=[r for r in result['rows'] if r['metric']==metric]
    if rows and any(r.get('numerator') is not None and r.get('denominator') is not None for r in rows):
        return 'Numerator ÷ denominator'+(' × 100.' if rows[0]['unit']=='percent' else '.')
    return None

def _table_metadata(keys):
    """Read table-level codebook rows for exact executed release/table pairs."""
    with readonly(DATA/'metadata_catalog.sqlite') as db:
        return {key:[dict(r) for r in db.execute('''SELECT table_name,survey,year_coverage,title FROM table_docs
            WHERE release_id=? AND table_name=? COLLATE NOCASE ORDER BY record_id''',key)] for key in keys}


def source_summary(result):
    executed={}
    for source in result.get('sources',[]):
        release=Path(source['database']).parent.name
        table=source['table']
        executed.setdefault((release,table.casefold()),table)
    keys=sorted(executed)
    metadata=_table_metadata(keys) if keys else {}
    rows=[];groups={};notes=[]
    for key in keys:
        release,_=key;table=executed[key];docs=metadata.get(key,[])
        documented_names=list(dict.fromkeys(d['table_name'] for d in docs if d.get('table_name')))
        if len(documented_names)==1:table=documented_names[0]
        release_label=release.removeprefix('IPEDS_').replace('_',' · ')
        release_label=re.sub(r'(?<=\d)-(?=\d)','–',release_label)
        fields={}
        for field in ['survey','year_coverage','title']:
            values=list(dict.fromkeys(str(d.get(field) or '').strip() for d in docs if str(d.get(field) or '').strip()))
            if len(values)==1:fields[field]=values[0]
            elif len(values)>1:
                fields[field]='Conflicting metadata'
                notes.append(release_label+' · '+table+': conflicting '+{'survey':'survey names','year_coverage':'year coverage','title':'table titles'}[field]+' — '+'; '.join(values)+'.')
            else:fields[field]='Not documented'
        if not docs:notes.append(release_label+' · '+table+': table-level source metadata is unavailable.')
        elif any(v=='Not documented' for v in fields.values()):notes.append(release_label+' · '+table+': some table-level source metadata is not documented.')
        title=fields['title']
        if title=='Not documented':title='Table description not documented'
        elif title=='Conflicting metadata':title='Conflicting source table descriptions'
        elif fields['year_coverage'] not in {'Not documented','Conflicting metadata'}:
            # Strip only the exact documented period suffix, shown separately
            # in its own column. Do not invent a shared title or reporting year.
            title=re.sub(r'\s*[:;—–-]?\s*'+re.escape(fields['year_coverage'])+r'\s*$', '',title,flags=re.I).strip(' :;,—–-') or fields['title']
        row={'IPEDS release':release_label,'Survey':fields['survey'],'Year coverage':fields['year_coverage'],'Table':table}
        rows.append(row)
        groups.setdefault(title,[]).append(row)
    return {'sources':rows,'source_groups':[{'title':title,'rows':items} for title,items in groups.items()],
            'source_notes':list(dict.fromkeys(notes))}


def evidence_summary(result):
    institutions=list(dict.fromkeys(r['institution'] for r in result['rows']))
    periods=list(dict.fromkeys(r['reporting_period'] for r in result['rows']))
    population=[]
    for s in result.get('sources',[]):
        for c in s.get('code_filters',[]):
            label=c.get('title') or c.get('value_label')
            if label and label not in population:population.append(label)
    return {'institutions':institutions,'periods':periods,'population':population,**source_summary(result)}
