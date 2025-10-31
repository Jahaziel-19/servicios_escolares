import uuid
from .context import set_request_context


class AuditRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        rid = str(uuid.uuid4())[:8]
        user = getattr(request, 'user', None)
        ip = request.META.get('REMOTE_ADDR')
        source = 'admin' if request.path.startswith('/admin') else 'publico'
        set_request_context(user=user, ip=ip, request_id=rid, source=source)
        return self.get_response(request)