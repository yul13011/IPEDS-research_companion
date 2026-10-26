"""Crowded comparisons fall back to full tables without removing source rows."""
from pathlib import Path
from copy import deepcopy
import sys,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'.packages'),str(ROOT)]
from prototype.responses import presentation_for,adjust_presentation


def result(categories=13,years=(2024,),institutions=('Southern Connecticut State University',)):
    rows=[{'institution':name,'metric':'occupation','measure':f'Occupation {i}',
        'observation_year':year,'reporting_period':f'Fall {year}','unit':'employees',
        'status':'ok','value':i,'groups':[f'Occupation: {i}'],'series_segment':str(i)}
        for name in institutions for year in years for i in range(categories)]
    return {'plan':{'metrics':['occupation'],'output':'chart'},'rows':rows,'observation_years':list(years)}


class ChartDensityTests(unittest.TestCase):
    def test_cutoff_table_and_explicit_chart_preserve_all_categories(self):
        r=result();before=deepcopy(r)
        p=presentation_for(r,'Southern Connecticut State University staff by occupation')
        self.assertEqual(p['chart_type'],'none');self.assertTrue(p['show_table'])
        self.assertIn('12 categories',p['table_reason'])
        self.assertEqual(presentation_for(result(12))['chart_type'],'bar')
        explicit=presentation_for(r,'Show a bar chart of staff by occupation')
        self.assertEqual(explicit['chart_type'],'bar');self.assertIsNone(explicit['table_reason'])
        edited=adjust_presentation('Make it a bar chart',{'result':r,'presentation':p})
        self.assertEqual(edited['presentation']['chart_type'],'bar')
        self.assertEqual(r,before)

    def test_years_and_cluster_cells_are_not_extra_categories(self):
        self.assertEqual(presentation_for(result(2,years=tuple(range(2010,2025))))['chart_type'],'line')
        self.assertEqual(presentation_for(result(3,institutions=('Yale','Harvard','Princeton')))['chart_type'],'bar')
        self.assertEqual(presentation_for(result(1,institutions=tuple(f'School {i}' for i in range(13))))['chart_type'],'none')

    def test_missing_categories_are_retained_and_units_are_separate(self):
        r=result();r['rows'][-1].update(status='missing',value=None)
        self.assertEqual(presentation_for(r)['chart_type'],'none')
        self.assertEqual(len(r['rows']),13)
        r['rows'][-1]['unit']='monetary amount'
        self.assertIsNone(presentation_for(r)['table_reason'])


if __name__=='__main__':unittest.main()
