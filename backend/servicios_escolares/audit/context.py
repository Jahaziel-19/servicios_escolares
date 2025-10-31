import threading

_local = threading.local()


def set_request_context(user=None, ip=None, request_id=None, source=None):
    _local.user = user
    _local.ip = ip
    _local.request_id = request_id
    _local.source = source


def get_request_context():
    return (
        getattr(_local, 'user', None),
        getattr(_local, 'ip', None),
        getattr(_local, 'request_id', None),
        getattr(_local, 'source', None),
    )