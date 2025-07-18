from django.conf      import settings
from django.apps      import apps
from rest_framework   import viewsets

StoreModel = apps.get_model(settings.STORE_MODEL)	# billing.Store を取得

class StoreScopedModelViewSet(viewsets.ModelViewSet):
	"""
	ログインユーザーの store_id だけに絞る。
	Store 自体を取得する場合は pk で絞り込み。
	"""
	def _store_id(self):
		return getattr(self.request.user, 'store_id', None) \
			or settings.DEFAULT_STORE_ID

	def get_queryset(self):
		qs  = super().get_queryset()
		sid = self._store_id()

		# 対象が Store 自体
		if qs.model is StoreModel:
			return qs.filter(pk=sid)

		# 他モデルなら store_id を持つ場合だけフィルタ
		if 'store_id' in (f.name for f in qs.model._meta.fields):
			return qs.filter(store_id=sid)
		return qs