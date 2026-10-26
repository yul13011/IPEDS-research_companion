"""Controlled live writer comparison over identical deterministic evidence packages."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import datetime,json,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.discovery import overview
from prototype.discovery_narrative import write
from prototype.agent import DEFAULT_MODEL

CONFIGS=[('sonnet_current',DEFAULT_MODEL,{}),
    ('haiku_current','claude-haiku-5-5',{}),
    ('haiku_larger','claude-haiku-5-5',{'max_tokens':7000}),
    ('haiku_no_reasoning','claude-haiku-5-5',{'reasoning':'disabled'})]

def main():
    if '--live' not in sys.argv:raise SystemExit('Pass --live; incurs API charges (up to 24 writer calls).')
    records=[];unavailable=[];target=ROOT/'evaluations/narrative_settings_comparison.json'
    if '--resume' in sys.argv and target.exists():
        prior=json.loads(target.read_text(encoding='utf-8'))
        unavailable.extend(prior.get('previous_unavailable_attempts',[]))
        for record in prior['records']:
            (records if record['usage'].get('usage_complete') else unavailable).append(record)
    def run(item):
        name,model,settings=item;start=time.perf_counter()
        answer=write(base,question,model,writer_settings=settings)
        audit=answer['discovery_narrative'];usage=answer.get('model_usage',{})
        record={'topic':topic,'round':round_number,'configuration':name,'model':model,'settings':settings,
            'status':audit['status'],'reason':audit.get('reason'),'error_type':audit.get('error_type'),'validation':audit.get('validation'),
            'evidence_sha256':audit.get('evidence_sha256'),'usage':usage,
            'wall_seconds':round(time.perf_counter()-start,3)}
        print(json.dumps(record),flush=True)
        return record
    with ThreadPoolExecutor(max_workers=2) as pool:
        for topic in ['faculty','graduation rates','admissions']:
            question='What data do you have on '+topic+'?'
            base=overview(question)
            for round_number in [1,2]:
                if sum(r['usage'].get('estimated_api_usd',0) or 0 for r in records)>2:
                    raise RuntimeError('Stopped at $2 estimated writer-probe spend.')
                order=CONFIGS if round_number==1 else CONFIGS[::-1]
                pending=[item for item in order if not any(r['topic']==topic and r['round']==round_number and r['configuration']==item[0] for r in records)]
                records.extend(pool.map(run,pending))
                target.write_text(json.dumps({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    'scope':'Same deterministic source evidence per topic for every writer setting. No app defaults changed.',
                    'previous_unavailable_attempts':unavailable,'records':records},indent=2),encoding='utf-8')
                if any(not r['usage'].get('usage_complete') and r.get('error_type') in {'BadRequestError','AuthenticationError','PermissionDeniedError'} for r in records):
                    print('Stopped: provider unavailable; retain partial results and restore account access before rerunning.',flush=True)
                    return
    print('Saved',target,flush=True)

if __name__=='__main__':main()
