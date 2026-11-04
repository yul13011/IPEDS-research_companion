"""Optional fluent plain-language answer for v2 results.

The Companion already composes a deterministic, grounded fact summary for every
analytic answer (`responses.summarize`, surfaced as `answer['message']`). This
module adds a *fluent* rewrite of those verified facts — the feature the gradrate
prototype had — without letting the model introduce a number of its own.

Design (mirrors the discovery narrative's "rewrite, never retrieve" contract):
- Input to the model is the VERIFIED summary + the fetched rows. It only rephrases.
- A numeric-grounding guard rejects any figure in the narrative that is not present
  in the source material; on failure the caller falls back to the deterministic
  summary, so an unsourced number can never reach the screen.
- UI-only: this is called from `ui.render_answer`, never on the frozen eval path,
  so the evaluation harness and v1 are completely unaffected.
- Gated to the v2 engine and a kill switch (`IPEDS_NARRATIVE=0`).
"""
import os
import re

from .engine_select import active_engine

# Sonnet 5.5 (= agent.DEFAULT_MODEL): prose fluency matters more than cost here,
# and the call is short and bounded.
NARRATIVE_MODEL = 'claude-sonnet-5-5'

SYSTEM = """You write a short, plain-language answer about U.S. college data from IPEDS.

You are given a VERIFIED factual summary and the underlying result rows. Rephrase them into a
direct, readable answer. Follow every rule:
- 2–5 sentences. Answer the question first, then at most one note (a trend, a gap, or missing data).
- Use ONLY numbers that appear in the provided facts. Never compute a new figure — no difference,
  average, percentage, ratio, or rank of your own. Describe any change in words ("higher", "rose",
  "about the same"), not as a number you calculated.
- A value shown as "not reported" or "not collected" means IPEDS did not report it. Say "not
  reported"; never treat it as zero.
- Reporting periods are IPEDS collection years. A national or aggregate figure is a pooled count,
  not an average of institutions — never call it an average.
- Write small counts in words (e.g. "all three schools"). No markdown headings, no variable codes,
  no table names.

Be factual and concise. Do not invent context or add caveats beyond what the data shows."""


def _enabled():
    return active_engine() == 'v2' and os.environ.get('IPEDS_NARRATIVE', '1') != '0'


def want_narrative(answer):
    """True when a fluent narrative is worth generating for this answer."""
    if not _enabled():
        return False
    # Only narrate answers that came through finalize_answer with a real question
    # (this also excludes the extract-builder preview, which carries no question).
    if not answer.get('narrative_question'):
        return False
    if answer.get('mode') in {'presentation adjustment', 'extract builder'}:
        return False
    result = answer.get('result') or {}
    # Schema-v2 categorical/list lookups are not numeric answers; the structured
    # panel already reads clearly and there is nothing to narrate.
    if result.get('result_schema_version') == 2:
        return False
    good = [r for r in result.get('rows', []) if r.get('status') == 'ok']
    return len(good) >= 1


def _numbers(text):
    """The set of numeric values in a string, comma-insensitive and as floats so
    "87", "87.0" and "87.00" compare equal and "2,995" matches "2995"."""
    text = re.sub(r'(?<=\d),(?=\d)', '', text or '')
    out = set()
    for token in re.findall(r'\d+(?:\.\d+)?', text):
        try:
            out.add(round(float(token), 4))
        except ValueError:
            pass
    return out


def _support(result, facts):
    """Every number the narrative is allowed to use: the verified summary plus the
    raw row values, periods, and counts."""
    from .responses import value_text
    parts = [facts]
    for row in result.get('rows', []):
        parts.append(value_text(row))
        parts.append(str(row.get('reporting_period', '')))
        for key in ('value', 'numerator', 'denominator', 'observation_year', 'entry_cohort_year'):
            if row.get(key) is not None:
                parts.append(str(row[key]))
    return _numbers(' '.join(parts))


def _grounded(text, support):
    return _numbers(text) <= support


def _rows_table(result):
    from .responses import value_text
    lines = []
    for row in result.get('rows', [])[:60]:
        lines.append('- ' + ' | '.join(str(x) for x in (
            row.get('institution'), row.get('measure'),
            value_text(row), row.get('reporting_period'))))
    return '\n'.join(lines)


def narrative_text(question, answer):
    """Return a validated fluent answer, or '' to fall back to the deterministic
    summary. Blocking; the caller runs it under a spinner and caches the result."""
    from .api_client import get_client
    from .responses import summarize, evidence_summary
    result = answer.get('result') or {}
    if not result.get('rows'):
        return ''
    facts = answer.get('message') or summarize(result)
    ev = evidence_summary(result)
    user = (
        'Question: ' + (question or '(not provided)') + '\n\n'
        'Verified summary: ' + facts + '\n\n'
        'Scope: ' + (', '.join(ev.get('institutions', [])) or 'n/a') + '\n'
        'Population / selection: ' + ('; '.join(ev.get('population', [])) or 'n/a') + '\n'
        'Reporting period(s): ' + (', '.join(ev.get('periods', [])) or 'n/a') + '\n\n'
        'Result rows:\n' + _rows_table(result))
    try:
        response = get_client().messages.create(
            model=NARRATIVE_MODEL, max_tokens=400,
            system=SYSTEM, messages=[{'role': 'user', 'content': user}])
        text = ''.join(
            block.text for block in response.content
            if getattr(block, 'type', '') == 'text').strip()
    except Exception:
        return ''
    if not text or not _grounded(text, _support(result, facts)):
        return ''
    return text
