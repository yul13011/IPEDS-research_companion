"""Version 2 relational plans. Closed vocabulary, never model-authored SQL."""
def obj(properties):return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
def array(items):return {'type':'array','items':items}
STRING={'type':'string'}
INTEGER={'type':'integer'}
FILTER=obj({'record_id':INTEGER,'operator':{'type':'string','enum':['eq','in','gt','gte','lt','lte','between']},
            'values':array(STRING),'code_record_ids':array(INTEGER)})

NULL_INT={'type':['integer','null']}
AGG=obj({'id':STRING,'operator':{'type':'string','enum':['sum','mean','weighted_mean','count','count_distinct','min','max']},
         'record_id':NULL_INT,'weight_record_id':NULL_INT})
SOURCE=obj({'id':STRING,'year':INTEGER,'table':STRING,'field_record_ids':array(INTEGER),'filters':array(FILTER),
            'group_by_record_ids':array(INTEGER),'aggregates':array(AGG)})
SOURCE['properties']['reconcile_distance_partition']={'type':'boolean'}
JOIN=obj({'left_source':STRING,'right_source':STRING,'left_columns':array(STRING),'right_columns':array(STRING),
          'how':{'type':'string','enum':['left','inner']},'cardinality':{'type':'string','enum':['one_to_one','many_to_one']},
          'missing_keys':{'type':'string','enum':['retain','error']},
          'period_alignment':{'type':'string','enum':['same_period','successive_periods','explicit_comparison']}})
EXPRESSION=obj({'id':STRING,'operator':{'type':'string','enum':['add','subtract','multiply','divide','percent','percent_change','sum','mean','weighted_mean','count','min','max']},'inputs':array(STRING),'group_by_references':array(STRING)})
QUERY_SCHEMA=obj({'version':INTEGER,'institutions':array(STRING),'source_years':array(INTEGER),
    'sources':array(SOURCE),'joins':array(JOIN),'expressions':array(EXPRESSION),
    'outputs':array(obj({'reference':STRING,'label':STRING})),
    'missing_policy':{'type':'string','enum':['propagate','complete_cases']},
    'time_basis':{'type':'string','enum':['source_period','explicit_comparison','cohort']},
    'assumptions':array(STRING),'clarification_questions':array(STRING)})

REFERENCE_HELP='Field references are f<source_id>_<record_id>, aggregates a<source_id>_<aggregate_id>, and earlier expressions x<expression_id>. Self-joins use distinct source IDs. The group reference institution means UNITID. Binary arithmetic has two inputs and empty group_by_references. Reducers sum/mean/count/min/max have one input, weighted_mean has value and weight inputs. Reducer groups may include institution and categorical field refs; empty groups mean the selected institutions combined. No literals, SQL, Python or arbitrary functions.'
REFERENCE_HELP+=' Arithmetic input order: subtract=[minuend,subtrahend]; divide/percent=[numerator,denominator]; percent_change=[NEW value,OLD baseline], computed (NEW-OLD)/OLD*100. Categorical codes belong in group_by_record_ids, never in numerical outputs.'

# Optional extensions preserve existing named-institution plan compatibility.
QUERY_SCHEMA['properties']['population']=obj({'fips':array(INTEGER),'controls':array(INTEGER),'levels':array(INTEGER),
    'degree_granting':{'type':['boolean','null']},'title_iv':{'type':'boolean'},'administrative_offices':{'type':'boolean'}})
QUERY_SCHEMA['properties']['annual_years']=array(INTEGER)
REFERENCE_HELP+=' For national/sector/state aggregates use population, institutions=[], and global reducers. Population explicitly gives fips (50 states+DC for US), controls (1 public/2 private nonprofit/3 for-profit), levels (1 four-year/2 two-year/3 less-than-two-year), degree_granting (null/true/false), title_iv and administrative_offices. Do not enumerate thousands of institutions. Default US Title IV institutions exclude administrative offices; include offices only for a source-defined staff/salary scope and disclose it. Empty controls/levels mean all. Optional annual_years runs the complete one-year query independently in each requested release, checking exact annual fields/codes; source_years and sources remain the one-year template. No cross-year joins in an annual template. For pooled percentages use sum source counts separately then percent; use the same complete reporting units for numerator and denominator, never average institution percentages. For available-report aggregate results use complete_cases and retain coverage/missingness warnings. Group by sector/control/state by joining that year HD directory and grouping its coded field. No literal or fabricated weights.'
REFERENCE_HELP+=' Reference example: source id s1 and field ID 123 require fs1_123 (not f1_123); source id e requires fe_123. Reducer expression id total is referenced as xtotal.'
REFERENCE_HELP+=' Annual templates also support 1–30 named institutions instead of population; each year independently validates institution records, field ownership and category labels. Use stable output references (for example per-institution source aggregates) across annual releases to preserve the same chart series.'
REFERENCE_HELP+=' For distance-education participation, include exclusive EFDEEXC plus some EFDESOM, divided by EFDETOT; these are mutually exclusive categories, not only fully online students. Optional source reconcile_distance_partition=true requires all four exact EF A_DIST fields EFDEEXC/EFDESOM/EFDENON/EFDETOT. It derives blank component zeros only when nonnegative reported counts already sum exactly to the total; suppressed/invalid values are never filled and unresolved blanks remain missing. Do not prefilter blank components with numeric filters. This derivation is audited and disclosed.'
REFERENCE_HELP+=' National total example: sources[0].id="e", field_record_ids=[<count field>], aggregates=[]; expressions=[{id:"total",operator:"sum",inputs:["fe_<count field>"],group_by_references:[]}]; outputs=[{reference:"xtotal",label:"Total enrollment"}]. Source aggregates operate within each institution; they do NOT combine institutions. Select the numeric count, not the categorical level code. Reuse the same reducer IDs in annual templates so all years form one series. Retention pairs RET_NMF/RRFTCTA and RET_NMP/RRPTCTA refer to a prior cohort and current enrollment by definition. Aid shares ANYAIDN/SCUGFFN, UPGRNTN/SCUGRAD, UFLOANN/SCUGRAD are source count relationships; count and amount fields differ. Include all missingness/coverage in the output audit.'
