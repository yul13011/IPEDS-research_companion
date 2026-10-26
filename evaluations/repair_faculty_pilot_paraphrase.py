"""One diagnosed narrative repair with exact instructional-population evidence."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
import anthropic
import evaluations.faculty_answer_pilot as p
from analysis_catalog.catalog import connection
p.AUDIT_FILE='semantic_repair_calls.json';p.CURRENT_CASE='instructional_faculty'
initial=json.loads((p.OUT/'results.json').read_text(encoding='utf-8'))
entry=next(e for e in initial if e['id']=='instructional_faculty')
pkg=json.loads((p.OUT/'instructional_faculty_evidence.json').read_text(encoding='utf-8'))
with connection() as db:
    extra=dict(db.execute("SELECT record_id,variable_name,title,long_description FROM source.variable_docs WHERE release_id='IPEDS_2024-25_Provisional' AND table_name='S2024_SIS' AND variable_name='SISTOTL'").fetchone())
pkg['fields'].append(extra)
policy=p.REFINED_POLICY+''' Instructional staff is not restricted to people whose main job is teaching alone. The supplied exact occupational definition includes primarily instruction AND instruction combined with research/public service. Preserve that scope; do not narrow it through a casual paraphrase.'''
client=anthropic.Anthropic(api_key=p.api_key(),timeout=45,max_retries=0)
writing,u=p.call(client,'write_explanation',p.REFINED_WRITE,policy,{'question':entry['question'],'review':entry['review'],'rows':entry['rows'],'source_evidence':pkg})
answer=p.render(pkg,entry['review'],entry['rows'],writing,refined=True)
repair={'id':'instructional_faculty','reason':'Initial refined prose incorrectly narrowed instructional work to main-job teaching.',
    'additional_source_evidence':extra,'policy':policy,'writing':writing,'usage':u,'answer':answer,'status':'semantic_repair_pending_manual_review'}
(p.OUT/'semantic_repair.json').write_text(json.dumps(repair,indent=2),encoding='utf-8')
print(json.dumps(repair,indent=2))
