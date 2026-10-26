"""Real paired retrieval/latency/cost checks for everyday discovery wording."""
from pathlib import Path
import argparse,datetime,json,statistics,sys,time
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.discovery import overview
from prototype.institution_confirmation import ask

CASES=[('family cost','What data do we have on what families actually pay?',['net price']),
    ('teacher pay',"What information do you have on teachers' pay?",['salar','salary']),
    ('students leaving','What data do we have on students who leave?',['graduation','retention','award and enrollment']),
    ('overseas students','What information do you have on students from overseas?',['enrollment']),
    ('college tuition','What data do we have about college tuition?',['tuition','student charges'])]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');parser.add_argument('--label');parser.add_argument('--output',default='discovery_interpretation_live.json');args=parser.parse_args()
    if not args.live:parser.error('Pass --live to incur the authorized provider usage.')
    report={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cases':[],
        'scope':'Real local metadata and configured provider, one fresh run per phrase. Baseline is offline original keywords. Timings exclude browser paint; small descriptive sample, no SLA. Target checks are source-description substrings, not proof of semantic recall or precision. Catalog verification establishes existence, not equivalence to everyday wording.'}
    path=ROOT/'evaluations'/Path(args.output).name
    for label,question,targets in CASES:
        if args.label and label!=args.label:continue
        mark=time.perf_counter();baseline=overview(question);baseline_elapsed=time.perf_counter()-mark
        mark=time.perf_counter();answer=ask(question,use_model=True);elapsed=time.perf_counter()-mark
        audit=answer.get('discovery',{}).get('interpretation',{})
        old_titles=[i['title'] for i in baseline.get('discovery',{}).get('topics',[])]
        titles=[i['title'] for i in answer.get('discovery',{}).get('topics',[])]
        expected=lambda values:any(any(t in title.casefold() for t in targets) for title in values)
        case={'label':label,'question':question,'baseline_keywords':baseline.get('query'),
            'baseline_seconds':baseline_elapsed,'baseline_titles':old_titles,'expanded_titles':titles,
            'baseline_target_found':expected(old_titles),'expanded_target_found':expected(titles),
            'original_hits_preserved':set(audit.get('original_hit_record_ids',[]))<=set(audit.get('merged_hit_record_ids',[])),
            'interpretation':audit,'narrative_status':answer.get('discovery_narrative',{}).get('status'),
            'narrative_reason':answer.get('discovery_narrative',{}).get('reason'),'message':answer['message'],
            'latency':answer.get('latency'),'wall_seconds':elapsed,'model_usage':answer.get('model_usage')}
        report['cases'].append(case);path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
        print(json.dumps({'label':label,'verified':[v['concept'] for v in audit.get('verified',[])],
            'rejected':[v['concept'] for v in audit.get('rejected',[])],'original_hits_preserved':case['original_hits_preserved'],
            'baseline_target_found':case['baseline_target_found'],'expanded_target_found':case['expanded_target_found'],
            'narrative_status':case['narrative_status'],'reason':case['narrative_reason'],
            'latency':case['latency'],'usage':case['model_usage']},ensure_ascii=False),flush=True)
    report['summary']={'cases':len(report['cases']),
        'baseline_targets_found':sum(c['baseline_target_found'] for c in report['cases']),
        'expanded_targets_found':sum(c['expanded_target_found'] for c in report['cases']),
        'original_hits_preserved':all(c['original_hits_preserved'] for c in report['cases']),
        'median_answer_seconds':statistics.median(c['wall_seconds'] for c in report['cases']),
        'median_interpretation_seconds':statistics.median(c['latency'].get('discovery_interpretation_seconds',0) for c in report['cases']),
        'estimated_total_usd':sum(c.get('model_usage',{}).get('estimated_api_usd') or 0 for c in report['cases'])}
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(report['summary']),flush=True)


if __name__=='__main__':main()
