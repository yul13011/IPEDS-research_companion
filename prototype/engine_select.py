"""Which interpretation engine is active for this process.

The frozen eval runner (`evaluations/run_eval_set.py`) is immutable and always
imports `intent_router.handle`. To reach the v2 resolver through that same entry
point without touching the runner, the active engine is read here — from the
`IPEDS_ENGINE` environment variable, or from the `--engine <name>` flag the
runner is invoked with (e.g. `python run_eval_set.py --engine v2`). Default v1.
"""
import os
import sys


def active_engine():
    env = os.environ.get('IPEDS_ENGINE')
    if env:
        return env.strip().lower()
    argv = sys.argv or []
    for i, tok in enumerate(argv):
        if tok == '--engine' and i + 1 < len(argv):
            return argv[i + 1].strip().lower()
        if tok.startswith('--engine='):
            return tok.split('=', 1)[1].strip().lower()
    return 'v1'
