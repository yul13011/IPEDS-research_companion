"""General relational-engine acceptance checks against independent source SQL."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from analysis_catalog.catalog import connection
from prototype.catalog import readonly,annual_path
from prototype.query_engine import execute,inspect,field_ref,aggregate_ref,number


def source(table,year=2024,sid='s',fields=(),filters=None,groups=(),aggregates=()):
    with connection() as db:
        release=db.execute('SELECT release_id FROM tables WHERE year=? AND table_name=? COLLATE NOCASE',(year,table)).fetchone()[0]
        defs={r['variable_name']:r['record_id'] for r in db.execute('SELECT record_id,variable_name FROM definitions WHERE release_id=? AND table_name=? COLLATE NOCASE',(release,table))}
        predicates=[]
        for col,values in (filters or {}).items():
            values=values if isinstance(values,list) else [values]
            codes=[r[0] for r in db.execute('SELECT record_id,code_value FROM source.code_values WHERE release_id=? AND table_name=? COLLATE NOCASE AND variable_name=?',(release,table,col)) if r[1] in values]
            predicates.append({'record_id':defs[col],'operator':'in' if len(values)>1 else 'eq','values':values,'code_record_ids':codes})
    s={'id':sid,'year':year,'table':table,'field_record_ids':[defs[f] for f in fields],
       'filters':predicates,'group_by_record_ids':[defs[f] for f in groups],
       'aggregates':[{'id':name,'operator':op,'record_id':defs[col] if col else None,'weight_record_id':defs[weight] if weight else None} for name,op,col,weight in aggregates]}
    return s,defs


def plan(sources,outputs,joins=(),expressions=(),institutions=('Yale',),missing='propagate',time_basis='source_period'):
    return {'version':2,'institutions':list(institutions),'source_years':list(dict.fromkeys(s['year'] for s in sources)),
        'sources':sources,'joins':list(joins),'expressions':list(expressions),'outputs':[{'reference':ref,'label':label} for ref,label in outputs],
        'missing_policy':missing,'time_basis':time_basis,'assumptions':[],'clarification_questions':[]}


def join(left,right,keys=('UNITID',),cardinality='one_to_one',period='same_period',missing='retain'):
    return {'left_source':left,'right_source':right,'left_columns':list(keys),'right_columns':list(keys),'how':'left',
        'cardinality':cardinality,'missing_keys':missing,'period_alignment':period}


def expr(name,op,inputs,groups=()):return {'id':name,'operator':op,'inputs':list(inputs),'group_by_references':list(groups)}


class QueryEngineTests(unittest.TestCase):
    def test_grouped_awards_match_source_sql(self):
        s,d=source('C2024_A',fields=['CTOTALT'],filters={'CIPCODE':'99','MAJORNUM':'1'},groups=['AWLEVEL'])
        p=plan([s],[(field_ref(d['CTOTALT'],'s'),'Awards')])
        result=execute(p,'Yale awards by degree level for July 2023–June 2024')
        with readonly(annual_path(2024)) as db:expected=list(db.execute("SELECT AWLEVEL,CTOTALT FROM C2024_A WHERE UNITID=130794 AND CIPCODE='99' AND MAJORNUM=1"))
        self.assertEqual(len(result['rows']),len(expected))
        self.assertEqual(sorted(r['value'] for r in result['rows']),sorted(r[1] for r in expected))
        self.assertTrue(all(r['groups'] for r in result['rows']))

    def test_disjoint_row_sum_and_overlap_rejection(self):
        s,d=source('SAL2024_IS',fields=['SATOTLT'],filters={'ARANK':['1','2','3']},aggregates=[('headcount','sum','SATOTLT',None)])
        p=plan([s],[(aggregate_ref('s','headcount'),'Selected-rank staff')])
        r=execute(p,'Sum Yale full-time nonmedical staff in professor, associate and assistant ranks')
        with readonly(annual_path(2024)) as db:expected=db.execute('SELECT SUM(SATOTLT) FROM SAL2024_IS WHERE UNITID=130794 AND ARANK IN (1,2,3)').fetchone()[0]
        self.assertEqual(r['rows'][0]['value'],expected)
        bad=deepcopy(s)
        s2,_=source('SAL2024_IS',fields=['SATOTLT'],filters={'ARANK':['1','7']},aggregates=[('headcount','sum','SATOTLT',None)])
        with self.assertRaisesRegex(ValueError,'overlap|totals'):execute(plan([s2],[(aggregate_ref('s','headcount'),'Bad sum')]),'Sum ranks')

    def test_one_to_one_fact_join_and_multi_step_calculation(self):
        a,da=source('ADM2024',sid='a',fields=['APPLCN','ADMSSN'])
        e,de=source('EF2024A',sid='e',fields=['EFTOTLT'],filters={'EFALEVEL':'4'})
        steps=[expr('rate','divide',[field_ref(da['ADMSSN'],'a'),field_ref(da['APPLCN'],'a')]),
               expr('yield','divide',[field_ref(de['EFTOTLT'],'e'),field_ref(da['ADMSSN'],'a')]),
               expr('product','multiply',['xrate','xyield'])]
        p=plan([a,e],[('xproduct','Enrolled / applicants')],joins=[join('a','e')],expressions=steps)
        r=execute(p,'Yale first-time enrollment divided by applicants via admission ratio times yield, fall 2024')
        with readonly(annual_path(2024)) as db:expected=db.execute('SELECT 1.0*e.EFTOTLT/a.APPLCN FROM ADM2024 a JOIN EF2024A e USING(UNITID) WHERE a.UNITID=130794 AND e.EFALEVEL=4').fetchone()[0]
        self.assertAlmostEqual(r['rows'][0]['value'],expected)
        self.assertTrue(r['join_validation'][0]['cardinality_verified'])

    def test_same_table_aliases_allow_population_comparison(self):
        a,d=source('EF2024A',sid='a',fields=['EFTOTLT'],filters={'EFALEVEL':'22'})
        b,_=source('EF2024A',sid='b',fields=['EFTOTLT'],filters={'EFALEVEL':'42'})
        p=plan([a,b],[('xdiff','Full-time minus part-time undergraduates')],joins=[join('a','b')],expressions=[expr('diff','subtract',[field_ref(d['EFTOTLT'],'a'),field_ref(d['EFTOTLT'],'b')])])
        r=execute(p,'Compare full-time and part-time Yale undergraduates in fall 2024')
        self.assertEqual(len(r['rows']),1)

    def test_cross_period_change(self):
        a,da=source('ADM2023',year=2023,sid='a',fields=['APPLCN'])
        b,db=source('ADM2024',sid='b',fields=['APPLCN'])
        p=plan([a,b],[('xgrowth','Applicant growth')],joins=[join('a','b',period='successive_periods')],expressions=[expr('growth','percent_change',[field_ref(db['APPLCN'],'b'),field_ref(da['APPLCN'],'a')])],time_basis='explicit_comparison')
        r=execute(p,'Percent change in Yale applicants from fall 2023 to fall 2024')
        with readonly(annual_path(2023)) as c:prior=c.execute('SELECT APPLCN FROM ADM2023 WHERE UNITID=130794').fetchone()[0]
        with readonly(annual_path(2024)) as c:now=c.execute('SELECT APPLCN FROM ADM2024 WHERE UNITID=130794').fetchone()[0]
        self.assertAlmostEqual(r['rows'][0]['value'],(now-prior)/prior*100)
        bad=deepcopy(p);bad['joins'][0]['period_alignment']='same_period'
        with self.assertRaisesRegex(ValueError,'different observation periods'):execute(bad,'Compare dates')
        bad=deepcopy(p);bad['expressions'][0]['inputs'].reverse()
        with self.assertRaisesRegex(ValueError,'NEW value'):execute(bad,'Percent change in Yale applicants from fall 2023 to fall 2024')
        with self.assertRaisesRegex(ValueError,'no date substitution'):execute(p,'Show applicants in fall 2025')

    def test_categories_are_labels_not_measures(self):
        s,d=source('C2024_A',fields=['CTOTALT','AWLEVEL'],filters={'CIPCODE':'99','MAJORNUM':'1'},groups=['AWLEVEL'])
        with self.assertRaisesRegex(ValueError,'Categorical codes'):inspect(plan([s],[(field_ref(d['AWLEVEL'],'s'),'Level')]),'Yale awards by award level')

    def test_model_can_submit_relational_plan_and_repair(self):
        from unittest.mock import patch,MagicMock
        from prototype.tests.test_catalog_planner import block,response
        from prototype.catalog_planner import model_catalog_plan
        s,d=source('C2024_A',fields=['CTOTALT'],filters={'CIPCODE':'99','MAJORNUM':'1'},groups=['AWLEVEL'])
        good=plan([s],[(field_ref(d['CTOTALT'],'s'),'Awards')]);bad=deepcopy(good)
        bad['outputs']=[{'reference':field_ref(d['AWLEVEL'],'s'),'label':'Invalid numeric category'}]
        with patch('anthropic.Anthropic') as cls:
            client=MagicMock();cls.return_value=client
            client.messages.create.side_effect=[response(block('submit_query_plan',bad,'bad')),response(block('submit_query_plan',good,'good'))]
            a=model_catalog_plan('Yale awards by award level')
        self.assertEqual(a['catalog_plan']['version'],2)
        self.assertEqual(len(a['validation_attempts']),1)
        self.assertTrue(a['catalog_proposal']['validation']['preflight_eligible'])

    def test_missing_institution_propagates_to_combined_mean(self):
        from unittest.mock import patch
        import prototype.query_engine as engine
        t,dt=source('COST1_2024',sid='t',fields=['TUITION3'])
        p=plan([t],[('xmean','Mean tuition')],expressions=[expr('mean','mean',[field_ref(dt['TUITION3'],'t')])],institutions=['Yale','Harvard'])
        original=engine.execute_source
        def missing(*args):
            frame,metadata,audit,names=original(*args)
            frame=frame[frame['__unitid']==130794];audit['missing_unitids']=[166027]
            return frame,metadata,audit,names
        with patch.object(engine,'execute_source',side_effect=missing):
            r=execute(p,'Mean of Yale and Harvard tuition')
            self.assertIsNone(r['rows'][0]['value'])
            self.assertEqual(r['rows'][0]['requested_rows'],2)
            p['missing_policy']='complete_cases'
            r=execute(p,'Complete-case mean of Yale and Harvard tuition')
            self.assertEqual(r['rows'][0]['value'],67250)

    def test_cross_institution_mean_and_joined_weighted_mean(self):
        t,dt=source('COST1_2024',sid='t',fields=['TUITION3'])
        e,de=source('EF2024A',sid='e',fields=['EFTOTLT'],filters={'EFALEVEL':'2'})
        p=plan([t,e],[('xmean','Weighted tuition')],joins=[join('t','e',period='explicit_comparison')],expressions=[expr('mean','weighted_mean',[field_ref(dt['TUITION3'],'t'),field_ref(de['EFTOTLT'],'e')])],institutions=['Yale','Harvard'],time_basis='explicit_comparison')
        r=execute(p,'Yale and Harvard out-of-state tuition for academic year 2024–25 weighted by fall 2024 total undergraduate headcounts')
        with readonly(annual_path(2024)) as db:
            expected=db.execute('SELECT SUM(1.0*t.TUITION3*e.EFTOTLT)/SUM(e.EFTOTLT) FROM Cost1_2024 t JOIN EF2024A e USING(UNITID) WHERE t.UNITID IN (130794,166027) AND e.EFALEVEL=2').fetchone()[0]
        self.assertAlmostEqual(r['rows'][0]['value'],expected)
        self.assertEqual(len(r['rows']),1);self.assertIsNone(r['rows'][0]['unitid'])
        p=plan([t],[('xmean','Unweighted tuition')],expressions=[expr('mean','mean',[field_ref(dt['TUITION3'],'t')])],institutions=['Yale','Harvard'])
        r=execute(p,'Simple mean of Yale and Harvard tuition')
        with readonly(annual_path(2024)) as db:expected=db.execute('SELECT AVG(TUITION3) FROM Cost1_2024 WHERE UNITID IN (130794,166027)').fetchone()[0]
        self.assertAlmostEqual(r['rows'][0]['value'],expected)

    def test_grouped_result_in_chat_and_exports(self):
        from streamlit.testing.v1 import AppTest
        from prototype.responses import finalize_answer
        from prototype.exports import csv_bytes,excel_bytes,audit_bytes
        s,d=source('C2024_A',fields=['CTOTALT'],filters={'CIPCODE':'99','MAJORNUM':'1'},groups=['AWLEVEL'])
        r=execute(plan([s],[(field_ref(d['CTOTALT'],'s'),'Awards')]),'Chart Yale awards by award level')
        answer=finalize_answer({'intent':'analyze','result':r},'Chart Yale awards by award level')
        app=AppTest.from_file(str(ROOT/'prototype/app.py'),default_timeout=60).run()
        app.session_state['main_page']='Ask & Analyze';app.session_state['history']=[{'question':'Chart Yale awards by award level','answer':answer}]
        app.run();self.assertFalse(app.exception)
        self.assertEqual(len(app.get('popover')),2)
        next(t for t in app.toggle if t.label=='Display table').set_value(True).run()
        self.assertFalse(app.exception);self.assertTrue(app.dataframe)
        self.assertTrue(csv_bytes(r));self.assertTrue(excel_bytes(r));self.assertIn(b'query_audit',audit_bytes(r))

    def test_join_rejects_many_to_many_or_hidden_keys(self):
        a,d=source('EF2024A',sid='a',fields=['EFTOTLT'],groups=['EFALEVEL'])
        b,_=source('EF2024A',sid='b',fields=['EFTOTLT'],groups=['EFALEVEL'])
        p=plan([a,b],[(field_ref(d['EFTOTLT'],'a'),'Count')],joins=[join('a','b')])
        with self.assertRaisesRegex(ValueError,'cardinality'):execute(p,'Join all enrollment rows')

    def test_weighted_salary_matches_independent_sql(self):
        s,d=source('SAL2024_IS',fields=['SA09MAT','SA09MCT'],filters={'ARANK':['1','2','3']},aggregates=[('salary','weighted_mean','SA09MAT','SA09MCT')])
        r=execute(plan([s],[(aggregate_ref('s','salary'),'Weighted nine-month salary')]),'Yale nine-month salary weighted by nine-month staff counts for professors, associate and assistant professors')
        with readonly(annual_path(2024)) as db:
            expected=db.execute('SELECT SUM(1.0*SA09MAT*SA09MCT)/SUM(SA09MCT) FROM SAL2024_IS WHERE UNITID=130794 AND ARANK IN (1,2,3)').fetchone()[0]
        self.assertAlmostEqual(r['rows'][0]['value'],expected)
        self.assertEqual(r['rows'][0]['available_rows'],3)
        wrong,_=source('SAL2024_IS',fields=['SA09MAT','SA12MCT'],filters={'ARANK':['1','2','3']},aggregates=[('salary','weighted_mean','SA09MAT','SA12MCT')])
        with self.assertRaisesRegex(ValueError,'contract periods'):execute(plan([wrong],[(aggregate_ref('s','salary'),'Bad weights')]),'Weighted salary')

    def test_salary_gender_mismatch_cannot_bypass_via_weighting_wording(self):
        for value,weight in [('SA09MAM','SA09MCT'),('SA09MAT','SA09MCM'),('SA09MAW','SA09MCT')]:
            s,d=source('SAL2024_IS',fields=[value,weight],filters={'ARANK':['1','2','3']},groups=['ARANK'])
            p=plan([s],[('xsalary','Salary')],expressions=[expr('salary','weighted_mean',[field_ref(d[value],'s'),field_ref(d[weight],'s')])])
            with self.assertRaisesRegex(ValueError,'populations differ'):
                execute(p,'Yale salary weighted by nine-month staff counts')
            p['expressions']=[expr('product','multiply',[field_ref(d[value],'s'),field_ref(d[weight],'s')])]
            p['outputs'][0]['reference']='xproduct'
            with self.assertRaisesRegex(ValueError,'populations differ'):inspect(p,'Salary using staff weights')
        s,d=source('SAL2024_IS',fields=['SA09MAM','SA09MCM'],filters={'ARANK':['1','2','3']},aggregates=[('salary','weighted_mean','SA09MAM','SA09MCM')])
        p=plan([s],[(aggregate_ref('s','salary'),'Male salary')])
        with self.assertRaisesRegex(ValueError,'not gender-restricted'):inspect(p,'Yale weighted salary for all staff')
        result=execute(p,'Yale male salary weighted by male nine-month staff counts')
        with readonly(annual_path(2024)) as db:
            expected=db.execute('SELECT SUM(1.0*SA09MAM*SA09MCM)/SUM(SA09MCM) FROM SAL2024_IS WHERE UNITID=130794 AND ARANK IN (1,2,3)').fetchone()[0]
        self.assertAlmostEqual(result['rows'][0]['value'],expected)

    def test_original_incorrect_salary_plan_is_now_blocked(self):
        import json
        cases=json.loads((Path(__file__).parent/'fixtures/salary_population_regression.json').read_text())
        good=next(c for c in cases if c['round']==1)
        wrong=next(c for c in cases if c['round']==2)
        with self.assertRaisesRegex(ValueError,'populations differ'):inspect(wrong['plan'],wrong['question'])
        result=execute(good['plan'],good['question'])
        with readonly(annual_path(2024)) as db:
            expected=db.execute('SELECT SUM(1.0*SA09MAT*SA09MCT)/SUM(SA09MCT) FROM SAL2024_IS WHERE UNITID=130794 AND ARANK IN (1,2,3)').fetchone()[0]
        self.assertAlmostEqual(result['rows'][0]['value'],expected)

    def test_cohort_rate_and_release_year_substitution_rejection(self):
        n,d=source('GR2024',sid='n',fields=['GRTOTLT'],filters={'COHORT':'2','GRTYPE':'12'})
        den,_=source('GR2024',sid='d',fields=['GRTOTLT'],filters={'COHORT':'2','GRTYPE':'8'})
        p=plan([n,den],[('xrate','Six-year bachelor graduation rate')],joins=[join('n','d')],expressions=[expr('rate','percent',[field_ref(d['GRTOTLT'],'n'),field_ref(d['GRTOTLT'],'d')])],time_basis='cohort')
        r=execute(p,'Yale six-year bachelor graduation rate for entering cohort 2018')
        with readonly(annual_path(2024)) as db:
            counts=dict(db.execute('SELECT GRTYPE,GRTOTLT FROM GR2024 WHERE UNITID=130794 AND GRTYPE IN (8,12)'))
        self.assertAlmostEqual(r['rows'][0]['value'],100*counts[12]/counts[8])
        self.assertEqual(r['rows'][0]['entry_cohort_year'],2018)
        with self.assertRaisesRegex(ValueError,'Cohort timing'):execute(p,'Yale graduation rate for entering cohort 2024')

    def test_reducer_does_not_double_count_joined_scalar(self):
        e,de=source('EF2024A',sid='e',fields=['EFTOTLT'],groups=['EFALEVEL'])
        a,da=source('ADM2024',sid='a',fields=['APPLCN'])
        p=plan([e,a],[('xbad','Applicants')],joins=[join('e','a',cardinality='many_to_one')],expressions=[expr('bad','sum',[field_ref(da['APPLCN'],'a')],['institution'])])
        with self.assertRaisesRegex(ValueError,'replicated this input grain'):execute(p,'Sum the joined applicants')

    def test_negative_financial_value_is_not_a_missing_sentinel(self):
        financial={'title':'Unrestricted net assets','long_description':'Net assets, including a deficit balance.'}
        count={'title':'Applicants total','long_description':'Number of applicants.'}
        self.assertEqual(number(-123,financial),-123)
        self.assertIsNone(number(-123,count))
        self.assertIsNone(number(-123,financial,{'-123'}))

    def test_numeric_range_filters_do_not_use_text_comparison(self):
        s,d=source('ADM2024',fields=['APPLCN'])
        s['filters']=[{'record_id':d['APPLCN'],'operator':'gt','values':['50000'],'code_record_ids':[]}]
        r=execute(plan([s],[(field_ref(d['APPLCN'],'s'),'Applicants')]),'Yale applicants greater than 50000')
        self.assertTrue(r['rows'][0]['value']>50000)


if __name__=='__main__':unittest.main()

