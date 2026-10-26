"""Bounded connection reuse; no responses, questions, or session state are cached."""
from collections import OrderedDict
from threading import RLock
import atexit

_clients=OrderedDict()
_lock=RLock()

def get_client():
    import anthropic
    from .agent import api_key
    # Factory identity keeps transport mocks isolated; credentials isolate rotation.
    factory=anthropic.Anthropic;key=api_key();identity=(factory,key)
    with _lock:
        if identity in _clients:
            _clients.move_to_end(identity)
            return _clients[identity]
        client=factory(api_key=key,timeout=45,max_retries=0)
        _clients[identity]=client
        # Do not close an evicted client: another request could still be using it.
        # The SDK closes unreferenced clients; shutdown closes retained instances.
        if len(_clients)>4:_clients.popitem(last=False)
        return client

def close_clients():
    with _lock:
        clients=list(_clients.values());_clients.clear()
    for client in clients:
        try:client.close()
        except Exception:pass

atexit.register(close_clients)
