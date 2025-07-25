# accounts/middleware.py
from django.shortcuts import redirect, get_object_or_404
from billing.models import Store


class StoreFromPathMiddleware:
	"""
	URL 先頭の /<store_slug>/ を取り出し request.store にセット
	"""
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		parts = request.path.lstrip('/').split('/', 1)
		if parts and parts[0]:
			try:
				request.store = Store.objects.get(slug=parts[0])
				request.path_info = '/' + parts[1] if len(parts) > 1 else '/'
			except Store.DoesNotExist:
				request.store = None
		return self.get_response(request)
