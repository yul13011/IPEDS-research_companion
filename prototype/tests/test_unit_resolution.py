"""Long-definition/section evidence and institution-specific program units."""
from pathlib import Path
from copy import deepcopy
import json,sqlite3,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.tests.test_shared_units import definition
from prototype.semantics import resolve
from prototype.semantics import display_result
from prototype.catalog import readonly,annual_path


class ResolutionTests(unittest.TestCase):
    def test_definition_and_section_resolutions(self):
        cases=[('F2324_F1A','F1A07','monetary amount'),('F2324_F1A','F1E04','monetary amount'),
            ('F2324_F2','F2D092','monetary amount'),('F2324_F3','F3C03','monetary amount'),
            ('SAL2024_NIS','SANIT02','monetary amount'),('AL2024','LEXOMPS','monetary amount'),
            ('DRVC2024','BASDEG','awards'),('COST1_2024','ROOMCAP','students'),
            ('COST1_2024','MEALSWK','meals per week'),('COST1_2024','APPLFEEG','monetary amount'),
            ('COST1_2024','LNAYWK1','weeks'),('HD2024','UEIS','identifier')]
        cases.append(('COST1_2024','WKCMP1','weeks'))
        for table,var,unit in cases:
            with self.subTest(variable=var):
                d,t=definition(table,var);assignment=resolve(d,t)
                self.assertEqual(assignment['unit'],unit);self.assertEqual(assignment['status'],'verified')
                self.assertTrue(assignment['evidence'][0]['excerpt'])

    def test_shorthand_finance_sections_are_exact_source_evidence(self):
        d,t=definition('F1415_F2','F2E017',2015)
        assignment=resolve(d,t)
        self.assertEqual(assignment['unit'],'monetary amount')
        self.assertTrue(any(e['excerpt']=='sectiontitle: Expenses by functional and natural classification' for e in assignment['evidence']))
        forged={**d,'title':'Mystery value','long_description':'Unspecified measurement.'}
        self.assertEqual(resolve(forged,{})['status'],'unresolved')

    def test_previous_unresolved_batch_has_no_unexamined_unknowns(self):
        with sqlite3.connect(ROOT/'evaluations/unit_catalog_before_resolution.sqlite') as db:
            old={rid:json.loads(a) for rid,a in db.execute('SELECT record_id,assignment FROM units')}
        with sqlite3.connect(ROOT/'data/unit_catalog.proposed.sqlite') as db:
            new={rid:json.loads(a) for rid,a in db.execute('SELECT record_id,assignment FROM units')}
        batch=[rid for rid,a in old.items() if a['status']=='unresolved']
        self.assertEqual(len(batch),2484)
        self.assertTrue(all(new[rid]['status'] in {'verified','conditional'} for rid in batch))
        self.assertTrue(all(new[rid]['evidence'] for rid in batch))

    def test_credit_and_clock_hours_resolve_from_actual_rows(self):
        d,t=definition('COST1_2024','CIPLGTH2');assignment=resolve(d,t)
        self.assertEqual(assignment['status'],'conditional')
        for code,unit in [(1,'clock hours'),(2,'credit hours')]:
            with readonly(annual_path(2024)) as db:
                uid,value,raw=db.execute('SELECT UNITID,CIPLGTH2,PRGMSR2 FROM COST1_2024 WHERE PRGMSR2=? AND CIPLGTH2>0 LIMIT 1',[code]).fetchone()
            row={'metric':'program','unit':'unknown','unit_metadata':assignment,'unitid':uid,'observation_year':2024,'value':value}
            result={'rows':[row]};before=deepcopy(result);view=display_result(result)
            self.assertEqual(view['rows'][0]['unit'],unit)
            self.assertEqual(view['rows'][0]['value'],value);self.assertEqual(result,before)
            evidence=view['rows'][0]['unit_metadata']['unit_selector_evidence']
            self.assertEqual(evidence['code_value'],str(code));self.assertTrue(evidence['code_record_id'])
            self.assertEqual(display_result(view),view)
        with patch('prototype.semantics._program_unit',return_value=None):
            self.assertEqual(display_result(result)['rows'][0]['unit'],'unknown')
        d,t=definition('COST1_2024','CIPLGTH6');assignment=resolve(d,t)
        with readonly(annual_path(2024)) as db:
            uid,value=db.execute('SELECT UNITID,CIPLGTH6 FROM COST1_2024 WHERE PRGMSR6=1 AND CIPLGTH6>0 LIMIT 1').fetchone()
        row={'metric':'program6','unit':'unknown','unit_metadata':assignment,'unitid':uid,'observation_year':2024,'value':value}
        self.assertEqual(display_result({'rows':[row]})['rows'][0]['unit'],'contact hours')

    def test_first_program_length_is_not_a_student_count(self):
        d,t=definition('COST1_2024','CIPLGTH1')
        self.assertEqual(resolve(d,t)['status'],'conditional')
        self.assertEqual(resolve(d,t)['unit_selector'],'PRGMSR1')
        old,t=definition('IC2019_PY','CIPLGTH2',2019)
        self.assertEqual(resolve(old,t)['unit'],'contact hours')

    def test_relational_direct_result_resolves_program_basis(self):
        from prototype.tests.test_query_engine import source,plan,field_ref
        from prototype.query_engine import execute
        with readonly(annual_path(2024)) as db:
            uid=db.execute('SELECT UNITID FROM COST1_2024 WHERE PRGMSR2=2 AND CIPLGTH2>0 LIMIT 1').fetchone()[0]
        s,defs=source('COST1_2024',fields=['CIPLGTH2'])
        result=execute(plan([s],[(field_ref(defs['CIPLGTH2'],'s'),'Program length')],institutions=(str(uid),)),'Program length')
        self.assertEqual(result['rows'][0]['unit_metadata']['status'],'conditional')
        self.assertEqual(display_result(result)['rows'][0]['unit'],'credit hours')

    def test_new_financial_fields_display_currency_and_preserve_values(self):
        from prototype.tests.test_units import real_result
        result=real_result('F2324_F2','F2D092');before=deepcopy(result)
        view=display_result(result)
        self.assertEqual({r['unit'] for r in view['rows']},{'USD'})
        self.assertEqual(result,before)
        self.assertEqual([r['value'] for r in view['rows']],[r['value'] for r in result['rows']])

    def test_saved_old_verified_program_count_is_revalidated(self):
        d,t=definition('COST1_2024','CIPLGTH1');meta=resolve(d,t)
        with readonly(annual_path(2024)) as db:
            uid,value=db.execute('SELECT UNITID,CIPLGTH1 FROM COST1_2024 WHERE PRGMSR1=1 AND CIPLGTH1>0 LIMIT 1').fetchone()
        metric='COST1_{YEAR}::CIPLGTH1'
        old={'rows':[{'metric':metric,'observation_year':2024,'unitid':uid,'value':value,'unit':'students',
             'unit_metadata':{**meta,'version':2,'status':'verified','quantity_type':'count','unit':'students'}}],
             'sources':[{'metric':metric,'year':2024,'formula':'direct source observation',
                'codebook_evidence':[{'record_id':d['record_id'],'variable_name':'CIPLGTH1'}]}]}
        before=deepcopy(old);view=display_result(old)
        self.assertEqual(view['rows'][0]['unit'],'clock hours')
        self.assertEqual(view['rows'][0]['value'],value);self.assertEqual(old,before)
        derived={'rows':[{'metric':'xsum','unit':'students','value':value,
            'unit_metadata':{'version':1,'unit':'students','status':'verified','inputs':[old['rows'][0]['unit_metadata']]}}]}
        self.assertEqual(display_result(derived)['rows'][0]['unit_metadata']['status'],'requires_revalidation')


if __name__=='__main__':unittest.main()
