# billing/middleware.py
from django.core.exceptions import PermissionDenied
from .models import Store

class AttachStoreMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ① 明示（Postman 等）
        sid = request.headers.get("X-Store-Id") or request.GET.get("store_id")
        store = None
        if sid:
            try:
                store = Store.objects.only("id").get(pk=int(sid))
            except Exception:
                raise PermissionDenied("不正な store_id です。")

        # ② ログインユーザーの店舗（1:1 前提）
        if not store and getattr(request, "user", None) and request.user.is_authenticated:
            store = getattr(request.user, "store", None)

        request.store = store
        return self.get_response(request)
