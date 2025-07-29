# billing/middleware.py
from django.utils.deprecation import MiddlewareMixin

class AttachStoreMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = getattr(request, 'user', None)
        request.store = getattr(user, 'store_profile', None) and user.store_profile.store
