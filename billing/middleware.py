# billing/middleware.py
from django.utils.deprecation import MiddlewareMixin

class AttachStoreMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        request.store = getattr(request.user, 'store', None)
        return self.get_response(request)