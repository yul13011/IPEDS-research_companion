"""Request-scoped stage notifications; no UI dependency or simulated progress."""
from contextlib import contextmanager
from contextvars import ContextVar

_REPORTER=ContextVar('ipeds_progress_reporter',default=None)


def report(message):
    callback=_REPORTER.get()
    if callback is not None:callback(message)


@contextmanager
def reporting(callback):
    token=_REPORTER.set(callback)
    try:yield
    finally:_REPORTER.reset(token)
