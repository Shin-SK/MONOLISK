from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.utils.deprecation import MiddlewareMixin
from .models import Store

# Store-Locked: ヘッダ一本化
# ・Store依存APIは常に X-Store-Id を必須
# ・/api/me, 認証/登録 等は例外
# ・クエリ ?store_id は互換として検出のみ（ヘッダと不一致なら 409）


SKIP_PATHS = (
	"/api/me",
	"/api/dj-rest-auth/login",
	"/api/dj-rest-auth/logout",
	"/api/dj-rest-auth/password",
	"/api/dj-rest-auth/user",
	"/api/auth/registration",
	"/api/dj-rest-auth/registration",
)

class AttachStoreMiddleware(MiddlewareMixin):
	def process_request(self, request):
		path = (request.path or "").rstrip("/")

		# 非APIは対象外
		if not path.startswith("/api/"):
			request.store = None
			return None

		# 例外
		if any(path.startswith(p) for p in SKIP_PATHS):
			request.store = None
			return None

		# ヘッダ必須
		raw_sid = request.headers.get("X-Store-Id")
		if not raw_sid:
			return JsonResponse({"detail": "X-Store-Id header is required."}, status=400)

		# クエリ不一致 → 409
		q_sid = request.GET.get("store_id")
		if q_sid and q_sid != raw_sid:
			return JsonResponse({"detail": "store_id mismatch between header and query."}, status=409)

		# Store 存在チェック
		try:
			sid = int(raw_sid)
			store = Store.objects.only("id").get(pk=sid)
		except Exception:
			return JsonResponse({"detail": "Invalid X-Store-Id."}, status=400)

		# ★ ここでは所属を確認しない（DRFのビューで判定）
		request.store = store
		return None

	def _belongs(self, user, sid: int) -> bool:
		# あなたの実装に合わせて最適化してください
		# 1) 多店舗 Membership がある場合
		ms = getattr(user, "memberships", None) or getattr(user, "store_memberships", None)
		if hasattr(ms, "filter"):
			return ms.filter(store_id=sid).exists()
		# 2) 単一 store の場合（暫定互換）
		u_store = getattr(user, "store", None)
		return (getattr(u_store, "id", None) == sid)
