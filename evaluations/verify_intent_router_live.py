"""Bounded live intent-only probes, plus validated chart patches; no new data queries."""
from pathlib import Path
import json,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.intent_router import interpret,apply_chart_edits
from prototype.agent import DEFAULT_MODEL
from prototype.analytics import execute,Plan
from prototype.responses import finalize_answer

def main():
    if '--live' not in sys.argv:raise SystemExit('Pass --live to make provider requests.')
    base=finalize_answer({'intent':'analyze','result':execute(Plan(['admission_rate'],['Ivy League'],[2024]))})
    history=[{'question':'Compare Ivy League admission rates in fall 2024.','answer':base}]
    cases=[('greeting','Hi',[],{'conversation'}),('thanks','Thanks, that helps!',history,{'conversation'}),
        ('discovery','What information do you have on faculty?',[],{'discovery'}),
        ('definition','What does Pell mean?',[],{'definition'}),
        ('numerical',"Show Yale's admission rate for the past ten years ending in fall 2024",[],{'numerical','analysis'}),
        ('categorical','Which schools in Massachusetts offer distance education in fall 2024?',[],{'categorical','analysis'}),
        ('axis_owner','reset x-axis range to 0-10',history,{'chart_edit'}),
        ('axis_paraphrase','Could you zoom the horizontal percentage scale to between zero and ten?',history,{'chart_edit'}),
        ('compound','Make Harvard red, put the legend at the bottom, and set the font size to 18.',history,{'chart_edit'}),
        ('quoted_title',"Set the title to 'Admissions, and show table'",history,{'chart_edit'}),
        ('mixed','Add MIT to this comparison and make the bars blue.',history,{'mixed'}),
        ('followup','What about in 2023?',history,{'numerical','analysis'}),
        ('unsupported','Can you make the lines dashed?',history,{'clarify'})]
    records=[];total_cost=0
    for label,question,conversation,expected in cases:
        start=time.perf_counter();record={'case':label,'question':question}
        try:
            d,usage,answers=interpret(question,conversation,DEFAULT_MODEL)
            record.update(decision=d,usage=usage,passed=d['route'] in expected)
            total_cost+=usage.get('estimated_api_usd',0)
            if d['route']=='chart_edit':
                edited=apply_chart_edits(answers[d['target_result_id']],d['chart_edits'])
                record['same_result']=edited['result'] is base['result']
                record['presentation']=edited['presentation'];record['passed']&=record['same_result']
                if label.startswith('axis_'):record['passed']&=edited['presentation']['y_min']==0 and edited['presentation']['y_max']==10
                if label=='compound':record['passed']&=edited['presentation']['font_size']==18 and edited['presentation']['legend']=='bottom' and edited['presentation']['series_colors'].get('Harvard University')=='red'
                if label=='quoted_title':record['passed']&=edited['presentation']['title']=='Admissions, and show table' and edited['presentation']['show_table']==base['presentation']['show_table']
            if label=='followup':record['passed']&=d['relationship']=='followup' and '2023' in d['question']
            if label=='mixed':record['passed']&=bool(d['chart_edits']) and 'MIT' in d['question']
        except Exception as exc:record.update(passed=False,error_type=type(exc).__name__,error=str(exc)[:500])
        record['wall_seconds']=round(time.perf_counter()-start,3);records.append(record)
        report={'model':DEFAULT_MODEL,'scope':'Live initial intent interpretation only, with chart patches applied locally. Analytical/discovery/definition executors tested separately. Not a broad accuracy certification.',
                'passed':sum(r['passed'] for r in records),'total':len(records),'estimated_api_usd':total_cost,'cases':records}
        (ROOT/'evaluations/intent_router_live.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps({k:record[k] for k in ['case','passed','wall_seconds']}|{'route':record.get('decision',{}).get('route'),'error':record.get('error')}),flush=True)
    return 0 if all(r['passed'] for r in records) else 1

if __name__=='__main__':raise SystemExit(main())
