# accounts/utils.py
from accounts.models import StoreMembership

def choose_current_store_id(request, user):
	"""
	優先順位：
	  1) ヘッダ X-Store-Id（superuserは無条件 / それ以外は membership 内）
	  2) primary_store
	  3) legacy: user.store_id
	  4) memberships 先頭
	  5) None
	"""
	mems = list(
		StoreMembership.objects.filter(user=user)
		.values('store_id', 'role', 'is_primary')   # ★ ここに 'role' を追加
	)
	store_ids = [m['store_id'] for m in mems]
	primary_store_id = next((m['store_id'] for m in mems if m['is_primary']), None)

	# 1) ヘッダ
	raw_sid = request.headers.get('X-Store-Id') if request else None
	header_sid = None
	if raw_sid:
		try:
			header_sid = int(raw_sid)
		except Exception:
			header_sid = None
	if header_sid and (getattr(user, 'is_superuser', False) or header_sid in store_ids):
		return header_sid, store_ids, primary_store_id, mems

	# 2) ～ 4)
	if primary_store_id:
		return primary_store_id, store_ids, primary_store_id, mems
	legacy_sid = getattr(user, 'store_id', None)
	if legacy_sid:
		return legacy_sid, store_ids, primary_store_id, mems
	if store_ids:
		return store_ids[0], store_ids, primary_store_id, mems

	# 5)
	return None, store_ids, primary_store_id, mems
