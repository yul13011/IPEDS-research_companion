"""Independent request → plan → result checks. Never calculates or invents data."""
from contextvars import ContextVar
from copy import deepcopy
import re
from .time_scope import trend_years,is_trend_followup,WORDS

CURRENT=ContextVar('ipeds_request_contract',default=None)

class IntentMismatch(ValueError):pass

def contract(question,resolved=None,bundle=None,resolution=None):
    bundle=bundle or {};active=bundle.get('active_analysis') or {}
    refs=(resolution or {}).get('referenced_turns',[])
    if len(refs)==1:active=next((t for t in bundle.get('recent_turns',[]) if t['turn']==refs[0]),active)
    plan=active.get('plan') or {};q=question.lower()
    named=re.fullmatch(r'(?:now|what about|how about|add)\s+(.+?)[?.!]?',question.strip(),re.I)
    replacement=_ids([named[1]]) if named else []
    continuation=is_trend_followup(question) or bool(re.fullmatch(r'(?:please )?(?:show|as|use)\s+percentages?[?.!]?',q.strip())) or bool(replacement)
    scope=(active.get('interpreted_question') or active.get('question',''))+'; '+question if continuation else question
    basis='entry_cohort' if re.search(r'entering cohorts?|cohort (?:of |entering )?\d{4}|year of entry|students who (?:started|entered)|started college',scope,re.I) else 'class' if re.search(r'class (?:of )?\d{4}',scope,re.I) else plan.get('time_basis','observation') if continuation else 'observation'
    cls=re.search(r'class (?:of )?(\d{4})',question,re.I);fall=re.search(r'(?:fall|entering)\s+(\d{4})',question,re.I)
    same_class_fall=bool(cls and fall and int(cls[1])-4==int(fall[1]))
    if same_class_fall:basis='observation'
    prior=plan.get('years') or plan.get('source_years')
    end=2018 if basis=='entry_cohort' else 2028 if basis=='class' else 2024
    window=trend_years(question,default_end=end,previous_years=prior)
    # Count the requested observations separately from the date-window binder:
    # an off-by-one error in that shared binder must not validate itself.
    number=r'(\d{1,2}|'+ '|'.join(WORDS)+r')'
    duration=re.search(r'\b'+number+r'[\s\-–‑]+year[\s\-–‑]+(?:longitudinal[\s\-–‑]+)?trend\b',question,re.I) or re.search(r'\b(?:past|last|over(?: the)?|for(?: the)?)\s+'+number+r'[\s\-–‑]+(?:(?:fall|academic|fiscal)\s+)?(?:years?|terms?)\b',question,re.I)
    count=(int(duration[1]) if duration[1].isdigit() else WORDS[duration[1].casefold()]) if duration else None
    temporal=bool(re.search(r'\btrend\b|longitudinal|over time',question,re.I))
    comparison=bool(re.search(r'percent(?:age)? change|difference between|change between',question,re.I)) and not temporal
    explicit=list(dict.fromkeys(int(y) for y in re.findall(r'\b(?:19|20)\d{2}\b',question)))
    if same_class_fall:explicit=[int(fall[1])]
    period=bool(re.search(r'\b(?:19|20)\d{2}\s*[-–/]\s*\d{2}\b',question))
    academic=bool(re.search(r'grants?|scholarships?|financial aid|degrees?|awards?|academic|fiscal',scope,re.I))
    period_ends=[]
    if academic:
        for start,finish in re.findall(r'\b((?:19|20)\d{2})\s*[-–/]\s*((?:19|20)\d{2}|\d{2})\b',question):
            a=int(start);b=int(finish) if len(finish)==4 else a//100*100+int(finish)
            if b==a+1:period_ends.append(b)
    if period_ends:
        window=list(range(period_ends[0],period_ends[-1]+1)) if len(period_ends)>1 and re.search(r'through|\bto\b|between',question,re.I) else period_ends
        period=True
    if academic and len(explicit)==2 and explicit[1]==explicit[0]+1 and re.search(r'july|june|academic year|fiscal year',question,re.I):window=[explicit[1]]
    if window is None and explicit and not period:
        window=list(range(explicit[0],explicit[1]+1)) if not comparison and len(explicit)==2 and re.search(r'\bthrough\b|\bto\b|\bbetween\b|\d{4}\s*[-–]\s*\d{4}',question,re.I) else explicit
    if window is None and continuation:window=prior
    if comparison and window:window=sorted({min(window),max(window)})
    if window and len(window)>1 and not comparison and not re.search(r'\b(sum|pooled|combined|cumulative|average across years)\b',question,re.I):temporal=True
    from .institution_confirmation import AUTHORIZED
    authorized=AUTHORIZED.get()
    ids=[int(x) for x in re.findall(r'\b\d{6}\b',question) if authorized is None or int(x) in authorized]
    ids=_ids(list(map(str,ids)))
    if re.search(r'\bivy\b|\bivies\b',question,re.I):
        from .catalog import IVY
        ids+=list(IVY)
    if not ids:ids=replacement
    if not ids and continuation:ids=_ids(plan.get('institutions',[])) or list((active.get('institution_identity') or {}).get('unitids',[]))
    if re.match(r'\s*(?:add|also include|include also)\b',question,re.I):ids+=_ids(plan.get('institutions',[]))
    for excluded in re.findall(r'\b(?:except|excluding|without)\s+(\d{6})\b',question,re.I):ids=[uid for uid in ids if uid!=int(excluded)]
    gender=bool(re.search(r'by (?:gender|sex)|(?:gender|sex)\s+(?:breakdown|distribution)|breakdown\s+(?:by |of )?(?:gender|sex)',scope,re.I))
    race=bool(re.search(r'race|ethnic',scope,re.I) and re.search(r'by |breakdown|distribution',scope,re.I))
    return dict(version=1,original_question=question,scope_question=scope,expected_years=window,time_basis=basis,
        temporal=temporal,period_count=count,
        unitids=sorted(set(ids)),inherit_institutions=continuation,
        dimensions=[name for name,required in [('gender',gender),('race',race)] if required],
        percentage=bool(re.search(r'\bpercent(?:age)?s?\b|\bshares?\b|\bproportions?\b',scope,re.I)) and not bool(re.search(r'percentage change|percent change',scope,re.I)),
        undergraduate=bool(re.search(r'undergrad',scope,re.I)))

def _ids(names):
    from .institution_confirmation import resolve
    from .catalog import IVY
    found=[]
    for name in names:
        if str(name).casefold() in {'ivy','ivies','ivy league'}:found.extend(IVY);continue
        uid=resolve(str(name),{})
        # Reviewed executor aliases are also valid when the identity layer has
        # already confirmed that exact ID. Do not silently discard "Brown" or
        # "Columbia" from an otherwise verified institutional group.
        if uid is None:
            from .catalog import ALIASES
            from .institution_confirmation import AUTHORIZED
            candidate=ALIASES.get(str(name).strip().casefold())
            if candidate is not None and candidate in (AUTHORIZED.get() or set()):uid=candidate
        if uid is not None:found.append(uid)
    return sorted(set(found))

def _check_institutions(actual,c):
    expected=set(c['unitids'])
    if expected and not expected<=set(actual):raise IntentMismatch('The plan does not include every requested institution. Please restate which institutions to include.')
    if expected and set(actual)!=expected:raise IntentMismatch('The institutions differ from the requested scope. Please confirm the intended institutions.')

def _field_info(plan,evidence):
    """Use selected source definitions/category evidence, never generated output labels."""
    evidence=evidence or {};defs=evidence.get('definition_evidence',[])
    byid={d['record_id']:d for d in defs}
    selected={s['record_id'] for s in plan.get('selections',[]) if s['role']=='measure'}
    groups=set(plan.get('group_by_record_ids',[]))
    if plan.get('version')==2:
        selected={rid for s in plan['sources'] for rid in s['field_record_ids']}
        groups={rid for s in plan['sources'] for rid in s['group_by_record_ids']}
    titles=[str(byid[r].get('title','')) for r in selected if r in byid]
    group_titles=[str(byid[r].get('title','')) for r in groups if r in byid]
    categories=' '.join(str(d.get('title','')) for d in evidence.get('category_evidence',[]))
    return titles,group_titles,categories

def check_plan(plan,question='',evidence=None):
    c=CURRENT.get()
    if c is None:return None
    from .progress import report
    report('Checking the planned scope against your request…')
    checks=[];_check_institutions(_ids(plan.get('institutions',[])),c);checks.append('requested institutions')
    from .populations import aggregate_question
    if aggregate_question(c['scope_question']) and not plan.get('population'):raise IntentMismatch('The request needs a population aggregate; a named-institution result cannot replace it.')
    years=plan.get('annual_years',plan.get('years',plan.get('source_years',[])));expected=c['expected_years']
    if 'version' not in plan:
        if expected is not None and sorted(years)!=sorted(expected):raise IntentMismatch('The planned years do not match the requested interval. Please restate the start and end years.')
        if c.get('period_count') is not None and len(set(years))!=c['period_count']:raise IntentMismatch('The plan does not contain the requested number of annual observations. Please restate the interval.')
        if c['temporal'] and len(set(years))<2:raise IntentMismatch('A longitudinal trend needs multiple periods; the plan contains only one. Please specify the intended interval.')
        from .analytics import measures
        specs=measures();chosen=[specs[m] for m in plan['metrics']]
        titles=[m['label'] for m in chosen];group_titles=[];categories=' '.join(m['definition'] for m in chosen)
        percentage=any(m['unit']=='percent' for m in chosen)
        # Exact familiar measure requests must not be routed to another familiar measure.
        q=c['scope_question'].lower();required=[]
        for phrase,metric in [('total enrollment','total_enrollment'),('undergraduate enrollment','undergraduate_enrollment'),('graduate enrollment','graduate_enrollment')]:
            if re.search(r'(?<!\w)'+phrase+r'\b',q) and not c['dimensions'] and not c['percentage']:required.append(metric)
        if not set(required)<=set(plan['metrics']):raise IntentMismatch('The planned measure differs from the requested enrollment measure. Please confirm the population to count.')
    else:
        titles,group_titles,categories=_field_info(plan,evidence)
        percentage=any(x.get('operator')=='percent' for x in plan.get('calculations',[])+plan.get('expressions',[]))
        # Source-defined percentages are also valid; inspect actual field semantics.
        semantics=(evidence or {}).get('field_semantics',{})
        if plan.get('version')==2:percentage=any(u=='percent' for u in (evidence or {}).get('output_units',[]))
        else:percentage=percentage or any(semantics.get(str(s['record_id']),{}).get('unit')=='percent' for s in plan['selections'] if s['role']=='measure')
        if c['temporal'] and len(set(years))<2:
            # A wide/long source can contain multiple observation periods in one
            # release. Reject only when its documented coverage is a single year.
            from .result_text import _table_metadata
            tables={(d.get('release_id'),str(d.get('table_name','')).casefold()) for d in (evidence or {}).get('definition_evidence',[]) if d.get('table_name')}
            docs=_table_metadata(sorted(tables)) if tables else {}
            coverage={int(y) for rows in docs.values() for d in rows for y in re.findall(r'\b(?:19|20)\d{2}\b',str(d.get('year_coverage','')))}
            if len(coverage)==1 and c['time_basis']=='observation':raise IntentMismatch('The trend plan selects only one documented reporting period. Please specify the intended multi-year interval.')
        if expected and c['time_basis']=='observation' and re.search(r'\bfall\b',c['scope_question'],re.I) and sorted(years)!=sorted(expected):
            # Fall survey/release years align for this annual route. Other survey
            # periods are checked from the actual returned reporting periods.
            if all(re.match(r'EF\d{4}',str(d.get('table_name','')),re.I) for d in (evidence or {}).get('definition_evidence',[])) and titles:
                raise IntentMismatch('The fall-enrollment plan omits requested years. Please restate the interval.')
    checks.append('requested time scope')
    for dimension in c['dimensions']:
        pattern=r'\b(gender|sex)\b' if dimension=='gender' else r'race|ethnic'
        grouped=any(re.search(pattern,t,re.I) for t in group_titles)
        if dimension=='gender':
            wide=any(re.search(r'\b(men|male)\b',t,re.I) for t in titles) and any(re.search(r'\b(women|female)\b',t,re.I) for t in titles)
        else:wide=sum(bool(re.search(r'\b(asian|black|white|hispanic|alaska|native|nonresident|race unknown|two or more)\b',t,re.I)) for t in titles)>=2
        if titles and not (wide or grouped):raise IntentMismatch('The plan does not represent the requested '+dimension+' breakdown. Please confirm the categories you want.')
        checks.append(dimension+' represented in source fields/grouping')
    if c['percentage'] and titles and not percentage:
        raise IntentMismatch('The request asks for percentages, but the plan contains counts without a percentage calculation or source-defined percentage. Please confirm the intended denominator.')
    if c['percentage']:checks.append('percentage output')
    if c['undergraduate'] and titles and 'version' not in plan and all(m['family']=='enrollment' for m in chosen) and 'undergraduate_enrollment' not in plan['metrics']:
        raise IntentMismatch('The plan does not establish the requested undergraduate population. Please confirm the population.')
    if c['undergraduate'] and 'version' in plan and any(re.fullmatch(r'EF\d{4}A?',str(d.get('table_name','')),re.I) for d in (evidence or {}).get('definition_evidence',[])):
        if not re.search(r'undergrad',categories+' '+' '.join(titles),re.I):raise IntentMismatch('The fall-enrollment source selection does not establish the requested undergraduate population. Please confirm the population.')
        if re.search(r'first[ -]time|first[ -]year',categories,re.I) and not re.search(r'first[ -]time|first[ -]year|freshm[ae]n|new entrants',c['scope_question'],re.I):
            raise IntentMismatch('The plan restricts enrollment to first-time students although the request asks for the broader undergraduate population. Please confirm the population.')
        checks.append('undergraduate source population')
    return {'contract':deepcopy(c),'plan_checks':checks,'policy':'Bounded independent checks; existing source/population/formula validators remain authoritative. Unknown semantic equivalence is not certified.'}

def check_result(result,c=None):
    if result.get('result_schema_version')==2 and result.get('observation_plan'):
        from .observations import verify_result
        return verify_result(result)
    c=c or result.get('intent_validation',{}).get('contract') or CURRENT.get()
    if not c:return []
    from .progress import report
    report('Checking result coverage before publication…')
    rows=result.get('rows',[])
    actual=[r['unitid'] for r in rows if r.get('unitid') is not None]
    if any(r.get('unitid') is None for r in rows) and result.get('query_audit'):
        actual+=_ids(result['plan']['institutions'])
    _check_institutions(actual,c)
    periods=set();coverage={};metric_coverage={}
    for row in rows:
        row_periods=set()
        if c['time_basis']=='entry_cohort' and row.get('entry_cohort_year') is not None:row_periods.add(int(row['entry_cohort_year']))
        elif c['time_basis']=='class':row_periods.add(int(row['observation_year'])+4)
        else:
            for text in str(row.get('reporting_period','')).split(';'):
                years=[int(y) for y in re.findall(r'\b(?:19|20)\d{2}\b',text)]
                short=list(re.finditer(r'((?:19|20)\d{2})[-–/](\d{2})\b',text))
                full=re.fullmatch(r'\s*((?:19|20)\d{2})[-–/]((?:19|20)\d{2})\s*',text)
                if short:row_periods.update(int(m[1])//100*100+int(m[2]) for m in short)
                elif full and int(full[2])==int(full[1])+1:row_periods.add(int(full[2]))
                elif years and re.search(r'july|june|academic|fiscal',text,re.I):row_periods.add(max(years))
                elif full and not c['temporal']:row_periods.update(range(int(full[1]),int(full[2])+1))
                else:row_periods.update(years)
            if not row_periods:row_periods.add(int(row['observation_year']))
            if c['temporal'] and len(row_periods)>1:row_periods={max(row_periods)}
        periods.update(row_periods)
        coverage.setdefault(row.get('unitid'),set()).update(row_periods)
        metric_coverage.setdefault((row.get('unitid'),row['metric']),set()).update(row_periods)
    if c['temporal'] and len(periods)<2:raise IntentMismatch('Only one reporting period was returned for a longitudinal request. No trend has been published; please restate the interval.')
    if c['temporal'] and c.get('period_count') is not None and len(periods)!=c['period_count']:raise IntentMismatch('The returned result does not contain the requested number of annual observations. No incomplete trend has been published.')
    if c['expected_years'] is not None and periods!=set(c['expected_years']):raise IntentMismatch('The returned periods do not cover the requested interval. No incomplete answer has been published; please confirm the start and end years.')
    if c['expected_years'] is not None and any(p!=set(c['expected_years']) for p in coverage.values()):raise IntentMismatch('A requested institution is missing periods from the returned result. No incomplete comparison has been published.')
    if c['expected_years'] is not None and not result.get('catalog_plan'):
        for uid in coverage:
            if any(metric_coverage.get((uid,m),set())!=set(c['expected_years']) for m in result['plan']['metrics']):raise IntentMismatch('A requested measure is missing periods from the returned result. No incomplete answer has been published.')
    if c['percentage'] and rows and not any(r.get('unit')=='percent' for r in rows):raise IntentMismatch('The returned result contains counts rather than the requested percentages. No reduced answer has been published.')
    for dim in c['dimensions']:
        by_scope={}
        for r in rows:
            key=(r.get('unitid'),r['observation_year']);by_scope.setdefault(key,set())
            if str(r['measure']).casefold() in {'grand total','total undergraduates','total undergraduate enrollment','overall total'}:continue
            by_scope[key].add((r['metric'],tuple(r.get('groups',[]))))
        if by_scope and any(len(v)<2 for v in by_scope.values()):raise IntentMismatch('The returned '+dim+' breakdown has only one category in a requested institution/period. No reduced breakdown has been published.')
    warnings=[]
    if c['temporal']:
        reported={r['observation_year'] for r in rows if r.get('status')=='ok' and r.get('value') is not None}
        if len(reported)<2:warnings.append('Fewer than two periods have reported values; a longitudinal trend cannot be assessed. Missing observations remain gaps.')
    return warnings

def stamp(result,checked):
    if checked is None:return result
    warnings=check_result(result,checked['contract'])
    result['warnings']=list(dict.fromkeys(result.get('warnings',[])+warnings))
    result['intent_validation']={**checked,'result_checks':['institution scope','actual reporting periods','requested output kind and breakdown cardinality'],'status':'passed'}
    return result
