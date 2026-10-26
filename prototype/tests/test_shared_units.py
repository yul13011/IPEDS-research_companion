"""Source-backed unit repairs and unchanged numeric/audit behavior."""
from pathlib import Path
from copy import deepcopy
import sys,json,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from analysis_catalog.catalog import connection,table_context
from prototype.unit_metadata import resolve
from prototype.field_semantics import describe_field,compatible


def definition(table,variable,year=2024):
    with connection() as db:
        row=db.execute('SELECT d.*,v.title,v.long_description,v.format,v.data_type FROM definitions d JOIN source.variable_docs v USING(record_id) WHERE d.release_id LIKE ? AND d.table_name=? AND d.variable_name=?',(f'IPEDS_{year}-%',table,variable)).fetchone()
    d=dict(row);return d,table_context(d['release_id'],table)


class SharedUnitTests(unittest.TestCase):
    def test_quantities_are_not_population_or_percentile(self):
        cases=[('ADM2024','SATVR25','score'),('ADM2024','ACTCM75','score'),
            ('EFIA2024','CDACTUA','credit hours'),('EFIA2024','CDACTGA','credit hours'),
            ('EF2024D','STUFACR','ratio'),('DRVEF2024','ENRTOT','students'),
            ('EF2024D','RET_PCF','percent'),('DRVGR2024','GRRTTOT','percent'),
            ('SFA2324','UDGPGRNTN','students'),('C2024_B','CSTOTLT','students'),
            ('SFA2324','UNDPGRNTN','students'),('GR2024_L2','PGLIN11','students'),
            ('C2024_B','CSNRALT','students'),('AL2024','LBRANCH','libraries'),
            ('AL2024','LILLDRC','transactions'),('S2024_NH','HRTOTLT','employees'),
            ('C2024_A','CTOTALT','awards'),('HD2024','NEWID','identifier')]
        for table,var,unit in cases:
            with self.subTest(variable=var):
                d,t=definition(table,var);r=resolve(d,t)
                self.assertEqual(r['unit'],unit);self.assertEqual(r['status'],'verified')
                self.assertTrue(r['evidence'][0]['excerpt'])
                self.assertEqual(describe_field(d,t)['unit'],unit)

    def test_all_releases_staff_rank_unit_and_scores(self):
        for year in range(2015,2025):
            for var in ['SISPROF','SISASCP','SISASTP','SISINST','SISLECT','SISNORK','SISTOTL']:
                d,t=definition(f'S{year}_SIS',var,year)
                self.assertEqual(resolve(d,t)['unit'],'employees',(year,var))
            d,t=definition(f'ADM{year}','SATVR25',year)
            self.assertEqual(resolve(d,t)['unit'],'score')

    def test_unknown_and_codes_cannot_authorize_arithmetic(self):
        d,t=definition('S2024_SIS','SISINST')
        unknown={**d,'variable_name':'MYSTERY','title':'Unknown measurement','long_description':'A source value.'}
        a=describe_field(unknown,{})
        self.assertEqual(a['unit'],'unknown');self.assertFalse(a['additive'])
        self.assertFalse(compatible(a,describe_field(d,t))[0])
        coded={**d,'category_count':2,'title':'Employee indicator'}
        self.assertEqual(resolve(coded,t)['unit'],'coded')
        self.assertFalse(describe_field(coded,t)['additive'])
        # A table's incidental mention of staff cannot define a mystery value.
        self.assertEqual(resolve(unknown,{'population_evidence':[{'description':'The table includes staff and students.','record_id':1}]})['unit'],'unknown')

    def test_currency_scales_and_prepared_catalog_freshness(self):
        d,t=definition('F2324_F2','F2E131')
        plain={**d,'title':'Salary dollars','long_description':'Salary in US dollars.'}
        scaled={**plain,'long_description':'Salary in thousands of US dollars.'}
        self.assertFalse(compatible(describe_field(plain,t),describe_field(scaled,t))[0])
        foreign={**plain,'long_description':'Salary in Canadian dollars.'}
        self.assertFalse(compatible(describe_field(plain,t),describe_field(foreign,t))[0])
        self.assertEqual(resolve(scaled,t)['scale'],1000)
        # Reusing a record ID with changed evidence must not reuse its cached unit.
        changed={**d,'title':'Unknown measurement','long_description':'A source value.'}
        self.assertEqual(resolve(changed,{})['unit'],'unknown')

    def test_saved_smith_units_chart_and_audit_preserve_originals(self):
        from prototype.units import display_result
        from prototype.responses import presentation_for
        from prototype.charts import prepare,panels
        from prototype.exports import csv_bytes,audit_bytes
        a=json.loads((ROOT/'evaluations/smith_rank_display_trace.json').read_text(encoding='utf-8'))
        r=a['result'];before=deepcopy(r);view=display_result(r)
        self.assertEqual({x['unit'] for x in view['rows']},{'employees'})
        self.assertEqual(r,before);self.assertEqual(display_result(view),view)
        self.assertEqual([x['value'] for x in view['rows']],[x['value'] for x in r['rows']])
        p=presentation_for(r,a['catalog_proposal']['question'])
        self.assertEqual(p['chart_type'],'bar')
        frame,_=prepare(r);self.assertEqual(int(frame.total_panel.sum()),1)
        self.assertEqual(len(panels(r,p)),2)
        self.assertIn(b'unit_metadata',csv_bytes(r))
        self.assertEqual(json.loads(audit_bytes(view))['rows'][3]['unit'],'source units')

    def test_real_smith_reexecution_uses_same_verified_units(self):
        from prototype.catalog_planner import proposal_answer
        from prototype.catalog_execution import execute_catalog
        a=json.loads((ROOT/'evaluations/smith_rank_display_trace.json').read_text(encoding='utf-8'))
        q="show Smith College's Full-time instructional staff by academic rank"
        fresh=execute_catalog(proposal_answer(a['catalog_plan'],q),q)
        self.assertIn('result',fresh,fresh.get('message'))
        self.assertEqual({x['unit'] for x in fresh['result']['rows']},{'employees'})
        self.assertEqual([r['value'] for r in fresh['result']['rows']],[r['value'] for r in a['result']['rows']])
        self.assertEqual(fresh['presentation']['chart_type'],'bar')
        (ROOT/'evaluations/smith_rank_units_fixed.json').write_text(json.dumps(fresh,indent=2,default=str),encoding='utf-8')

    def test_old_derived_results_need_revalidation_without_changing_values(self):
        from prototype.units import display_result
        from prototype.exports import audit_bytes
        r={'rows':[{'metric':'xold','observation_year':2024,'unit':'percent','value':42}],
           'sources':[{'metric':'xold','year':2024,'formula':{'expressions':[{'operator':'percent'}]}}]}
        before=deepcopy(r);view=display_result(r)
        self.assertEqual(view['rows'][0]['unit'],'unknown')
        self.assertEqual(view['rows'][0]['unit_metadata']['status'],'requires_revalidation')
        self.assertEqual(view['rows'][0]['value'],42);self.assertEqual(r,before)
        self.assertEqual(json.loads(audit_bytes(view))['rows'][0]['unit'],'percent')

    def test_ui_cannot_force_an_unresolved_measurement_axis(self):
        from streamlit.testing.v1 import AppTest
        from unittest.mock import patch
        a=json.loads((ROOT/'evaluations/smith_rank_units_fixed.json').read_text(encoding='utf-8'))
        from prototype.unit_metadata import VERSION
        r=deepcopy(a['result']);r['rows'][0].update(unit='unknown',unit_metadata={'version':VERSION,'unit':'unknown','status':'unresolved'})
        def app():
            import streamlit as st
            from prototype.components import render_result
            render_result(st.session_state['result'],'unresolved',show_chart=True)
        test=AppTest.from_function(app,default_timeout=60);test.session_state['result']=r
        with patch('prototype.charts.panels',side_effect=AssertionError('No unverified axis')):test.run()
        self.assertFalse(test.exception)
        self.assertTrue(any('measurement unit is unresolved' in str(c.value) for c in test.caption))
        self.assertTrue(test.dataframe)

    def test_smith_all_ranks_total_renders_without_stopiteration(self):
        from streamlit.testing.v1 import AppTest
        a=json.loads((ROOT/'evaluations/smith_rank_units_fixed.json').read_text(encoding='utf-8'))
        def app():
            import streamlit as st
            from prototype.components import render_result
            render_result(st.session_state['result'],'smith_total',show_chart=True)
        test=AppTest.from_function(app,default_timeout=60);test.session_state['result']=a['result'];test.run()
        self.assertFalse(test.exception)
        self.assertTrue(any(m.value=='351' for m in test.metric))
        self.assertEqual(len(test.get('vega_lite_chart')),1)


if __name__=='__main__':unittest.main()
