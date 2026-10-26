"""Production aggregate acceptance, scope preservation and negative checks."""
import sys,json,unittest
from pathlib import Path
from copy import deepcopy
from io import BytesIO
from unittest.mock import patch,MagicMock
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from evaluations.run_population_engine_benchmarks import build
from prototype.tests.test_query_engine import source,plan,expr,join
from prototype.query_engine import execute,field_ref
from prototype.populations import default_population,select,aggregate_question
from prototype.catalog import readonly,annual_path

class PopulationTests(unittest.TestCase):
    def test_distance_partition_zeros_require_count_identity(self):
        from prototype.query_engine import reconcile_distance_counts
        cases=[({'EFDEEXC':10,'EFDESOM':None,'EFDENON':None,'EFDETOT':10},['EFDESOM','EFDENON']),
               ({'EFDEEXC':None,'EFDESOM':None,'EFDENON':20,'EFDETOT':20},['EFDEEXC','EFDESOM']),
               ({'EFDEEXC':4,'EFDESOM':None,'EFDENON':2,'EFDETOT':10},[]),
               ({'EFDEEXC':None,'EFDESOM':None,'EFDENON':None,'EFDETOT':None},[])]
        for values,expected in cases:
            raw=dict(values);self.assertEqual(reconcile_distance_counts(values,raw),expected)
            self.assertTrue(all(values[c]==0 for c in expected))
        values={'EFDEEXC':10,'EFDESOM':None,'EFDENON':0,'EFDETOT':10}
        self.assertEqual(reconcile_distance_counts(values,{**values,'EFDESOM':'suppressed'}),[])
        for values in [{'EFDEEXC':11,'EFDESOM':None,'EFDENON':0,'EFDETOT':10},
                       {'EFDEEXC':1,'EFDESOM':2,'EFDENON':3,'EFDETOT':10},
                       {'EFDEEXC':-1,'EFDESOM':None,'EFDENON':0,'EFDETOT':10}]:
            with self.assertRaises(ValueError):reconcile_distance_counts(values,dict(values))

    def test_distance_participation_matches_nces_and_discloses_derivation(self):
        p,_=build(42,2024);r=execute(p,'Percentage of students in any distance education in fall 2024')
        row=r['rows'][0]
        self.assertEqual(row['denominator'],20066904)
        self.assertEqual(row['numerator'],5218918+5569198)
        self.assertEqual(row['unit'],'percent')
        self.assertAlmostEqual(row['value'],53.8,delta=.05)
        self.assertGreater(r['query_audit'][0]['partition_reconciliation']['derived_zero_cells'],0)
        self.assertTrue(any('derived as zero' in w for w in r['warnings']))
        bad=deepcopy(p);bad['sources'][0]['table']='EF2024A'
        with self.assertRaises(ValueError):execute(bad,'Invalid distance partition source')

    def test_outcome_measures_eight_year_pooled_completion(self):
        from prototype.query_engine import documented_count_share
        p,_=build(200,2024);result=execute(p,'Calculate the eight-year award completion percentage')
        row=result['rows'][0]
        with readonly(annual_path(2024)) as db:
            expected=db.execute('SELECT COUNT(*),SUM(o.OMAWDN8),SUM(o.OMACHRT) FROM OM2024 o JOIN HD2024 h USING(UNITID) WHERE o.OMCHRT=50 AND h.FIPS BETWEEN 1 AND 56 AND h.PSET4FLG IN (1,3) AND h.DEGGRANT=1 AND h.SECTOR BETWEEN 1 AND 9 AND o.OMAWDN8>=0 AND o.OMACHRT>=0').fetchone()
        self.assertEqual(expected[0],3473)
        self.assertEqual((row['numerator'],row['denominator']),(expected[1],expected[2]))
        self.assertAlmostEqual(row['value'],100*expected[1]/expected[2])
        self.assertAlmostEqual(row['value'],47.3,delta=.05)
        s={'year':2024,'table':'OM2024'}
        b={'definitions':{1:{'variable_name':'OMAWDN8','title':'Number of adjusted cohort receiving an award at 8 years (August 31, 2024)','long_description':'Students from the adjusted cohort receiving an award from reporting institution.'},2:{'variable_name':'OMACHRT','title':'Adjusted 2016-17 cohort'}},'descriptors':{1:{'unit':'students'},2:{'unit':'students'}}}
        self.assertTrue(documented_count_share(b,s,s,1,2))
        b['definitions'][2]['title']='Adjusted 2015-16 cohort'
        self.assertFalse(documented_count_share(b,s,s,1,2))
        b['definitions'][2]['title']='Adjusted 2016-17 cohort'
        b['definitions'][1]['title']='Number receiving an award at 4 years (August 31, 2020)'
        self.assertFalse(documented_count_share(b,s,s,1,2))

    def test_national_count_and_pooled_rates_match_nces(self):
        expectations={1:(5626,0),3:(20066904,0),12:(624689,0),19:(61,.05),20:(64.8,.05),21:(42.7,.05),22:(71.2,.05),32:(77.9,.05),33:(46.9,.05),35:(32.4,.05),50:(100224,.5),51:(741767,0)}
        for q,(expected,tolerance) in expectations.items():
            with self.subTest(q=q):
                p,_=build(q,2024);r=execute(p,'Calculate source aggregate')
                self.assertLessEqual(abs(r['rows'][0]['value']-expected),tolerance+1e-8)
                self.assertTrue(r['population_evidence']);self.assertIsNone(r['rows'][0]['unitid'])

    def test_sector_sums_match_independent_sql_and_reconcile_national(self):
        e,de=source('EF2024',sid='e',fields=['EFTOTAL'],filters={'EFLEVEL':'10'})
        h,dh=source('HD2024',sid='h',groups=['SECTOR'])
        p=plan([h,e],[('xvalue','Enrollment')],joins=[join('h','e')],expressions=[expr('value','sum',[field_ref(de['EFTOTAL'],'e')],[field_ref(dh['SECTOR'],'h')])],institutions=[],missing='complete_cases')
        p['population']=default_population()
        result=execute(p,'National enrollment by sector in fall 2024')
        with readonly(annual_path(2024)) as db:
            expected=[r[0] for r in db.execute('SELECT SUM(e.EFTOTAL) FROM EF2024 e JOIN HD2024 h USING(UNITID) WHERE e.EFLEVEL=10 AND h.PSET4FLG IN (1,3) AND h.FIPS BETWEEN 1 AND 56 AND h.SECTOR BETWEEN 1 AND 9 GROUP BY h.SECTOR')]
        self.assertEqual(sorted(r['value'] for r in result['rows']),sorted(expected))
        self.assertEqual(sum(r['value'] for r in result['rows']),20066904)
        self.assertTrue(all(r['groups'] for r in result['rows']))
        from prototype.responses import presentation_for
        self.assertEqual(presentation_for(result)['chart_type'],'bar')

    def test_annual_trend_source_binding_and_intent(self):
        from prototype.intent_checks import CURRENT,contract
        p,_=build(3,2024);p['annual_years']=[2022,2023,2024]
        token=CURRENT.set(contract('National total enrollment trend from 2022 through 2024'))
        try:r=execute(p,'National total enrollment trend from 2022 through 2024')
        finally:CURRENT.reset(token)
        self.assertEqual([x['value'] for x in r['rows']],[18954628,19426353,20066904])
        self.assertEqual(len({x['metric'] for x in r['rows']}),1)
        self.assertEqual(set(r['population_evidence']),{2022,2023,2024})
        bad=deepcopy(p);bad['annual_years']=[2024,2025]
        with self.assertRaises(ValueError):execute(bad,'National enrollment trend')

    def test_unweighted_tuition_and_revenues(self):
        for q,expected,tol in [(13,553403556,.5),(15,327348748,.5),(17,20101654,.5),(207,12116,.5)]:
            with self.subTest(q=q):
                p,scale=build(q,2024);self.assertLessEqual(abs(execute(p,'Source aggregate')['rows'][0]['value']*scale-expected),tol)

    def test_scope_and_raw_output_substitution_rejected(self):
        p,_=build(3,2024)
        bad=deepcopy(p);bad['institutions']=['Yale']
        with self.assertRaises(ValueError):execute(bad,'National enrollment')
        bad=deepcopy(p);bad['population']['fips']=[]
        with self.assertRaises(ValueError):execute(bad,'National enrollment')
        bad=deepcopy(p);bad['population']['controls']=[2]
        with self.assertRaisesRegex(ValueError,'public/private'):execute(bad,'Enrollment at public institutions')
        bad=deepcopy(p);bad['population']['fips']=[9]
        with self.assertRaisesRegex(ValueError,'geography'):execute(bad,'Enrollment in Massachusetts')
        bad=deepcopy(p);bad['expressions']=[];bad['outputs'][0]['reference']=field_ref(bad['sources'][0]['field_record_ids'][0],'s')
        with self.assertRaisesRegex(ValueError,'must be aggregates'):execute(bad,'National enrollment')
        with self.assertRaisesRegex(ValueError,'grouping'):execute(p,'National enrollment by sector')
        self.assertFalse(aggregate_question('Show us Yale enrollment'))

    def test_cannot_sum_institutional_rates(self):
        s,d=source('EF2024D',fields=['RET_PCF'])
        p=plan([s],[('xvalue','Bad total')],expressions=[expr('value','sum',[field_ref(d['RET_PCF'],'s')])],institutions=[])
        p['population']=default_population()
        with self.assertRaisesRegex(ValueError,'nonadditive|rates'):execute(p,'National retention')

    def test_pooled_missing_pair_excluded_from_both_counts(self):
        import prototype.query_engine as engine
        p,_=build(32,2024);original=engine.execute_source
        def missing(*args):
            frame,meta,audit,names=original(*args);ref=next(k for k,v in meta.items() if p['sources'][0]['field_record_ids'][0] in v['record_ids'])
            frame.loc[frame.index[0],ref]=None
            return frame,meta,audit,names
        with patch.object(engine,'execute_source',side_effect=missing):r=execute(p,'National retention')
        self.assertIsNotNone(r['rows'][0]['value']);self.assertGreater(r['rows'][0]['denominator'],0)
        self.assertTrue(any('Complete-case' in w for w in r['warnings']))

    def test_provider_route_and_exports(self):
        from prototype.tests.test_catalog_planner import block,response
        from prototype.institution_confirmation import ask
        from prototype.exports import csv_bytes,excel_bytes,audit_bytes
        from openpyxl import load_workbook
        p,_=build(3,2024)
        with patch('anthropic.Anthropic') as cls:
            cls.return_value.messages.create.return_value=response(block('submit_query_plan',p))
            answer=ask('National total enrollment in fall 2024',use_model=True)
        self.assertEqual(answer['result']['rows'][0]['value'],20066904)
        self.assertEqual(cls.return_value.messages.create.call_count,1)
        r=answer['result'];self.assertIn(b'20066904',csv_bytes(r));self.assertIn(b'population_evidence',audit_bytes(r))
        wb=load_workbook(BytesIO(excel_bytes(r)),read_only=True)
        self.assertIn('Aggregate scope',wb.sheetnames);self.assertEqual(wb['Population reporting units'].max_row,5627)

    def test_alias_reference_normalization_retains_exact_field(self):
        p,_=build(3,2024);p['sources'][0]['id']='s1'
        rid=p['sources'][0]['field_record_ids'][0];p['expressions'][0]['inputs']=[f'f1_{rid}']
        r=execute(p,'National enrollment');self.assertEqual(r['rows'][0]['value'],20066904)
        self.assertEqual(r['catalog_plan']['expressions'][0]['inputs'],[f'fs1_{rid}'])
        self.assertTrue(any('Normalized' in n for n in r['catalog_plan']['assumptions']))

    def test_entering_cohort_is_bound_from_source_evidence(self):
        from prototype.intent_checks import CURRENT,contract
        p,_=build(20,2024);p['time_basis']='cohort'
        question='National bachelor graduation rate for entering cohort 2018'
        token=CURRENT.set(contract(question))
        try:r=execute(p,question)
        finally:CURRENT.reset(token)
        self.assertEqual(r['rows'][0]['entry_cohort_year'],2018)
        self.assertEqual(r['rows'][0]['observation_year'],2024)
        with self.assertRaisesRegex(ValueError,'exactly'):execute(p,'National graduation rate for entering cohort 2017')

    def test_known_discrepancy_blocks_method_not_named_queries(self):
        import prototype.population_review as review
        p,_=build(3,2024);key=review.fingerprint(p)
        policy=MagicMock();policy.exists.return_value=True;policy.read_text.return_value=json.dumps({'blocked':{key:{'source_year':2024}}})
        with patch.object(review,'POLICY',policy):
            with self.assertRaisesRegex(ValueError,'under review'):execute(p,'National enrollment')
            named=deepcopy(p);named.pop('population');named['institutions']=['Yale']
            result=execute(named,'Yale enrollment')
            self.assertEqual(result['query_audit'][0]['requested_unitids'],[130794])
            self.assertGreater(result['rows'][0]['value'],0)

    def test_named_scope_is_not_silently_dropped(self):
        p,_=build(3,2024)
        with self.assertRaisesRegex(ValueError,'named institution'):execute(p,'Compare national enrollment with Yale University')
        self.assertFalse(aggregate_question('How many students attend United States University?'))

if __name__=='__main__':unittest.main()
