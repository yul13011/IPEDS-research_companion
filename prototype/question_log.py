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

Share the sheet with the service account's client_email (Editor) and give it a tab whose
header row is: timestamp, session_id, question, outcome.
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
COLUMNS=('timestamp','session_id','question','outcome')

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
    except Exception:
        _log.exception('question log: could not open the sheet')
        _worksheet=None
    return _worksheet


def log_question(question,outcome,session_id=''):
    """Append one row (timestamp, session_id, question, outcome). Fire-and-forget and
    quiet-fail: never raises, never blocks the answer. A silent no-op when unconfigured."""
    if not question or not configured():return
    row=[datetime.now(timezone.utc).isoformat(),session_id or '',str(question),str(outcome)]

    def _append():
        with _lock:
            ws=_open()
        if ws is None:return
        try:ws.append_row(row,value_input_option='RAW')
        except Exception:_log.exception('question log: append failed (outcome=%s)',outcome)

    threading.Thread(target=_append,daemon=True).start()
