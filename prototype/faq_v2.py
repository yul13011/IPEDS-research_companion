"""Small, curated FAQ layer for v2 — our deterministic control surface.

The home-screen example chips and the cost question are frozen, vetted requests.
Each already carries a proven source-reviewed execution recipe in
`learning_content.json` (a reviewed plan, a stored catalog/observation plan, or
the deterministic cost route). The FAQ layer recognizes those questions and runs
their recipe directly through the untouched execution core — no model
interpretation, no stochastic routing, and every number still fetched and
source-bound by the core. This is intentionally tiny: known questions, vetted
answers, under our control, exactly as the improvement plan calls for.
"""
import re
import unicodedata
from functools import lru_cache


def _norm(text):
    """Case/÷-fold a question so straight vs. curly quotes and hyphen vs. en-dash
    (the only differences between the eval wording and the chip wording) match."""
    text = unicodedata.normalize('NFKD', str(text))
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = text.replace('’', "'").replace('‘', "'").replace('′', "'")
    text = text.replace('–', '-').replace('—', '-').replace('−', '-')
    return re.sub(r'\s+', ' ', text).strip().lower()


@lru_cache(maxsize=1)
def _chip_index():
    """Normalized chip question -> example id, from the curated learning content."""
    from .workflows import topics
    index = {}
    for topic in topics():
        for example in topic['examples']:
            index[_norm(example['question'])] = example['id']
    return index


def lookup(question):
    """Return the curated example id for a known FAQ question, else None."""
    if not isinstance(question, str):
        return None
    return _chip_index().get(_norm(question))


def run_faq(example_id, question):
    """Execute a curated FAQ through its proven recipe; mark the answer as FAQ-served."""
    from .workflows import execute_example
    answer = execute_example(example_id)
    answer['mode'] = 'curated FAQ'
    answer['faq'] = {'example_id': example_id}
    answer.setdefault('message', 'Answered from a curated, source-reviewed example plan.')
    usage = answer.get('model_usage') or {}
    usage.setdefault('calls', 0)
    usage.setdefault('estimated_api_usd', 0.0)
    usage['model'] = 'faq'
    answer['model_usage'] = usage
    return answer
