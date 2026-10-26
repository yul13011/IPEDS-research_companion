"""Topic availability answers use local source metadata, not statistical values."""
from pathlib import Path
import json,sys,time,unittest
from copy import deepcopy
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.discovery import overview,period_text,survey_blocks,group_tables,validate_topics,topic,stable_title


class DiscoveryTests(unittest.TestCase):
    def test_generic_college_word_does_not_dilute_specific_topic(self):
        question='what data do we have about college tuition'
        self.assertEqual(topic(question),'tuition')
        self.assertEqual(topic('what information do you have on university tuition'),'tuition')
        self.assertEqual(topic('what data do we have on college'),'college')
        answer=overview(question)
        self.assertTrue(any('tuition' in i['title'].casefold() or 'student charges' in i['title'].casefold() for i in answer['discovery']['topics']))

    def test_exact_survey_groups_and_different_periods(self):
        years=['Academic year 2020-21','Academic year 2021-22','Academic year 2022-23']
        def item(title,survey,periods):return {'title':title,'survey':survey,'periods':periods,'fields':[]}
        items=[item('Directory','Institutional Characteristics',years),item('Mission','Institutional Characteristics',years),item('Branches','Institutional Characteristics',years[1:]),item('Library','Academic Libraries',['Fiscal year 2022']),item('Distinct survey','Institutional characteristics',years)]
        blocks=survey_blocks(items)
        self.assertEqual(len(blocks),3)
        self.assertIn('unless noted',blocks[0])
        self.assertIn('2020-21 through Academic year 2022-23',blocks[0])
        self.assertIn('**Branches** — Reporting periods: Academic year 2021-22; Academic year 2022-23.',blocks[0])
        self.assertIn('- **Mission**.',blocks[0])
        example=item('Directory.','Institutional Characteristics',years)
        example['fields']=['Status of institution.','Date institution closed']
        self.assertIn('- **Directory**.  \n  Example fields: Status of institution; Date institution closed.',survey_blocks([example])[0])
        self.assertNotIn('Library',blocks[0])
        self.assertEqual(period_text(['Fall 2020','Fall 2022','Fall 2023']),'Fall 2020; Fall 2022; Fall 2023')
        self.assertEqual(period_text(['2019-20','Fiscal year 2020','Fiscal year 2021']),'2019-20; Fiscal year 2020; Fiscal year 2021')
        answer=overview('what data do we have on the institution characteristics')
        self.assertEqual(answer['message'].count('**Survey: Institutional Characteristics**'),1)

    def test_graduation_annual_versions_and_cohort_coverage(self):
        answer=overview('What data do we have on graduation rates?')
        items=answer['discovery']['topics']
        within200=[i for i in items if '200%' in i['title']]
        self.assertEqual(len(within200),1)
        self.assertEqual(len(within200[0]['releases']),10)
        self.assertEqual(len(within200[0]['tables']),10)
        self.assertIn('2006; 2008 through 2016',within200[0]['cohorts'])
        self.assertNotIn('2007',within200[0]['cohorts'])
        self.assertNotIn('cohort year',answer['message'])
        self.assertIn('Outcome dates',answer['message'])
        self.assertIn('August 31: 2015 through 2024',answer['message'])
        self.assertNotIn('..',answer['message'])
        self.assertTrue(any('4-year, 2-year institutions' in i['title'] and '150%' in i['title'] for i in items))
        self.assertTrue(any('less-than-2-year institutions' in i['title'] for i in items))
        for item in items:
            self.assertTrue(item['fields'],item['title'])
            self.assertNotRegex(item['title'],r'\b(?:19|20)\d{2}\b')
        validate_topics(items,answer['evidence'])
        bad=deepcopy(items);bad[0]['periods']=bad[0]['periods'][:-1]
        with self.assertRaises(ValueError):validate_topics(bad,answer['evidence'])
        with self.assertRaises(ValueError):validate_topics(items+[items[0]],answer['evidence'])
        bad=deepcopy(items);bad[0]['fields'][0]='Unverified example field'
        with self.assertRaises(ValueError):validate_topics(bad,answer['evidence'])

    def test_metadata_and_schema_grouping_is_conservative(self):
        self.assertEqual(stable_title({'title':'Frequently used derived variables (EF): Fall enrollment 2024','year_coverage':'Fall 2024','release_id':'IPEDS_2024-25_Provisional'}),'Frequently used derived variables (EF)')
        def row(year,table,percent=200,population='4-year'):
            return {'release_id':f'IPEDS_{year}-release','table_name':table,'survey':'Graduation Rates','title':f'Graduation rate data, {percent}% of normal time - cohort year {year-8} ({population})','year_coverage':f'Status of student as of August 31, {year}'}
        rows=[row(2020,'GR200_20'),row(2021,'GR200_21'),row(2021,'GR2021',150),row(2022,'GR2022_L2',200,'less-than-2-year')]
        schemas={(r['release_id'],r['table_name']):{'UNITID','COHORT','COMPLETERS'} for r in rows}
        groups=group_tables(rows,schemas)
        self.assertEqual(sorted(map(len,groups)),[1,1,2])
        changed=row(2022,'GR200_22');rows.append(changed)
        schemas[(changed['release_id'],changed['table_name'])]={'UNITID','DIFFERENT_UNIT','DIFFERENT_POPULATION'}
        self.assertEqual(sorted(map(len,group_tables(rows,schemas))),[1,1,1,2])

    def test_examples_retrieved_for_each_selected_feature(self):
        for topic in ['expenses','institution characteristics','academic libraries']:
            answer=overview('What data do we have on '+topic+'?')
            self.assertTrue(answer['discovery']['topics'])
            references={r['record_id']:r for r in answer['evidence']}
            for item in answer['discovery']['topics']:
                self.assertTrue(item['fields'],item['title'])
                self.assertEqual(len(item['fields']),len(item['field_record_ids']))
                for record_id in item['field_record_ids']:
                    self.assertTrue(references[record_id]['physical_column_present'])
                self.assertNotRegex(item['title'],r'\b(?:19|20)\d{2}\b')

    def test_real_topics_and_latency(self):
        timings=[]
        for topic in ['faculty','enrollment','financial aid','institutional finances','graduation rates']:
            start=time.perf_counter();answer=overview('What data do we have on '+topic+'?')
            self.assertTrue(answer['discovery']['topics'],topic)
            self.assertNotIn('result',answer)
            self.assertNotIn('numerical execution still pending',answer['message'])
            self.assertNotIn('Tables:',answer['message'])
            for item in answer['discovery']['topics']:
                self.assertTrue(item['record_ids']);self.assertTrue(item['tables'])
                self.assertTrue(item['periods'])
            timings.append({'topic':topic,'answer_ready_seconds':time.perf_counter()-start,'model_calls':0})
        (ROOT/'evaluations/discovery_latency.json').write_text(json.dumps({'scope':'Local metadata discovery; no model or statistical queries, excludes browser rendering. Single run per topic.','cases':timings},indent=2),encoding='utf-8')

    def test_year_scope_unknown_topic_and_empty_topic(self):
        answer=overview('What data do we have on faculty from 2020 through 2022?')
        self.assertEqual(answer['discovery']['requested_release_years'],[2020,2021,2022])
        self.assertTrue(answer['discovery']['topics'])
        for item in answer['discovery']['topics']:
            self.assertEqual(len(item['releases']),3)
        unknown=overview('What data do we have on xylophoniczebras?')
        self.assertFalse(unknown['discovery']['topics'])
        self.assertIn('does not establish',unknown['message'])
        self.assertEqual(overview('What data do we have?')['intent'],'guide')
        self.assertFalse(overview('What data do we have on faculty in 2035?')['discovery']['topics'])

    def test_discovery_skips_analytical_and_identity_planning(self):
        from prototype.institution_confirmation import ask
        from prototype.agent import ask as direct
        with patch('prototype.institution_confirmation.mentions',side_effect=AssertionError('No institution clarification for catalog discovery')),patch('prototype.agent.model_plan',side_effect=AssertionError('No statistical plan')),patch('prototype.agent.execute',side_effect=AssertionError('No fact query')),patch('prototype.conversation.resolve',side_effect=AssertionError('Explicit discovery is a new topic')):
            for route in [ask,direct]:
                answer=route('What data do we have on faculty?',use_model=False,conversation=[{'question':'Yale applicants','answer':{'message':'Earlier analysis'}}])
                self.assertEqual(answer['mode'],'data discovery')
                self.assertTrue(answer['discovery']['topics'])
                self.assertEqual(answer['latency']['live_model_calls'],0)

    def test_readable_answer_with_optional_sources_in_chat(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        app.session_state['use_ai']=False
        app.button(key='nav_ask').click().run()
        app.chat_input(key='initial_question').set_value('What data do we have on faculty?').run()
        self.assertFalse(app.exception)
        answer=app.session_state['history'][-1]['answer']
        self.assertEqual(answer['mode'],'data discovery')
        self.assertTrue(any(p.proto.popover.label=='Definitions & sources' for p in app.get('popover')))
        self.assertNotIn('result',answer)


if __name__=='__main__':unittest.main()
