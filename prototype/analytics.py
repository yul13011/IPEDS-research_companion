"""Validate plans against annual evidence, compile trusted mappings, query read-only."""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from functools import lru_cache
from .catalog import BASE, DATA, readonly, annual_path, evidence, evidence_hash, institutions

REGISTRY = BASE/'measure-registry'/'reviewed_measures.json'


def measures():
    return {m['id']:m for m in json.loads(REGISTRY.read_text(encoding='utf-8'))['measures']}


@dataclass
class Plan:
    metrics: list
    institutions: list
    years: list
    time_basis: str = 'observation'
    output: str = 'table'

    def validate(self):
        specs=measures()
        if not isinstance(self.metrics,list) or not 1<=len(self.metrics)<=12 or any(m not in specs for m in self.metrics):
            raise ValueError('Choose 1–12 reviewed measures for this executor. Other source fields use catalog-driven proposed plans; this route cannot execute them.')
        if not isinstance(self.institutions,list) or not self.institutions or any(not isinstance(x,str) or not x.strip() for x in self.institutions):
            raise ValueError('Specify an institution or Ivy League; no institution is assumed.')
        if not isinstance(self.years,list) or not 1<=len(self.years)<=10 or any(type(y) is not int for y in self.years):
            raise ValueError('Select 1–10 integer years.')
        if self.time_basis not in {'observation','entry_cohort','class'} or self.output not in {'table','chart','export','answer'}:
            raise ValueError('Unsupported time basis or output.')
        families={specs[m]['family'] for m in self.metrics}
        if self.time_basis=='entry_cohort' and not families<={'graduation','pell'}:
            raise ValueError('Entering-cohort time is only supported for six-year graduation measures.')
        if self.time_basis=='class' and not families<={'admissions','sat'}:
            raise ValueError('Class-of means a nominal four-year class, supported here only for first-year admissions/SAT.')
        if len(set(self.metrics))!=len(self.metrics) or len(set(self.years))!=len(self.years):
            raise ValueError('Duplicate measures or years are not permitted.')
        observations=[y+(6 if self.time_basis=='entry_cohort' else -4 if self.time_basis=='class' else 0) for y in self.years]
        if any(y<2015 or y>2024 for y in observations):
            raise ValueError(f'Request needs observation year(s) {observations}. Available: 2015–2024. No substitute year was used.')
        return observations


def _identifier(name):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',name):raise ValueError('Invalid registry identifier')
    return '"'+name+'"'


def compile_query(spec,mapping,unitid):
    table=_identifier(mapping['table'])
    if spec.get('ratio_rows'):
        col=_identifier(spec['value_column'])
        return (f'SELECT 100.0*n.{col}/NULLIF(d.{col},0) AS value,n.{col} AS numerator,d.{col} AS denominator '
                f'FROM {table} n JOIN {table} d ON n.UNITID=d.UNITID AND d.GRTYPE=8 '
                'WHERE n.UNITID=? AND n.GRTYPE=12',[unitid])
    # Expressions are versioned application configuration, never user/model SQL.
    expr=spec['expression']
    if not re.fullmatch(r'[A-Za-z0-9_.*+/(), -]+',expr):raise ValueError('Invalid registry expression')
    extras=''
    if spec.get('numerator'):
        extras=f",{_identifier(spec['numerator'])} AS numerator,{_identifier(spec['denominator'])} AS denominator"
    elif spec['family']=='pell' and spec['id'].endswith('_rate'):
        if spec['id'].startswith('nonpell'):extras=',SSCMBAC+NRCMBAC AS numerator,SSADJCT+NRADJCT AS denominator'
        else:extras=',PGCMBAC AS numerator,PGADJCT AS denominator'
    where=['UNITID=?'];params=[unitid]
    for col,value in spec['filters'].items():
        where.append(_identifier(col)+'=?');params.append(value)
    return f'SELECT {expr} AS value{extras} FROM {table} WHERE '+ ' AND '.join(where),params


@lru_cache(maxsize=1)
def _benchmark_records():
    path=BASE/'evaluations'/'results'/'yale_cases.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else []


def benchmark_notes(metric,year,unitid):
    if unitid!=130794:return []
    names={'applicants':'Total Applications','admits':'Total Admits','matriculants':'Total Matrics',
           'admission_rate':'Admit Rate','yield_rate':'Yield Rate','graduate_enrollment':'Graduate/Professional',
           'total_enrollment':'Total','undergraduate_enrollment':'Undergraduate'}
    key=names.get(metric,metric)
    if metric.startswith(('satvr','satmt')):key=('Verbal_' if metric.startswith('satvr') else 'Math_')+metric[-2:]
    records=_benchmark_records()
    return [f"Yale reference discrepancy: {r['metric']} in {year}: IPEDS {r['actual']}, reference {r['expected']} (benchmark rate values use fractions, not percent). Cause remains unresolved."
            for r in records if r['observation_year']==year and r['metric']==key and r['status']=='mismatch']


def execute(plan):
    from .intent_checks import check_plan,stamp
    from .progress import report
    report('Validating selections and source definitions…')
    observations=plan.validate();specs=measures();rows=[];sources=[];warnings=[];definitions={};technical_notes=[]
    intent_check=check_plan(asdict(plan))
    registry_hash=sha256(REGISTRY.read_bytes()).hexdigest()
    # All mappings and source definitions are checked before any analytical query.
    prepared=[]
    with readonly(DATA/'metadata_catalog.sqlite') as cat:
        for year in sorted(observations):
            path=annual_path(year);release=path.parent.name
            for metric in plan.metrics:
                spec=specs[metric];definitions[metric]=spec['definition']
                mapping=spec['annual'].get(str(year))
                if mapping is None:
                    prepared.append((year,path,metric,spec,None,None));continue
                if mapping['release']!=release:raise ValueError('Registry release differs from annual database; re-review mapping.')
                docs=evidence(cat,release,mapping['table'],spec['columns'])
                if [d['record_id'] for d in docs]!=mapping['definition_record_ids']:
                    raise ValueError('Codebook evidence changed; registry needs review.')
                if evidence_hash(docs)!=mapping['evidence_sha256']:
                    raise ValueError('Codebook definition content changed; registry needs review.')
                for code in mapping['code_evidence']:
                    actual=cat.execute('SELECT code_value,value_label FROM code_values WHERE record_id=?',(code['record_id'],)).fetchone()
                    if not actual or dict(actual)!={k:code[k] for k in ('code_value','value_label')}:
                        raise ValueError('Categorical definition changed; registry needs review.')
                prepared.append((year,path,metric,spec,mapping,docs))
    for year,path,metric,spec,mapping,docs in prepared:
        report(f'Reading source data for {year}…')
        ids=institutions(plan.institutions,year)
        with readonly(path) as db:
            for unitid in ids:
                names=db.execute(f'SELECT INSTNM FROM HD{year} WHERE UNITID=?',(unitid,)).fetchall()
                if len(names)!=1:raise ValueError(f'Institution {unitid} is not uniquely reported in {year}.')
                row={'institution':names[0][0],'unitid':unitid,'observation_year':year,
                     'entry_cohort_year':year-6 if spec['family'] in {'graduation','pell'} else None,
                     'reporting_period':f'{year-1}–{str(year)[-2:]}' if spec['family'] in {'aid','completions'} else f'fall {year}' if spec['family'] in {'admissions','sat','enrollment'} else f'six-year outcome {year}',
                     'metric':metric,'measure':spec['label'],'unit':spec['unit'],'value':None,
                     'release':path.parent.name,'provisional':'Provisional' in path.parent.name,
                     'status':'not_collected','numerator':None,'denominator':None,
                     'series_segment':'pre-2017 SAT protocol' if spec['family']=='sat' and year<2017 else '2017+ SAT protocol' if spec['family']=='sat' else 'comparable scope'}
                if mapping:
                    from .unit_metadata import resolve
                    row['unit_metadata']=resolve({'title':spec['label'],'long_description':spec['definition'],'release_id':mapping['release'],
                        'table_name':mapping['table'],'variable_name':metric},reviewed_unit=spec['unit'])
                    row['unit_metadata']['definition_record_ids']=mapping['definition_record_ids']
                    sql,params=compile_query(spec,mapping,unitid)
                    values=db.execute(sql,params).fetchmany(3)
                    if len(values)>1:raise ValueError(f'Duplicate records: {metric}, {year}, {unitid}; result blocked.')
                    row['status']='missing'
                    if values:
                        record=dict(values[0]);value=record['value']
                        row['numerator']=record.get('numerator');row['denominator']=record.get('denominator')
                        if value is not None:
                            value=float(value)
                            valid=value>=0 and (spec['unit']!='percent' or value<=100)
                            if spec['unit']=='score':valid=200<=value<=800
                            if row['denominator'] is not None:
                                valid=valid and row['denominator']>0 and 0<=row['numerator']<=row['denominator']
                            if not valid:raise ValueError(f'Invalid count/rate/score: {metric}, {year}, {unitid}.')
                            row.update(value=value,status='ok')
                    sources.append({'metric':metric,'year':year,'unitid':unitid,'database':str(path),
                        'database_size':path.stat().st_size,'database_mtime_ns':path.stat().st_mtime_ns,
                        'table':mapping['table'],'columns':spec['columns'],'filters':spec['filters'],
                        'formula':spec['expression'],'sql':sql,'parameters':params,'codebook_evidence':docs,
                        'code_filters':mapping['code_evidence'],'location_overrides':mapping['location_overrides']})
                    warnings.extend(benchmark_notes(metric,year,unitid))
                if row['status']!='ok':warnings.append(f"{row['institution']}, {year}, {row['measure']}: {row['status']}; not treated as zero.")
                rows.append(row)
    if any(r['provisional'] for r in rows):warnings.append('2024–25 is provisional; values may be revised.')
    if any(specs[m]['family']=='sat' for m in plan.metrics):
        technical_notes.append(specs[next(m for m in plan.metrics if specs[m]['family']=='sat')]['definition'])
        if min(observations)<2017<=max(observations):warnings.append('SAT reporting changed in 2017. Trend segments on either side are not directly comparable.')
    if 'undergraduate_grant_percent' in plan.metrics:technical_notes.append(specs['undergraduate_grant_percent']['definition'])
    if plan.time_basis=='class':warnings.append('Class-of was interpreted as fall entry four years earlier; it is a nominal class label, not an observed graduation cohort.')
    payload={'plan':asdict(plan),'observation_years':observations,'rows':rows,'sources':sources,
             'warnings':list(dict.fromkeys(warnings)),'technical_notes':technical_notes,'definitions':definitions,
             'created_at':datetime.now(timezone.utc).isoformat(),'registry_sha256':registry_hash,
             'coverage':{'requested_cells':len(rows),'available_cells':sum(r['status']=='ok' for r in rows)},
             'review_status':'Implementation-reviewed source mappings; retained Yale benchmark discrepancies are disclosed, not resolved.'}
    payload['result_id']=sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:16]
    return stamp(payload,intent_check)
