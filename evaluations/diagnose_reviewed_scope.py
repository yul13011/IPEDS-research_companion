"""Inspect one rejected reviewed-plan proposal; --live incurs API charges."""
from pathlib import Path
from unittest.mock import patch
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.api_client import get_client
from prototype.agent import DEFAULT_MODEL,usage_cost
from prototype.intent_router import handle
from prototype.institution_confirmation import ask

def main():
    if '--live' not in sys.argv:raise SystemExit('Pass --live for at most four provider calls.')
    client=get_client();original=client.messages.create;calls=[]
    def create(**kwargs):
        if len(calls)>=4:raise RuntimeError('Diagnostic provider-call cap reached.')
        response=original(**kwargs)
        usage={k:getattr(response.usage,k,0) or 0 for k in ['input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens']}
        tools=[{'tool':b.name,'input':b.input} for b in response.content if b.type=='tool_use']
        payload=kwargs['messages'][0]['content']
        if isinstance(payload,str):
            try:payload=json.loads(payload)
            except json.JSONDecodeError:payload={}
        calls.append({'model':kwargs['model'],'tools':tools,
            'planner_question':payload.get('question') if isinstance(payload,dict) else None,
            'usage':usage,'estimated_api_usd':usage_cost(kwargs['model'],usage)})
        return response
    question='Compare Yale University and Harvard University admission rates in fall 2024 and make the bars blue.'
    with patch.object(client.messages,'create',side_effect=create):
        answer=handle(question,None,DEFAULT_MODEL,[],ask)
    result={'question':question,'calls':calls,'answer':{k:answer.get(k) for k in ['intent','message','plan','intent_validation','model_usage']}}
    target=ROOT/'evaluations/reviewed_scope_diagnostic.json'
    target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
