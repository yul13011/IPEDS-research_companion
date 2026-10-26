"""Build explicit annual mappings from verified local metadata; never modify sources.

Implementation review is distinct from project-owner approval and benchmark agreement.
Run from agent-redesign: python -m prototype.build_registry
"""
import json
from .catalog import BASE, DATA, readonly, annual_path, evidence, evidence_hash


def definitions():
    out = []
    def add(id, label, family, unit, columns, expression, filters=None, **extra):
        out.append(dict(id=id,label=label,family=family,unit=unit,columns=columns,
                        expression=expression,filters=filters or {},**extra))
    for id,label,col in [('applicants','Applicants','APPLCN'),('admits','Admitted students','ADMSSN'),('matriculants','Enrolled first-year students','ENRLT')]:
        add(id,label,'admissions','students',[col],col)
    add('admission_rate','Admission rate','admissions','percent',['ADMSSN','APPLCN'],'100.0*ADMSSN/NULLIF(APPLCN,0)',numerator='ADMSSN',denominator='APPLCN')
    add('yield_rate','Yield rate','admissions','percent',['ENRLT','ADMSSN'],'100.0*ENRLT/NULLIF(ADMSSN,0)',numerator='ENRLT',denominator='ADMSSN')
    for prefix,section in [('SATVR','SAT reading/verbal'),('SATMT','SAT math')]:
        for pct in [25,50,75]:
            col=f'{prefix}{pct}'
            add(col.lower(),f'{section}, {pct}th percentile','sat','score',[col],col,start=2022 if pct==50 else 2015)
    for id,label,col,unit in [('sat_submitters','SAT submitters','SATNUM','students'),('sat_submission_percent','SAT submission percentage','SATPCT','percent')]:
        add(id,label,'sat',unit,[col],col)
    for id,label,level in [('undergraduate_enrollment','Undergraduate enrollment',20),('graduate_enrollment','Graduate enrollment',50),('total_enrollment','Total enrollment',10)]:
        add(id,label,'enrollment','students',['EFTOTAL','EFLEVEL'],'EFTOTAL',{'EFLEVEL':level})
    for prefix,label,col in [('', 'All', 'GRTOTLT'),('men_', 'Men', 'GRTOTLM'),('women_', 'Women', 'GRTOTLW'),('nonresident_', 'U.S. nonresident', 'GRNRALT')]:
        for suffix,title,grtype in [('cohort','adjusted bachelor cohort',8),('completers','six-year bachelor completers',12)]:
            add(prefix+'graduation_'+suffix,f'{label}: {title}','graduation','students',[col,'GRTYPE'],col,{'GRTYPE':grtype})
        add(prefix+'graduation_rate',f'{label}: six-year bachelor graduation rate','graduation','percent',[col,'GRTYPE'],f'100.0*n.{col}/NULLIF(d.{col},0)',ratio_rows=True,value_column=col)
    for prefix,label in [('pell','Pell recipients'),('nonpell','Non-Pell students')]:
        den='PGADJCT' if prefix=='pell' else 'SSADJCT+NRADJCT'
        num='PGCMBAC' if prefix=='pell' else 'SSCMBAC+NRCMBAC'
        for suffix,title,expr,unit in [('cohort','adjusted bachelor cohort',den,'students'),('completers','six-year bachelor completers',num,'students'),('rate','six-year bachelor graduation rate',f'100.0*({num})/NULLIF(({den}),0)','percent')]:
            import re
            cols=[c for c in dict.fromkeys(re.findall(r'\b[A-Z][A-Z0-9]+\b',expr)) if c != 'NULLIF']+['PSGRTYPE']
            add(prefix+'_graduation_'+suffix,f'{label}: {title}','pell','percent' if suffix=='rate' else unit,cols,expr,{'PSGRTYPE':2},start=2016)
    add('bachelors_degrees',"Bachelor's degrees awarded",'completions','degrees',['CTOTALT','AWLEVEL','CIPCODE','MAJORNUM'],'CTOTALT',{'AWLEVEL':5,'CIPCODE':'99','MAJORNUM':1})
    add('undergraduate_grant_percent','Undergraduates awarded grants/scholarships','aid','percent',['UAGRNTN','SCUGRAD','UAGRNTP'],'100.0*UAGRNTN/NULLIF(SCUGRAD,0)',numerator='UAGRNTN',denominator='SCUGRAD')
    return out


NOTES = {
 'admissions': 'First-time degree/certificate-seeking undergraduates for fall, including prior-summer entrants; not graduate admissions. Rates use raw counts, not rounded derived percentages.',
 'sat': 'Enrolled first-time degree/certificate-seeking undergraduate SAT submitters, including prior-summer entrants; not all applicants or all first-year students. SAT scale/protocol changes in 2017: do not join pre-2017 and 2017+ score lines. Yale reference score treatment remains unresolved.',
 'enrollment': 'Fall credit headcount as of the official fall reporting date/October 15. Graduate is the IPEDS graduate category, which may differ from a local graduate/professional snapshot.',
 'graduation': 'First-time full-time bachelor-seeking adjusted cohort; bachelor completers within six years / adjusted cohort after exclusions. Observation year is entering cohort + 6. U.S. nonresident is not a general foreign-born category. No custom URM grouping is approved.',
 'pell': 'Bachelor subcohort, PSGRTYPE=2. Non-Pell combines subsidized-loan-only and neither-Pell-nor-subsidized-loan categories. Not available for 2015 outcomes. Observation year = entry + 6.',
 'completions': 'Awards July 1 of the preceding year through June 30 of the observation year. All-program total (CIPCODE=99), bachelor level (5), first major (1); second majors are not extra degrees. Program-level CIP trends are outside this mapping.',
 'aid': 'Grant/scholarship aid from all known sources for the SFA all-undergraduate cohort, not any aid including loans and not only entering first-time students. Aid reporting period ends in the collection start year (SFA2324 in the 2024–25 release refers to 2023–24). Term reporters use a fall cohort; program reporters use a full-year cohort, so populations differ across calendar systems. 2023 documentation has an SFA table-location correction; source definitions are preserved. This mapping has not been compared with a user-supplied longitudinal aid benchmark.'
}


def build():
    measures = definitions()
    with readonly(DATA/'metadata_catalog.sqlite') as db:
        for spec in measures:
            spec.update(version=1,review_status='implementation_reviewed',owner_approval='not_requested',
                        definition=NOTES[spec['family']],annual={})
            for year in range(spec.get('start',2015),2025):
                path=annual_path(year);release=path.parent.name
                family=spec['family']
                table={'admissions':f'ADM{year}','sat':f'ADM{year}','enrollment':f'EF{year}',
                       'graduation':f'GR{year}','pell':f'GR{year}_PELL_SSL','completions':f'C{year}_A'}.get(family)
                if family=='aid':
                    candidates=[r[0] for r in db.execute("SELECT table_name FROM physical_columns WHERE release_id=? AND column_name='UAGRNTN' AND table_name LIKE 'sfa%'",(release,))]
                    if len(candidates)!=1:raise ValueError(f'Unexpected SFA locations: {candidates}')
                    table=candidates[0]
                docs=evidence(db,release,table,spec['columns'])
                # Ensure every categorical selection has annual source labels.
                required=dict(spec['filters'])
                if spec.get('ratio_rows'):required={'GRTYPE':8}
                code_evidence=[]
                for col,value in required.items():
                    item=next(d for d in docs if d['variable_name'].upper()==col)
                    matched=[x for x in item['codes'] if str(x['code_value'])==str(value)]
                    if not matched:raise ValueError(f'Missing annual code definition: {year} {table} {col}={value}')
                    code_evidence.extend(matched)
                if spec.get('ratio_rows'):
                    item=next(d for d in docs if d['variable_name'].upper()=='GRTYPE')
                    code_evidence.extend(x for x in item['codes'] if str(x['code_value'])=='12')
                    if len(code_evidence)!=2:raise ValueError('Missing bachelor completion code')
                spec['annual'][str(year)]={'release':release,'table':table,
                    'definition_record_ids':[d['record_id'] for d in docs], 'evidence_sha256':evidence_hash(docs), 'code_evidence':code_evidence,
                    'location_overrides':[dict(column=d['variable_name'],documented_table=d['documented_table'],physical_table=table,record_id=d['record_id']) for d in docs if d['location_override']]}
    payload={'registry_version':1,'review_basis':'Local annual codebook definitions + physical schemas/categorical labels + Yale retrieval evaluation. Implementation review, not owner approval or a claim that all benchmarks agree.',
             'unsupported':['Custom URM/Non-URM until unknown-race rule resolved','National graduation aggregation until missing-count/reporting-unit rules reviewed','SAT 10th/90th percentiles','Graduate admissions','Unmapped measures: discovery only'],
             'measures':measures}
    target=BASE/'measure-registry'/'reviewed_measures.json'
    target.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f'Wrote {len(measures)} measures / {sum(len(s["annual"]) for s in measures)} annual mappings to {target}')


if __name__=='__main__':build()
