# billing/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS
from accounts.caps import get_caps_for
from .models import BillCastStay, Cast


class RequireCap(BasePermission):
    """
    Viewに `required_cap = '...'` を付与して使う。
    """
    def has_permission(self, request, view):
        cap = getattr(view, 'required_cap', None)
        if not cap:
            return True
        store_id = getattr(request, 'store', None) and request.store.id or request.query_params.get('store_id')
        caps = get_caps_for(request.user, int(store_id) if store_id else None)
        return cap in caps

class OwnerReadOnly(BasePermission):
    """
    オーナーはReadのみ許可（複数店舗含む）。
    PL閲覧系ビューに併用すると安全。
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        # それ以外のメソッドは RequireCap に任せる（ここではブロック）
        return False


def _req_store_id(request):
    sid = getattr(getattr(request, "store", None), "id", None) \
          or request.query_params.get("store_id") \
          or request.headers.get("X-Store-ID")
    try:
        return int(sid) if sid is not None else None
    except Exception:
        return None

class CastHonshimeiForBill(BasePermission):
    message = '本指名の在席中のみ、自分の卓に注文できます。'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):  # obj = Bill
        sid = _req_store_id(request)
        if sid is None or obj.table.store_id != sid:
            return False
        cast_id = Cast.objects.filter(user=request.user).values_list('id', flat=True).first()
        if not cast_id:
            return False
        return BillCastStay.objects.filter(
            bill=obj, cast_id=cast_id,
            left_at__isnull=True, is_honshimei=True
        ).exists()



def _req_store_id(request):
	sid = getattr(getattr(request, "store", None), "id", None) \
	      or request.query_params.get("store_id") \
	      or request.headers.get("X-Store-Id") \
	      or request.headers.get("X-Store-ID")    # ★ 両方見る
	try:
		return int(sid) if sid is not None else None
	except Exception:
		return None

class CanOrderBillItem(BasePermission):
	message = '本指名の在席中のみ、自分の卓に注文できます。'

	def has_permission(self, request, view):
		return bool(request.user and request.user.is_authenticated)

	def has_object_permission(self, request, view, obj):
		sid = _req_store_id(request)
		if sid is None:
			return False

		# ★ obj を必ず Bill に正規化
		if hasattr(obj, 'table'):        # Bill
			bill = obj
		elif hasattr(obj, 'bill'):       # BillItem
			bill = obj.bill
		elif hasattr(obj, 'bill_id'):    # BillItem（遅延）
			bill = Bill.objects.select_related('table') \
			       .only('id','table_id','table__store_id').get(id=obj.bill_id)
		else:
			return False

		# tableが未ロードなら補完
		if getattr(bill, 'table', None) is None:
			bill = Bill.objects.select_related('table') \
			       .only('id','table_id','table__store_id').get(id=bill.id)

		if int(bill.table.store_id) != int(sid):
			return False

		# スタッフ権限ならOK
		caps = get_caps_for(request.user, sid)
		if 'operate_orders' in caps:
			return True

		# キャスト：本指名で在席中ならOK
		cast_id = Cast.objects.filter(user=request.user).values_list('id', flat=True).first()
		if not cast_id:
			return False

		return BillCastStay.objects.filter(
			bill=bill, cast_id=cast_id,
			left_at__isnull=True, is_honshimei=True
		).exists()