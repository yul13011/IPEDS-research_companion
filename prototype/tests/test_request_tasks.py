"""Source-backed coverage and complete, scope-preserving conversational work."""
from pathlib import Path
from copy import deepcopy
from unittest.mock import Mock,patch
import sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype import intent_router as router,conversation as working,coverage
from prototype.tests.test_intent_router import decision,edit,USAGE
from prototype.analytics import Plan,execute
from prototype.responses import finalize_answer
from prototype.agent import DEFAULT_MODEL
from prototype.tests.test_query_engine import source,plan,field_ref


def query(operation='none',**changes):
    return dict({'operation':operation,'measure_ids':[],'field_record_ids':[],'institutions':[],
        'topic':'','time_basis':'observation','requested_years':[],'inherit_working':False,'requested_chart':'','scope_mode':'context'},**changes)


def task(route,request,*,identity='t1',question=None,refs=None,binding='new',changes=None,depends=None,cov=None,edits=None,target=''):
    d=decision(route,question or request,refs=refs,rid=target,edits=edits,
        relationship='followup' if refs or depends else 'new',message='Please specify the intended meaning.' if route=='clarify' else '')
    return dict(d,id=identity,request=request,depends_on=depends or [],binding=binding,
        subject_result_id='',changes=changes or [],period_selection='as_requested',coverage=cov or query())


class RequestTaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=finalize_answer({'result':execute(Plan(['admission_rate'],['Ivy League'],[2024]))})
        cls.history=[{'question':'Compare Ivy League admission rates in fall 2024.','answer':cls.base}]

    def run_request(self,tasks,prompt,history=None,executor=None):
        history=self.history if history is None else history
        _,answers=router.charts_context(history)
        with patch.object(router,'interpret',return_value=({'tasks':tasks},dict(USAGE),answers)):
            return router.handle(prompt,working.recent_result(history),DEFAULT_MODEL,history,executor or Mock(side_effect=AssertionError('Unexpected statistical query')))

    def test_unavailable_fall_then_which_years_preserves_subject_and_artifact(self):
        q='Do we have admission rates for fall 2025?'
        first=self.run_request([task('coverage',q,refs=[1],binding='working',cov=query('check',requested_years=[2025],inherit_working=True,time_basis='working'))],q)
        self.assertIn('not loaded',first['message'])
        self.assertEqual(first['coverage']['available_periods'],list(range(2015,2025)))
        self.assertEqual(first['task_tracking']['tasks'][0]['status'],'unavailable')
        q2='Which years do we have?'
        second=self.run_request([task('coverage',q2,refs=[2],binding='working',cov=query('periods',inherit_working=True,time_basis='working'))],q2,self.history+[{'question':q,'answer':first}])
        self.assertIn('2015–2024',second['message'])
        self.assertEqual(second['working_analysis']['artifact']['result_id'],self.base['result']['result_id'])
        self.assertEqual(len(second['coverage']['entries'][0]['periods'][0]['institutions']),8)

    def test_measure_specific_periods_not_global_year_range(self):
        sat=coverage.answer(query('periods',measure_ids=['satvr50'],institutions=['Yale']))
        self.assertEqual(sat['coverage']['available_periods'],[2022,2023,2024])
        not_mapped=coverage.answer(query('check',measure_ids=['satvr50'],requested_years=[2020]))
        self.assertNotEqual(not_mapped['coverage']['requested_status'],'not_loaded')
        cohorts=coverage.answer(query('periods',measure_ids=['graduation_rate'],time_basis='entry_cohort'))
        self.assertEqual(cohorts['coverage']['available_periods'],list(range(2009,2019)))

    def test_matching_measure_inherits_institutions_unless_dataset_scope_is_explicit(self):
        state=working.from_history(self.history)
        state['subject']['measure_ids']=['applicants','admits','admission_rate']
        answer=coverage.answer(query('check',measure_ids=['admission_rate'],requested_years=[2025]),state)
        self.assertEqual(len(answer['coverage']['scope']['institutions']),8)
        dataset=coverage.answer(query('periods',measure_ids=['admission_rate'],scope_mode='dataset'),state)
        self.assertEqual(dataset['coverage']['scope']['institutions'],[])

    def test_global_release_inventory_cannot_silently_replace_bound_measure_years(self):
        q='Which years do you have?'
        t=task('coverage',q,cov=query('releases',scope_mode='dataset'))
        from prototype.request_tasks import validate
        with self.assertRaisesRegex(ValueError,'silently cleared'):
            validate({'tasks':[t]},q,self.history,router.charts_context(self.history)[1],router.SCHEMA)
        q='Which years does the whole database cover?'
        t=task('coverage',q,changes=['measure'],cov=query('releases',scope_mode='dataset'))
        answer=self.run_request([t],q)
        self.assertEqual(answer['coverage']['time_basis'],'source_release')
        self.assertEqual(answer['coverage']['scope']['measure_ids'],[])

    def test_no_bounded_search_absence_claim(self):
        answer=coverage.answer(query('check',topic='qzxabcxzz',requested_years=[2024]))
        self.assertEqual(answer['coverage']['status'],'inconclusive')
        self.assertIn('does not prove',answer['message'])
        releases=coverage.answer(query('releases'))
        self.assertEqual(releases['coverage']['time_basis'],'source_release')

    def test_independent_parts_and_coverage_dependency(self):
        a='Do we have admission rates for fall 2025?';b='Which years are available?';c='Compare the latest available year.'
        tasks=[task('coverage',a,refs=[1],binding='working',cov=query('check',requested_years=[2025],inherit_working=True)),
            task('coverage',b,identity='t2',refs=[1],binding='working',cov=query('periods',inherit_working=True)),
            task('numerical',c,identity='t3',question='Compare Ivy League admission rates in the latest available year.',refs=[1],binding='working',changes=['period'],depends=['t2'])]
        tasks[-1]['period_selection']='latest_available'
        tasks[-1]['referenced_turns']=[]  # Dependency supplies the antecedent.
        executor=Mock(return_value=deepcopy(self.base))
        answer=self.run_request(tasks,a+' '+b+' '+c,executor=executor)
        self.assertEqual([t['status'] for t in answer['task_tracking']['tasks']],['unavailable','answered','answered'])
        self.assertEqual(executor.call_count,1)
        self.assertIn('2024',executor.call_args.args[0]);self.assertNotIn('2025',executor.call_args.args[0])
        self.assertEqual(answer['model_usage']['calls'],1)
        self.assertEqual(working.recent_result([{'answer':answer}])['result']['result_id'],self.base['result']['result_id'])

    def test_coverage_can_bootstrap_analysis_without_an_earlier_result(self):
        a='Which years are available for Ivy League admission rates?';b='Compare the latest available year.'
        first=task('coverage',a,cov=query('periods',measure_ids=['admission_rate'],institutions=['Ivy League'],scope_mode='explicit'))
        second=task('numerical',b,identity='t2',question='Compare Ivy League admission rates for the latest available year.',binding='working',changes=['period'],depends=['t1'])
        second['period_selection']='latest_available'
        answer=self.run_request([first,second],a+' '+b,history=[],executor=Mock(return_value=deepcopy(self.base)))
        self.assertEqual([t['status'] for t in answer['task_tracking']['tasks']],['answered','answered'])

    def test_unsupported_chart_does_not_drop_independent_work(self):
        a='Show a 100% stacked bar chart.';b='Compare Ivy League admission rates in fall 2024.'
        tasks=[task('capability',a,cov=query('capabilities',requested_chart='100% stacked bar')),
            task('numerical',b,identity='t2')]
        executor=Mock(return_value=deepcopy(self.base))
        answer=self.run_request(tasks,a+' '+b,executor=executor)
        self.assertEqual([t['status'] for t in answer['task_tracking']['tasks']],['unsupported','answered'])
        executor.assert_called_once()

    def test_omitted_question_or_bad_dependency_fails_before_execution(self):
        t=task('numerical','Compare Ivy League admission rates in fall 2024.')
        with self.assertRaisesRegex(ValueError,'every part'):
            self.run_request([t],t['request']+' Which years are available?')
        t['depends_on']=['t1']
        with self.assertRaisesRegex(ValueError,'dependencies'):self.run_request([t],t['request'])

    def test_dependent_chart_uses_new_result_and_parent_history_is_reusable(self):
        a='Compare Ivy League admission rates in fall 2024.';b='Set the font size to 18.'
        tasks=[task('numerical',a),task('chart_edit',b,identity='t2',depends=['t1'],binding='working',changes=['presentation'],edits=[edit('font_size',18)],target='task:t1')]
        answer=self.run_request(tasks,a+' '+b,executor=Mock(return_value=deepcopy(self.base)))
        self.assertEqual([t['status'] for t in answer['task_tracking']['tasks']],['answered','answered'])
        self.assertEqual(answer['task_results'][1]['answer']['presentation']['font_size'],18)
        charts,answers=router.charts_context([{'question':a+' '+b,'answer':answer}])
        self.assertEqual(len(charts),1);self.assertEqual(charts[0]['presentation']['font_size'],18)

    def test_working_binding_supplies_validated_reference_without_model_guessing_turn(self):
        q='Set the font size to 18.'
        t=task('chart_edit',q,binding='working',changes=['presentation'],edits=[edit('font_size',18)])
        t['relationship']='followup'
        answer=self.run_request([t],q)
        self.assertEqual(answer['presentation']['font_size'],18)
        self.assertIs(answer['result'],self.base['result'])

    def test_population_guard_rejects_undergraduate_substitution(self):
        s,defs=source('EF2024A',fields=['EFASIAT','EFTOTLT'],filters={'EFALEVEL':'12'})
        grad_plan=plan([s],[(field_ref(defs['EFASIAT'],'s'),'Graduate Asian count')])
        from prototype.query_engine import execute as execute_query
        grad=finalize_answer({'catalog_plan':grad_plan,'result':execute_query(grad_plan,'Yale graduate enrollment by race in fall 2024')})
        ug_source,ug_defs=source('EF2024A',fields=['EFASIAT','EFTOTLT'],filters={'EFALEVEL':'2'})
        ug_plan=plan([ug_source],[(field_ref(ug_defs['EFASIAT'],'s'),'Undergraduate Asian count')])
        bad=finalize_answer({'catalog_plan':ug_plan,'result':execute_query(ug_plan,'Yale undergraduate enrollment by race in fall 2024')})
        q='Convert these student enrollment numbers into percentages.'
        answer=self.run_request([task('numerical',q,question='Convert Yale graduate enrollment by race and ethnicity in fall 2024 into percentages of total graduate enrollment.',refs=[1],binding='working',changes=['calculation'])],q,[{'question':'Yale graduate enrollment by race in fall 2024','answer':grad}],Mock(return_value=bad))
        self.assertEqual(answer['task_tracking']['tasks'][0]['status'],'blocked')
        self.assertNotIn('result',answer)
        self.assertEqual(answer['working_analysis']['artifact']['result_id'],grad['result']['result_id'])

    def test_earlier_analytical_subject_is_bound_by_result_id(self):
        newer=finalize_answer({'result':execute(Plan(['admission_rate'],['Yale'],[2024]))})
        h=self.history+[{'question':'Yale admission rate in fall 2024','answer':newer}]
        q='Use the earlier Ivy comparison.'
        t=task('numerical',q,question='Show the Ivy League admission rates in fall 2024.',refs=[1],binding='referenced')
        t['subject_result_id']=self.base['result']['result_id']
        executor=Mock(return_value=deepcopy(self.base))
        answer=self.run_request([t],q,h,executor)
        self.assertEqual(answer['task_tracking']['tasks'][0]['status'],'answered')
        self.assertEqual(executor.call_args.args[1],self.base['result']['plan'])

    def test_working_result_turn_rebases_when_chat_history_is_trimmed(self):
        state=working.from_history(self.history)
        state['artifact']['turn']=31
        h=[{'question':'Old comparison','answer':self.base},{'question':'Which years?','answer':{'working_analysis':state}}]
        self.assertEqual(working.from_history(h)['artifact']['turn'],1)
        self.assertIsNone(working.from_history(h[1:])['artifact'])

    def test_calculation_change_cannot_drop_an_output_category_hidden_in_selections(self):
        s,d=source('EF2024A',fields=['EFASIAT','EFWHITT'],filters={'EFALEVEL':'12'})
        p=plan([s],[(field_ref(d['EFASIAT'],'s'),'Asian'),(field_ref(d['EFWHITT'],'s'),'White')])
        from prototype.query_engine import execute as execute_query
        old=finalize_answer({'catalog_plan':p,'result':execute_query(p,'Yale graduate Asian and White enrollment in fall 2024')})
        changed=deepcopy(old);changed['catalog_plan']['outputs']=changed['catalog_plan']['outputs'][:1]
        changed['result']['catalog_plan']['outputs']=changed['result']['catalog_plan']['outputs'][:1]
        changed['result']['rows']=changed['result']['rows'][:1]
        with self.assertRaisesRegex(ValueError,'dropped'):
            working.validate_transition(working.subject_for(old),changed,['calculation'])

    def test_multi_part_response_renders_and_remains_followable_in_streamlit(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        app.session_state['use_ai']=True;app.session_state['main_page']='Ask & Analyze';app.run()
        a='Which years are available for Ivy League admission rates?';b='Compare the latest available year.'
        tasks=[task('coverage',a,cov=query('periods',measure_ids=['admission_rate'],institutions=['Ivy League'],scope_mode='explicit')),
            task('numerical',b,identity='t2',question='Compare Ivy League admission rates for the latest available year.',depends=['t1'],binding='working',changes=['period'])]
        tasks[-1]['period_selection']='latest_available'
        with patch.object(router,'interpret',return_value=({'tasks':tasks},dict(USAGE),{})),patch('prototype.ui.ask',return_value=deepcopy(self.base)):
            app.chat_input(key='initial_question').set_value(a+' '+b).run()
        self.assertFalse(app.exception);self.assertFalse(app.session_state.get('request_error'))
        saved=app.session_state['history'][-1]['answer']
        self.assertEqual([t['status'] for t in saved['task_tracking']['tasks']],['answered','answered'])
        self.assertEqual(app.session_state['last_plan'],self.base['result']['plan'])
        q='Which years do we have?'
        follow=task('coverage',q,refs=[1],binding='working',cov=query('periods',inherit_working=True))
        with patch.object(router,'interpret',return_value=({'tasks':[follow]},dict(USAGE),router.charts_context(app.session_state['history'])[1])):
            app.chat_input(key='followup_question').set_value(q).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['history'][-1]['answer']['coverage']['available_periods'],list(range(2015,2025)))

if __name__=='__main__':unittest.main()
