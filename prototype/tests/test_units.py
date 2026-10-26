"""Currency display is source-bound, shared, and never rescales analytical data."""
from copy import deepcopy
from pathlib import Path
from io import BytesIO
import json,sys,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.tests.test_query_engine import source,plan,field_ref
from prototype.query_engine import execute
from prototype.catalog import readonly,annual_path
from prototype.units import display_result,monetary_evidence,UNVERIFIED
from prototype.responses import summarize,value_text,presentation_for
from prototype.charts import panels,prepare
from prototype.exports import csv_bytes,excel_bytes,audit_bytes


def real_result(table,field,filters=None):
    s,d=source(table,fields=[field],filters=filters)
    return execute(plan([s],[(field_ref(d[field],'s'),field)],
                        institutions=('Mount Holyoke College','Yale','Harvard')),field+' at selected institutions')


class UnitTests(unittest.TestCase):
    def test_real_salary_outlays_averages_tuition_finance_and_exports(self):
        import pandas as pd
        from openpyxl import load_workbook
        for table,field,filters in [('SAL2024_IS','SAOUTLT',{'ARANK':'7'}),
                ('SAL2024_IS','SAEQ9AT',{'ARANK':'7'}),('COST1_2024','TUITION3',None),
                ('F2324_F2','F2E131',None)]:
            with self.subTest(field=field):
                result=real_result(table,field,filters);before=deepcopy(result)
                view=display_result(result)
                self.assertEqual({r['unit'] for r in view['rows']},{'USD'})
                self.assertEqual(display_result(view),view)
                for row in view['rows']:
                    with readonly(annual_path(2024)) as db:
                        sql=f'SELECT "{field}" FROM "{table}" WHERE UNITID=?'+(' AND ARANK=7' if filters else '')
                        expected=db.execute(sql,(row['unitid'],)).fetchone()[0]
                    self.assertEqual(row['value'],float(expected))
                    self.assertTrue(value_text(row).startswith('$'))
                if field=='SAOUTLT':self.assertEqual(next(r['value'] for r in view['rows'] if r['unitid']==166939),27792003)
                self.assertIn('$',summarize(result));self.assertNotIn('monetary amount',summarize(result))
                frame,_=prepare(result)
                self.assertTrue(all(v.startswith('$') for v in frame.display_value))
                for panel in panels(result,presentation_for(result)):
                    self.assertEqual(panel['unit'],'USD')
                    self.assertIn('US dollars (USD)',json.dumps(panel['chart'].to_dict()))
                exported=pd.read_csv(BytesIO(csv_bytes(result)))
                self.assertEqual(set(exported.unit),{'USD'});self.assertEqual(set(exported.currency_scale),{1})
                self.assertEqual(exported.value.tolist(),[r['value'] for r in result['rows']])
                wb=load_workbook(BytesIO(excel_bytes(result)),data_only=True)
                values=list(wb['Data'].values);columns=values[0]
                self.assertTrue(all(r[columns.index('unit')]=='USD' for r in values[1:]))
                self.assertTrue(all(r[columns.index('currency_scale')]==1 for r in values[1:]))
                for target in [result,view]:
                    audit=json.loads(audit_bytes(target));self.assertEqual(audit['rows'],result['rows'])
                    self.assertTrue(audit['display_units'])
                self.assertEqual(result,before)

    def test_scale_uncertainty_conflicts_and_nonmoney(self):
        base={'rows':[{'metric':'m','observation_year':2024,'unit':'monetary amount','value':1234,'status':'ok'}],
              'sources':[{'metric':'m','year':2024,'table':'OTHER','codebook_evidence':[
                  {'record_id':1,'variable_name':'x','title':'Salary outlays','long_description':'Amount in thousands of US dollars'}]}]}
        view=display_result(base)
        self.assertEqual(view['rows'][0]['unit'],'USD (thousands)')
        self.assertEqual(view['rows'][0]['value'],1234)
        self.assertEqual(value_text(view['rows'][0]),'$1,234 thousand')
        for text in ['Salary outlays in thousands','Salary outlays ($000)']:
            base['sources'][0]['table']='SAL2024_IS'
            base['sources'][0]['codebook_evidence'][0]['long_description']=text
            self.assertEqual(display_result(base)['rows'][0]['currency_scale'],1000)
        base['sources'][0]['table']='OTHER'
        base['sources'][0]['codebook_evidence'][0]['long_description']='Amount in millions of US dollars'
        self.assertEqual(display_result(base)['rows'][0]['unit'],'USD (millions)')
        base['sources'][0]['codebook_evidence'][0]['long_description']='Salary expense'
        self.assertEqual(display_result(base)['rows'][0]['unit'],UNVERIFIED)
        self.assertNotIn('$',value_text(display_result(base)['rows'][0]))
        base['sources'][0]['table']='SAL2024_IS'
        base['sources'][0]['codebook_evidence'][0]['long_description']='Canadian dollars'
        self.assertEqual(display_result(base)['rows'][0]['unit'],UNVERIFIED)
        base['sources'][0]['codebook_evidence']=[
            {'title':'Salary dollars','long_description':'US dollars'},
            {'title':'Salary dollars','long_description':'thousands of US dollars'}]
        self.assertEqual(display_result(base)['rows'][0]['unit'],UNVERIFIED)
        for unit in ['percent','employees','FTE']:
            base['rows'][0]['unit']=unit
            self.assertEqual(display_result(base)['rows'],base['rows'])
        base['rows'][0].update(unit='dollars',value=None,status='missing')
        self.assertEqual(value_text(display_result(base)['rows'][0]),'not reported')

    def test_actual_table_ui_uses_dollars_for_saved_result(self):
        from streamlit.testing.v1 import AppTest
        result=real_result('SAL2024_IS','SAOUTLT',{'ARANK':'7'})
        before=deepcopy(result)
        def app():
            import streamlit as st
            from prototype.components import render_result
            render_result(st.session_state['currency_result'],'currency',show_chart=False)
        app=AppTest.from_function(app,default_timeout=60)
        app.session_state['currency_result']=result;app.run()
        self.assertFalse(app.exception)
        table=app.dataframe[0].value
        self.assertTrue(all(v.startswith('$') for v in table['Value']))
        self.assertFalse(any('monetary amount' in v for v in table['Value']))
        self.assertIn('$27,792,003',table['Value'].tolist())
        self.assertEqual(app.session_state['currency_result'],before)


if __name__=='__main__':unittest.main()
