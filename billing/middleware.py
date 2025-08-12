# billing/middleware.py
class AttachStoreMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        store = getattr(user, "store", None) if (user and getattr(user, "is_authenticated", False)) else None
        request.store = store
        return self.get_response(request)
