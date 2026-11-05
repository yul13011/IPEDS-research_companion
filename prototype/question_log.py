"""Record each question and its outcome to a Google Sheet, for prototype analytics.

Ports the gradrate prototype's question log to this app. Writing is fire-and-forget on a
daemon thread and quiet-fails: a logging failure must never slow an answer or surface an
error to a visitor. When gspread is not installed or no sheet is configured, logging is a
silent no-op, so the app runs unchanged without it.

Unlike gradrate (which used Streamlit's st.secrets + st-gsheets-connection), this app reads
config from environment variables or .streamlit/secrets.toml directly, matching how it reads
the Anthropic key (see agent.api_key). Configure either way:

  .streamlit/secrets.toml  (simplest: point at the downloaded JSON file; no key pasting)
      [question_log]
      spreadsheet      = "https://docs.google.com/spreadsheets/d/<id>/edit"
      credentials_file = "C:/path/to/service-account.json"
      worksheet        = "questions"       # optional; defaults to "questions"

  .streamlit/secrets.toml  (alternative: inline the service-account fields)
      [question_log]
      spreadsheet = "https://docs.google.com/spreadsheets/d/<id>/edit"
      [question_log.service_account]
      type = "service_account"
      client_email = "...@....iam.gserviceaccount.com"
      private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"
      # ...the rest of the service-account JSON...

  environment (preferred on Render)
      IPEDS_QUESTIONS_SHEET          spreadsheet id or URL
      IPEDS_QUESTIONS_WORKSHEET      optional tab name (default "questions")
      IPEDS_GSHEETS_CREDENTIALS      the service-account JSON, as a single string
      GOOGLE_APPLICATION_CREDENTIALS path to the service-account JSON file (fallback)

Share the sheet with the service account's client_email (Editor). The tab's header row is
written automatically on first use (see `_ensure_header`): timestamp, session_id, question,
outcome, then the derived analytics columns (interpreted_as, route, relationship, served_by,
topic, scope, n_rows, had_value, latency_s, model, est_usd, n_calls, engine, narrative) and
app_version. An existing four-column sheet keeps its rows and is extended in place.
"""
import json
import logging
import os
import threading
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from .catalog import BASE

WORKSHEET_DEFAULT='questions'
# Structured analytics columns derived from the finished answer (all already computed
# by the pipeline — see `fields`). Appended after the original four so an existing
# sheet keeps its first columns and only gains new ones on the right.
EXTRA_COLUMNS=('interpreted_as','route','relationship','served_by','topic','scope',
               'n_rows','had_value','latency_s','model','est_usd','n_calls','engine','narrative')
COLUMNS=('timestamp','session_id','question','outcome')+EXTRA_COLUMNS+('app_version',)

_log=logging.getLogger('question_log')
_lock=threading.Lock()
_worksheet=None   # cached gspread Worksheet handle; opened once, only on success


def _secrets():
    for p in [BASE/'.streamlit'/'secrets.toml', BASE.parent/'.streamlit'/'secrets.toml']:
        if p.exists():
            try:return tomllib.loads(p.read_text(encoding='utf-8-sig'))
            except (OSError,tomllib.TOMLDecodeError):pass
    return {}


def _credentials():
    """Service-account dict, resolved in order: env raw JSON, a JSON file path (env or the
    `credentials_file` secret), or an inline [question_log.service_account] table. None if unset."""
    raw=os.environ.get('IPEDS_GSHEETS_CREDENTIALS')
    if raw:
        try:return json.loads(raw)
        except json.JSONDecodeError:_log.warning('IPEDS_GSHEETS_CREDENTIALS is not valid JSON');return None
    cfg=_secrets().get('question_log',{})
    path=os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') or cfg.get('credentials_file')
    if path and Path(path).exists():
        try:return json.loads(Path(path).read_text(encoding='utf-8'))
        except (OSError,json.JSONDecodeError):_log.warning('question log: credentials file is missing or not valid JSON');return None
    sa=cfg.get('service_account')
    return dict(sa) if sa else None


def _target():
    """(spreadsheet ref, worksheet name) from env or secrets.toml; ref is None when unset."""
    cfg=_secrets().get('question_log',{})
    ref=os.environ.get('IPEDS_QUESTIONS_SHEET') or cfg.get('spreadsheet')
    ws=os.environ.get('IPEDS_QUESTIONS_WORKSHEET') or cfg.get('worksheet') or WORKSHEET_DEFAULT
    return ref,ws


def configured():
    """True when both a sheet and credentials are present. No network; cheap to call."""
    ref,_=_target()
    return bool(ref) and _credentials() is not None


def _open():
    """Open and cache the worksheet handle (network). Retries on each call until it succeeds."""
    global _worksheet
    if _worksheet is not None:return _worksheet
    try:
        import gspread
        ref,ws=_target()
        client=gspread.service_account_from_dict(_credentials())
        book=client.open_by_url(ref) if '://' in ref else client.open_by_key(ref)
        _worksheet=book.worksheet(ws)
        _ensure_header(_worksheet)
    except Exception:
        _log.exception('question log: could not open the sheet')
        _worksheet=None
    return _worksheet


from functools import lru_cache


@lru_cache(maxsize=1)
def _app_version():
    """A short identifier for the running build, so outcomes can be segmented by deploy.
    Prefers an explicit env var, then Render's commit, then the local git SHA; '' if none."""
    v=os.environ.get('IPEDS_APP_VERSION') or os.environ.get('RENDER_GIT_COMMIT')
    if v:return v[:12]
    try:
        import subprocess
        out=subprocess.run(['git','rev-parse','--short','HEAD'],cwd=str(BASE),
                           capture_output=True,text=True,timeout=2)
        return out.stdout.strip()
    except Exception:
        return ''


# Source-table prefix -> coarse topic, for catalog/observation plans whose metrics are
# table-qualified (e.g. "DRVC{YEAR}::MASDEG"). Reviewed-measure plans use the measure
# family directly; this only fills the gap. Order matters: check longer keys first.
_TABLE_TOPIC=[('DRVIC','cost'),('DRVC','completions'),('DRVGR','graduation'),('DRVHR','faculty/staff'),
              ('DRVF','finance'),('DRVAL','library'),('DRVADM','admissions'),('DRVEF','enrollment'),
              ('ADM','admissions'),('SFA','aid'),('SAL','faculty/staff'),('EAP','faculty/staff'),
              ('GR','graduation'),('EF','enrollment'),('AL','library'),('IC','institutional characteristics'),
              ('C','completions'),('F','finance'),('S','faculty/staff')]


def _topic(answer):
    """Best-effort subject family, for a demand view of what users ask about. '' when unclear."""
    result=answer.get('result') or {}
    plan=answer.get('plan') or result.get('plan') or {}
    metrics=plan.get('metrics') or []
    if metrics:
        try:
            from .analytics import measures
            specs=measures();fams={specs[m]['family'] for m in metrics if m in specs}
            if fams:return '/'.join(sorted(fams))
        except Exception:pass
    tokens=set()
    for r in (result.get('rows') or []):
        m=str(r.get('metric') or '')
        head=m.split('::')[0].split('{')[0]
        head=''.join(ch for ch in head if not ch.isdigit()).rstrip('_') or head
        if head:tokens.add(head.upper())
    found=[]
    for tok in tokens:
        for prefix,topic in _TABLE_TOPIC:
            if tok.startswith(prefix):
                if topic not in found:found.append(topic)
                break
    return '/'.join(sorted(found))


def _scope(answer):
    """The shape of the request: one school, a comparison, a matching list, or an aggregate."""
    result=answer.get('result') or {}
    if result.get('result_kind')=='institution_list':return 'institution_list'
    plan=(answer.get('plan') or answer.get('catalog_plan') or answer.get('observation_plan')
          or result.get('plan') or {})
    if plan.get('population') or (answer.get('observation_plan') or {}).get('population'):
        return 'aggregate'
    rows=result.get('rows') or []
    names={r.get('institution') or r.get('unitid') for r in rows}
    n=len(names) or len(plan.get('institutions') or [])
    return 'comparison' if n>1 else 'single' if n==1 else ''


def fields(answer):
    """Derive the structured analytics columns from a finished answer. Best-effort and
    exception-proof: any field that cannot be determined is left ''. Returns a dict keyed
    by EXTRA_COLUMNS."""
    f={k:'' for k in EXTRA_COLUMNS}
    if not isinstance(answer,dict):return f
    try:
        ii=answer.get('intent_interpretation') or {}
        mu=answer.get('model_usage') or {}
        lat=answer.get('latency') or {}
        f['interpreted_as']=answer.get('resolved_question') or answer.get('interpreted_as') or ''
        f['route']=ii.get('operation') or ii.get('route') or ''
        f['relationship']=ii.get('relationship') or ''
        f['served_by']=answer.get('mode') or ''
        f['engine']=mu.get('engine') or ii.get('engine') or ''
        f['model']=mu.get('model') or ''
        f['est_usd']=mu.get('estimated_api_usd')
        f['n_calls']=mu.get('calls')
        secs=lat.get('answer_ready_seconds')
        f['latency_s']=round(secs,2) if isinstance(secs,(int,float)) else ''
        if answer.get('result') is not None:
            from .request_tasks import usable
            rows=answer['result'].get('rows') or []
            f['n_rows']=len(rows)
            f['had_value']=usable(answer['result'])
        f['topic']=_topic(answer)
        f['scope']=_scope(answer)
        try:
            from .result_narrative import want_narrative
            f['narrative']=bool(want_narrative(answer))
        except Exception:pass
    except Exception:
        _log.debug('question log: field derivation failed',exc_info=True)
    return f


def _cell(value):
    """Spreadsheet-friendly primitive: blanks for None, TRUE/FALSE for booleans."""
    if value is None:return ''
    if isinstance(value,bool):return 'TRUE' if value else 'FALSE'
    return value


def _ensure_header(ws):
    """Write the header row once so the derived columns are labelled. Conservative: only
    when row 1 is empty or still the original four-column header, never over other content."""
    try:first=ws.row_values(1)
    except Exception:return
    if first==list(COLUMNS):return
    if not first or first==['timestamp','session_id','question','outcome']:
        try:ws.update(range_name='A1',values=[list(COLUMNS)])
        except Exception:_log.exception('question log: could not write header row')


def log_question(question,outcome,session_id='',answer=None):
    """Append one analytics row: the original timestamp/session_id/question/outcome plus the
    structured columns derived from `answer` (blank when no answer is supplied, e.g. on error).
    Fire-and-forget and quiet-fail: never raises, never blocks the answer; a no-op when
    unconfigured."""
    if not question or not configured():return
    record={'timestamp':datetime.now(timezone.utc).isoformat(),'session_id':session_id or '',
            'question':str(question),'outcome':str(outcome),
            **(fields(answer) if answer is not None else {k:'' for k in EXTRA_COLUMNS}),
            'app_version':_app_version()}
    row=[_cell(record.get(c,'')) for c in COLUMNS]

    def _append():
        with _lock:
            ws=_open()
        if ws is None:return
        try:ws.append_row(row,value_input_option='RAW')
        except Exception:_log.exception('question log: append failed (outcome=%s)',outcome)

    threading.Thread(target=_append,daemon=True).start()
