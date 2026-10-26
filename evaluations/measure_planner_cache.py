"""Small live, metadata-only cache probe; run manually (incurs API charges).

Records per-call cache usage, not a controlled before/after cost comparison.
Does not execute statistical queries or change the application's model setting.
"""
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.agent import DEFAULT_MODEL,usage_cost
from prototype.api_client import get_client
from prototype.catalog_planner import model_catalog_plan


def main():
    client=get_client()
    original=client.messages.create
    records=[]
    current={}
    def create(**kwargs):
        if len(records)>=12:raise RuntimeError('Live probe call budget reached.')
        start=time.perf_counter()
        response=original(**kwargs)
        usage={k:getattr(response.usage,k,0) or 0 for k in (
            'input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens')}
        stable=kwargs['messages'][0]['content'][0]['text']
        records.append({'question':current['question'],'seconds':round(time.perf_counter()-start,3),
            'catalog_prefix_sha256':hashlib.sha256(stable.encode()).hexdigest(),
            'message_count':len(kwargs['messages']),**usage,
            'estimated_api_usd':usage_cost(DEFAULT_MODEL,usage)})
        print(json.dumps(records[-1]),flush=True)
        return response
    outcomes=[]
    # Only metadata proposals are prepared. Isolate any saved proposal artifacts.
    with tempfile.TemporaryDirectory() as temporary:
        with patch.object(client.messages,'create',side_effect=create),patch('prototype.catalog_planner.PLAN_DIR',Path(temporary)):
            for institution in ('Yale','Harvard'):
                current['question']=f'Show {institution} academic library total expenses for fiscal 2024.'
                answer=model_catalog_plan(current['question'])
                outcomes.append({'question':current['question'],'intent':answer.get('intent'),
                    'calls':answer.get('model_usage',{}).get('calls'),
                    'validation':answer.get('catalog_proposal',{}).get('validation',{})})
    total_input=sum(r[k] for r in records for k in (
        'input_tokens','cache_creation_input_tokens','cache_read_input_tokens'))
    result={'model':DEFAULT_MODEL,'ttl':'5m','note':'Cache hit probe, not a controlled before/after experiment.',
        'outcomes':outcomes,'calls':records,'total_input_tokens':total_input,
        'cache_read_fraction':sum(r['cache_read_input_tokens'] for r in records)/total_input if total_input else 0,
        'estimated_api_usd':sum(r['estimated_api_usd'] for r in records)}
    target=ROOT/'evaluations/planner_cache_probe.json'
    target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('Saved',target,flush=True)


if __name__=='__main__':main()
