"""Chart contracts against real results: units, scope, ordering, data and gaps."""
from pathlib import Path
from copy import deepcopy
import json,sys,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.agent import ask
from prototype.analytics import execute,Plan
from prototype.charts import panels,prepare
from prototype.responses import presentation_for

class ChartTests(unittest.TestCase):
    def test_catalog_gender_trend_connects_years_and_keeps_explicit_breaks(self):
        from analysis_catalog.catalog import connection
        from prototype.catalog_planner import expand_annual_plan,proposal_answer
        from prototype.catalog_execution import execute_catalog
        with connection() as db:
            ids={r['variable_name']:r['record_id'] for r in db.execute("SELECT record_id,variable_name FROM definitions WHERE table_name='EF2024A'")}
            code=db.execute("SELECT record_id,code_value FROM source.code_values WHERE table_name='EF2024A' AND variable_name='EFALEVEL' AND value_label='All students, Undergraduate total'").fetchone()
        template={'version':1,'institutions':['Yale University'],'source_years':[2024],
            'requested_time':{'basis':'fall','description':'Fall 2015 through 2024'},
            'selections':[{'record_id':ids[f],'role':'measure'} for f in ['EFTOTLM','EFTOTLW']],
            'filters':[{'record_id':ids['EFALEVEL'],'operator':'eq','values':[code['code_value']],'code_record_ids':[code['record_id']]}],
            'group_by_record_ids':[],'calculations':[],'joins':[],'output':'chart','assumptions':[],'clarification_questions':[]}
        q='Yale undergraduates by gender from 2015 through 2024'
        plan=expand_annual_plan(template,list(range(2015,2025)))
        result=execute_catalog(proposal_answer(plan,q),q)['result']
        self.assertEqual({r['series_segment'] for r in result['rows']},{'source observations'})
        # Also repair displayed answers saved before this executor fix.
        for row in result['rows']:row['series_segment']=f"source release {row['observation_year']}"
        before=deepcopy(result)
        spec=panels(result,presentation_for(result))[0]['chart'].to_dict()
        data=next(v for v in spec['datasets'].values() if 'series_label' in v[0])
        groups={}
        for row in data:groups.setdefault((row['series_label'],row['series_segment']),[]).append(row)
        self.assertEqual(sorted(len(rows) for rows in groups.values()),[10,10])
        self.assertEqual(spec['mark']['type'],'line')
        self.assertEqual(result,before)
        for row in result['rows']:row['series_segment']='pre-2017 SAT protocol' if row['observation_year']<2017 else '2017+ SAT protocol'
        frame,_=prepare(result)
        self.assertEqual(set(frame.series_segment),{'pre-2017 SAT protocol','2017+ SAT protocol'})
        # An unavailable value stays null in the line dataset, with gap rendering.
        result['rows'][3].update(value=None,status='missing')
        spec=panels(result,presentation_for(result))[0]['chart'].to_dict()
        data=next(v for v in spec['datasets'].values() if 'series_label' in v[0])
        self.assertEqual(sum(row['plot_value'] is None for row in data),1)
        self.assertEqual(spec['mark']['invalid'],'break-paths-show-domains')

    def test_category_labels_percent_scale_and_immutability(self):
        r=ask('Show Yale undergrad population by race and ethnicity as percentages in 2024')['result']
        before=deepcopy(r);p=presentation_for(r);p['chart_type']='bar';charts=panels(r,p)
        self.assertEqual(r,before);self.assertEqual(len(charts),1)
        chart=charts[0];spec=chart['chart'].to_dict();text=json.dumps(spec)
        self.assertIn('Undergraduates by race',chart['title']);self.assertIn('Undergraduate',chart['subtitle'])
        self.assertIn('Fall',r['rows'][0]['reporting_period'])
        self.assertEqual(spec['layer'][0]['encoding']['x']['scale']['domain'],[0,100])
        self.assertGreater(spec['height'],250)
        rows=next(v for v in spec['datasets'].values() if 'display_measure' in v[0])
        self.assertTrue(any('unknown' in x['display_measure'].lower() for x in rows))
        self.assertTrue(any('nonresident' in x['display_measure'].lower() for x in rows))
        self.assertFalse(any('EFAIANT' in x['display_measure'] for x in rows))
        order=spec['layer'][0]['encoding']['y']['sort']
        values={x['display_measure']:x['plot_value'] for x in rows}
        self.assertEqual(order[0].replace('\n',' '),max(values,key=values.get))

    def test_totals_are_separate_from_categories(self):
        r=ask('Show Yale undergrad population by race and ethnicity in 2024')['result']
        p=presentation_for(r);p['chart_type']='bar';charts=panels(r,p)
        self.assertEqual(len(charts),2)
        self.assertEqual(sum(c['rows'] for c in charts),len(r['rows']))
        self.assertEqual(sum(c['total'] for c in charts),1)

    def test_many_institution_trends_share_scale_and_keep_every_row(self):
        r=execute(Plan(['admission_rate'],['Ivy League'],list(range(2015,2025))));p=presentation_for(r)
        charts=panels(r,p);self.assertEqual(len(charts),2)
        self.assertEqual(sum(c['rows'] for c in charts),len(r['rows']))
        specs=[c['chart'].to_dict() for c in charts]
        self.assertEqual(specs[0]['encoding']['y']['scale']['domain'],specs[1]['encoding']['y']['scale']['domain'])
        self.assertTrue(all(s['height']==320 for s in specs))
        self.assertTrue(all(len(s['encoding']['color']['scale']['domain'])<=4 for s in specs))
        for spec in specs:
            ordered=spec['encoding']['x']['sort'];ticks=spec['encoding']['x']['axis']['values']
            self.assertEqual(ticks,ordered)
            self.assertEqual(ticks,[str(year) for year in range(2015,2025)])
            self.assertFalse(spec['encoding']['x']['axis']['labelOverlap'])
        self.assertTrue(all(s['mark']['invalid']=='break-paths-show-domains' for s in specs))

    def test_comparison_keeps_eight_institutions_together(self):
        r=execute(Plan(['applicants'],['Ivy League'],[2024]));charts=panels(r,presentation_for(r))
        self.assertEqual(len(charts),1);self.assertEqual(charts[0]['rows'],8)

    def test_bar_followup_keeps_time_periods_distinct_and_ordered(self):
        r=execute(Plan(['applicants'],['Yale'],[2022,2023,2024]));p=presentation_for(r);p['chart_type']='bar'
        spec=panels(r,p)[0]['chart'].to_dict()
        self.assertEqual(spec['layer'][0]['encoding']['y']['sort'],['Fall 2022','Fall 2023','Fall 2024'])

    def test_multiple_category_trends_have_at_most_four_series(self):
        r=ask('Show Yale undergrad population by race and ethnicity from 2022 to 2024')['result']
        p=presentation_for(r);p['chart_type']='line';charts=panels(r,p)
        self.assertEqual(sum(c['rows'] for c in charts),len(r['rows']))
        for panel in charts:
            spec=panel['chart'].to_dict()
            rows=next(v for v in spec['datasets'].values() if 'series_label' in v[0])
            self.assertLessEqual(len({row['series_label'] for row in rows}),4)

    def test_cohort_axis_and_currency_and_signed_values(self):
        r=execute(Plan(['graduation_rate'],['Yale'],[2017,2018],time_basis='entry_cohort'))
        frame,cohort=prepare(r);self.assertTrue(cohort)
        self.assertEqual(set(frame.period_label),{'2017','2018'})
        from prototype.charts import formatted,domain
        self.assertEqual(formatted(12345,'USD'),'$12,345')
        self.assertEqual(formatted(12345,'monetary amount'),'12,345')
        self.assertEqual(formatted(56.789,'percent'),'56.8%')
        import pandas as pd
        limits=domain(pd.Series([-123,20]),'monetary amount',False,{})
        self.assertLess(limits[0],-123);self.assertGreater(limits[1],20)

    def test_result_in_chat_with_new_renderer(self):
        from streamlit.testing.v1 import AppTest
        from prototype.responses import finalize_answer
        r=ask('Show Yale undergrad population by race and ethnicity in 2024')['result']
        a=finalize_answer({'intent':'analyze','result':r});a['presentation']['chart_type']='bar'
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        app.session_state['main_page']='Ask & Analyze';app.session_state['history']=[{'question':'Race breakdown','answer':a}]
        app.run();self.assertFalse(app.exception)
        self.assertEqual(len(app.get('vega_lite_chart')),1)
        self.assertEqual(len(app.get('popover')),2)

if __name__=='__main__':unittest.main()


