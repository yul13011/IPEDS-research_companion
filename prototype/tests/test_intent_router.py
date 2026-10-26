"""Claude-first dispatch, typed chart validation, provenance, and UI integration."""
from pathlib import Path
from copy import deepcopy
from types import SimpleNamespace as NS
from unittest.mock import patch,Mock
import sys,json,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype import intent_router as router
from prototype.analytics import execute,Plan
from prototype.responses import finalize_answer
from prototype.agent import DEFAULT_MODEL

def edit(setting,value,series=''):return dict(setting=setting,value=value,series=series)
def decision(route='chart_edit',question='Set numeric axis from zero to ten',rid='',refs=None,edits=None,relationship=None,message=''):
    return dict(route=route,question=question,target_result_id=rid,referenced_turns=refs or [],chart_edits=edits or [],
                relationship=relationship or ('followup' if refs else 'new'),message=message,institution_mentions=[],
                documentation={'kind':'meaning','terms':[question.removeprefix('Define ')],'years':[]} if route=='definition' else {'kind':'none','terms':[],'years':[]})
USAGE=dict(calls=1,latency_seconds=.1,estimated_api_usd=.001,input_tokens=100,output_tokens=40)

class IntentRouterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=finalize_answer({'intent':'analyze','result':execute(Plan(['admission_rate'],['Ivy League'],[2024]))})
        cls.history=[{'question':'Compare Ivy League admission rates in fall 2024.','answer':cls.base}]
        cls.rid=cls.base['result']['result_id']
    def run_request(self,d,prompt='Reset the horizontal axis to between zero and ten',executor=None):
        executor=executor or Mock(side_effect=AssertionError('Unexpected analytical executor'))
        with patch.object(router,'interpret',return_value=(d,dict(USAGE),{self.rid:self.base})):
            return router.handle(prompt,self.base,DEFAULT_MODEL,self.history,executor)

    def test_semantic_chart_patch_reuses_original_result(self):
        d=decision(rid=self.rid,refs=[1],edits=[edit('x_min',0),edit('x_max',10)])
        before=deepcopy(self.base)
        answer=self.run_request(d)
        self.assertEqual(answer['mode'],'presentation adjustment');self.assertIs(answer['result'],self.base['result'])
        self.assertEqual([answer['presentation']['y_min'],answer['presentation']['y_max']],[0,10])
        self.assertEqual(self.base,before);self.assertEqual(answer['model_usage']['calls'],1)
        self.assertNotIn('latency',self.base['result'].get('intent_interpretation',{}))

    def test_atomic_invalid_patch_does_not_edit_or_execute(self):
        for edits in [[edit('title','Partial title'),edit('x_min',0),edit('x_max',200)],
                      [edit('font_size',999)],[edit('x_min',10),edit('x_max',0)],
                      [edit('x_min',0)],[edit('gridlines','false')],
                      [edit('title','a'),edit('title','b')],
                      [edit('reference_value',float('inf'))],
                      [edit('series_color','red','Unknown school')]]:
            with self.subTest(edits=edits):
                a=self.run_request(decision(rid=self.rid,refs=[1],edits=edits))
                self.assertEqual(a['intent'],'clarify');self.assertNotIn('result',a)
        self.assertIsNone(self.base['presentation']['title'])

    def test_axis_orientation_reset_and_rendered_ticks(self):
        from prototype.charts import styled
        from prototype.charts import panels
        d=decision(rid=self.rid,refs=[1],edits=[edit('x_min',0),edit('x_max',10)])
        a=self.run_request(d);p=a['presentation'];spec=styled(panels(a['result'],p)[0],p)
        plot=spec['layer'][0];self.assertEqual(plot['encoding']['x']['scale']['domain'],[0,10])
        self.assertNotIn('values',plot['encoding']['x']['axis'])
        reset=router.apply_chart_edits(a,[edit('x_min',None),edit('x_max',None)])
        self.assertIsNone(reset['presentation']['y_min'])
        with self.assertRaises(ValueError):router.apply_chart_edits(a,[edit('y_min',0),edit('y_max',10)])

    def test_context_has_current_overrides_and_no_full_data(self):
        charts,answers=router.charts_context(self.history,{self.rid:{'title':'Current edited title','y_min':0,'y_max':10}})
        self.assertEqual(charts[0]['numeric_axis'],'x');self.assertEqual(charts[0]['presentation']['title'],'Current edited title')
        self.assertNotIn('rows',charts[0]);self.assertEqual(len(charts[0]['series']),8)
        self.assertIs(answers[self.rid]['result'],self.base['result'])

    def test_old_chart_target_is_validated(self):
        newer=finalize_answer({'result':execute(Plan(['total_enrollment'],['Yale'],[2024]))})
        history=self.history+[{'question':'Yale enrollment','answer':newer}]
        charts,answers=router.charts_context(history)
        d=decision(rid=self.rid,refs=[1],edits=[edit('title','Earlier chart')])
        router.validate_decision(d,'Rename first chart',history,answers)
        d['referenced_turns']=[2]
        with self.assertRaises(ValueError):router.validate_decision(d,'Rename first chart',history,answers)

    def test_conversation_calls_interpreter_before_any_local_parser(self):
        d=decision('conversation','Hi',message='Hello! What IPEDS question can I help with?')
        with patch('prototype.purpose.direct',side_effect=AssertionError('Local purpose shortcut called')):
            a=self.run_request(d,'Hi')
        self.assertEqual(a['intent'],'conversation');self.assertEqual(a['model_usage']['calls'],1)

    def test_source_routes_dispatch_to_corresponding_executor(self):
        for kind,question,target in [('discovery','What data do you have on faculty?','prototype.discovery.overview'),
                                     ('definition','Define Pell','prototype.definitions.answer')]:
            d=decision(kind,question)
            with patch(target,return_value={'intent':'definition' if kind=='definition' else 'discover','message':'Source-backed answer'}) as fn:
                a=self.run_request(d,question)
            fn.assert_called_once();self.assertEqual(a['model_usage']['calls'],1)
        for kind in ['numerical','categorical','analysis']:
            d=decision(kind,'Show Yale enrollment in 2024')
            executor=Mock(return_value={'intent':'clarify','message':'Analytical executor reached'})
            self.run_request(d,'Show Yale enrollment in 2024',executor)
            self.assertIsNone(executor.call_args.args[1]);self.assertTrue(executor.call_args.args[2])

    def test_definition_executor_uses_typed_term_not_free_text(self):
        d=decision('definition','Define admission rate and explain how it is calculated.')
        d['documentation']={'kind':'meaning','terms':['admission rate'],'years':[2015]}
        with patch('prototype.definitions.answer',return_value={'intent':'definition','message':'Source definition'}) as define:
            self.run_request(d,'What does admission rate mean in 2015?')
        self.assertEqual(define.call_args.args[0],'Define admission rate in 2015')
        d['documentation']['years']=[]
        with self.assertRaises(ValueError):self.run_request(d,'Define admission rate in 2015')

    def test_clarification_may_identify_chart_but_cannot_edit_it(self):
        d=decision('clarify','',rid=self.rid,refs=[1],message='Dashed lines are unavailable. Would you like a different color?')
        a=self.run_request(d,'Make the lines dashed')
        self.assertEqual(a['intent'],'clarify');self.assertNotIn('result',a)
        d['chart_edits']=[edit('color','red')]
        with self.assertRaises(ValueError):self.run_request(d,'Make the lines dashed')

    def test_chart_plan_needs_no_rewritten_sentence(self):
        d=decision(question='',rid=self.rid,refs=[1],edits=[edit('numeric_min',0),edit('numeric_max',10)])
        a=self.run_request(d)
        self.assertEqual(a['presentation']['y_max'],10);self.assertNotIn('resolved_question',a)

    def test_mixed_analysis_edits_new_result_and_retains_usage(self):
        newer=finalize_answer({'result':execute(Plan(['admission_rate'],['Yale','Harvard'],[2024]))})
        before=deepcopy(self.base)
        d=decision('mixed','Compare Yale and Harvard admission rates in 2024',refs=[1],edits=[edit('color','red')])
        executor=Mock(return_value=newer)
        a=self.run_request(d,'Add Harvard and color the bars red in 2024',executor)
        self.assertIs(a['result'],newer['result']);self.assertEqual(a['presentation']['color'],'red')
        self.assertEqual(self.base,before)
        bad=decision('mixed','Compare Yale and Harvard',refs=[1],edits=[edit('font_size',999)])
        executor=Mock(side_effect=AssertionError('Invalid edits must fail before analysis'))
        self.assertEqual(self.run_request(bad,'Add Harvard and make font size 999',executor)['intent'],'clarify')

    def test_context_resolution_is_not_called_twice(self):
        from prototype import agent
        d=decision('numerical','Show Harvard admission rate in 2024',refs=[1])
        executor=lambda q,p,u,m,**kwargs:agent.ask(q,p,u,m,conversation=kwargs['conversation'])
        with (patch('prototype.memory.resolve',side_effect=AssertionError('Duplicate context call')),
              patch('prototype.agent._answer',return_value={'intent':'clarify','message':'Planner reached'})):
            a=self.run_request(d,'What about Harvard?',executor)
        self.assertEqual(a['conversation_resolution']['kind'],'followup');self.assertIsNone(router.INTERPRETED.get())

    def test_transport_schema_context_and_malformed_decision(self):
        d=decision('conversation','Hello',message='Hello!')
        response=NS(content=[NS(type='tool_use',name='route_request',input=d)],stop_reason='tool_use',usage=NS(input_tokens=100,output_tokens=20))
        with patch('anthropic.Anthropic') as cls:
            cls.return_value.messages.create.return_value=response
            answer,usage,_=router.interpret('Hello',[],DEFAULT_MODEL)
            payload=json.loads(cls.return_value.messages.create.call_args.kwargs['messages'][0]['content'])
        self.assertEqual(answer,d);self.assertEqual(payload['question'],'Hello');self.assertEqual(usage['calls'],1)
        with patch('anthropic.Anthropic') as cls:
            cls.return_value.messages.create.return_value=NS(content=[],stop_reason='end_turn')
            with self.assertRaises(ValueError):router.interpret('Hello',[],DEFAULT_MODEL)
        d=decision('numerical','Show Yale enrollment')
        with self.assertRaises(ValueError):router.validate_decision(d,'Show Yale enrollment in 2020',self.history,{})

    def test_release_labels_normalize_without_collapsing_observation_windows(self):
        for label in ['2024-25','2024–2025','2024/25']:
            q='Define admission rate in the '+label+' release'
            d=decision('definition','Define admission rate');d['documentation']['years']=[2024,2025]
            normalized=router.normalize_decision(d,q)
            self.assertEqual(normalized['documentation']['years'],[2024])
            router.validate_decision(normalized,q,[],{})
        self.assertIsNone(router.source_release_years('Compare fall 2023-2024 admissions'))
        self.assertIsNone(router.source_release_years('Compare releases 2015-2024'))
        self.assertIsNone(router.source_release_years('Compare releases 2023-2024'))
        self.assertEqual(router.source_release_years('Compare 2023-24 and 2024-25 releases'),[2023,2024])
        d['documentation']['years']=[2024,2030]
        self.assertEqual(router.normalize_decision(d,q)['documentation']['years'],[2024,2030])

    def test_analysis_with_chart_edits_is_normalized_to_mixed(self):
        d=decision('numerical','Compare Yale and Harvard in 2024',edits=[edit('color','blue')])
        normalized=router.normalize_decision(d,'Compare Yale and Harvard in 2024 and make the bars blue')
        self.assertEqual(normalized['route'],'mixed')
        router.validate_decision(normalized,'Compare Yale and Harvard in 2024 and make the bars blue',[],{})
        self.assertEqual(d['route'],'numerical')
        invalid=decision('conversation','Hello',message='Hello',edits=[edit('color','blue')])
        with self.assertRaises(ValueError):router.validate_decision(router.normalize_decision(invalid,'Hello'),'Hello',[],{})

    def test_ai_ui_chart_and_greeting_bypass_local_shortcuts(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        app.session_state['use_ai']=True;app.session_state['main_page']='Ask & Analyze'
        app.session_state['history']=deepcopy(self.history);app.run()
        d=decision(rid=self.rid,refs=[1],edits=[edit('x_min',0),edit('x_max',10)])
        with (patch.object(router,'interpret',return_value=(d,dict(USAGE),{self.rid:self.base})) as interpreted,
             patch('prototype.ui.adjust_presentation',side_effect=AssertionError('Local chart parser called')),
             patch('prototype.purpose.direct',side_effect=AssertionError('Local purpose parser called')),
             patch('prototype.ui.ask',side_effect=AssertionError('Analytical executor called'))):
            app.chat_input(key='followup_question').set_value('Reset the horizontal scale to between zero and ten').run()
        interpreted.assert_called_once();self.assertFalse(app.exception);self.assertFalse(app.session_state.get('request_error'))
        a=app.session_state['history'][-1]['answer'];self.assertEqual(a['presentation']['y_max'],10)
        self.assertEqual(a['result'],self.base['result'])
        d=decision('conversation','Thanks',message='You are welcome.')
        with patch.object(router,'interpret',return_value=(d,dict(USAGE),{})) as interpreted:
            app.chat_input(key='followup_question').set_value('Thanks').run()
        interpreted.assert_called_once();self.assertEqual(app.session_state['history'][-1]['answer']['mode'],'conversation')

if __name__=='__main__':unittest.main()
