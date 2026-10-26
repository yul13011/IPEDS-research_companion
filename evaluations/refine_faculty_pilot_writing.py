"""Second writing pass only; preserves all initial pilot outputs and evidence."""
from pathlib import Path
import json,sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
import anthropic
import evaluations.faculty_answer_pilot as p
p.AUDIT_FILE='writing_refinement_calls.json'

entries=json.loads((p.OUT/'results.json').read_text(encoding='utf-8'))
client=anthropic.Anthropic(api_key=p.api_key(),timeout=45,max_retries=0)
out=[]
for entry in entries:
    if not entry.get('rows'):continue
    p.CURRENT_CASE=entry['id']
    pkg=json.loads((p.OUT/(entry['id']+'_evidence.json')).read_text(encoding='utf-8'))
    try:
        value,u=p.call(client,'write_explanation',p.REFINED_WRITE,p.REFINED_POLICY,
            {'question':entry['question'],'review':entry['review'],'rows':entry['rows'],'source_evidence':pkg})
        answer=p.render(pkg,entry['review'],entry['rows'],value,refined=True)
        row={'id':entry['id'],'writing':value,'usage':u,'answer':answer,'words':len(answer.split()),'source_values_reused_unchanged':True}
    except Exception as exc:row={'id':entry['id'],'error':str(exc)}
    out.append(row)
    (p.OUT/'writing_refinement.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    (p.OUT/'writing_refinement_calls.json').write_text(json.dumps(p.CALL_AUDIT,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in row.items() if k not in {'writing','answer'}}),flush=True)
md='# Refined faculty answer examples\n\n'
for row in out:md+='## '+row['id']+'\n\n'+row.get('answer','ERROR: '+row.get('error',''))+'\n\n'
(p.OUT/'refined_answers.md').write_text(md,encoding='utf-8')
