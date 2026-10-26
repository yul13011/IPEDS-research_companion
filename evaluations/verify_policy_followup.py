"""Supplemental paired mixed-request check after a local timeout.

Separate artifact: never replaces failures from the main qualification run.
Run with --live, without concurrent regression tests.
"""
import sys
import compare_models_reliability as expanded
bench=expanded.bench

if __name__=='__main__':
    if '--live' not in sys.argv:raise SystemExit('Pass --live; incurs API charges.')
    seeds,expected=bench.fixtures()
    bench.fixtures=lambda:(seeds,expected)
    bench.CASES=[c for c in bench.CASES if c[0] in {'mixed','mixed__variation'}]
    bench.MODELS=['claude-sonnet-5-5','automatic']
    bench.TARGET=bench.ROOT/'evaluations/model_policy_followup.json'
    if '--annotation-fix' in sys.argv:bench.TARGET=bench.ROOT/'evaluations/model_policy_annotation_fix.json'
    raise SystemExit(bench.main())
