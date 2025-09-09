# accounts/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .caps import get_caps_for
from .models import StoreRole
from .serializers import UserDetailsWithStoreSerializer  # ★ avatar_url をもらう

def _role_to_str(role):
    if role == StoreRole.OWNER:   return 'owner'
    if role == StoreRole.MANAGER: return 'manager'
    if role == StoreRole.STAFF:   return 'staff'
    if role == StoreRole.CAST:    return 'cast'
    return None

def _resolve_current_role(user, store_id):
	if not user.is_authenticated:
		return None
	if store_id:
		role = (
			user.memberships
				.filter(store_id=store_id)
				.values_list('role', flat=True)
				.first()
		)
		if role is not None:
			mapping = {
				StoreRole.OWNER:   'owner',
				StoreRole.MANAGER: 'manager',
				StoreRole.STAFF:   'staff',
				StoreRole.CAST:    'cast',
			}
			return mapping.get(role)
	if getattr(user, 'is_superuser', False):
		return 'owner'
	role = user.memberships.values_list('role', flat=True).first()
	if role is not None:
		mapping = {
			StoreRole.OWNER:   'owner',
			StoreRole.MANAGER: 'manager',
			StoreRole.STAFF:   'staff',
			StoreRole.CAST:    'cast',
		}
		return mapping.get(role)
	return None

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
	u = request.user
	memberships = u.memberships.select_related('store').all()
	store_ids = [m.store_id for m in memberships]
	primary_store_id = next((m.store_id for m in memberships if m.is_primary), None)

	# ★ current_store_id は「ヘッダ優先」。/api/me ではクエリは見ない
	raw_sid = request.headers.get('X-Store-Id')
	try:
		header_sid = int(raw_sid) if raw_sid is not None else None
	except Exception:
		header_sid = None

	current_store_id = header_sid or primary_store_id

	# cast_id は現在店舗優先で解決
	cast_id = None
	try:
		from billing.models import Cast
		qs = Cast.objects.filter(user=u)
		if current_store_id:
			cast_id = (
				qs.filter(store_id=current_store_id).values_list('id', flat=True).first()
				or qs.values_list('id', flat=True).first()
			)
		else:
			cast_id = qs.values_list('id', flat=True).first()
	except Exception:
		pass

	avatar_url = UserDetailsWithStoreSerializer(
		u, context={'request': request, 'store_id': current_store_id}
	).data.get('avatar_url')

	return Response({
		'id': u.id,
		'username': u.get_username(),
		'name': getattr(u, 'display_name', None) or u.get_full_name() or u.get_username(),
		'is_superuser': u.is_superuser,
		'stores': store_ids,
		'primary_store_id': primary_store_id,
		'current_store_id': current_store_id,
		'cast_id': cast_id,
		'claims': sorted(list(get_caps_for(u, current_store_id))),
		'current_role': _resolve_current_role(u, current_store_id),
		'avatar_url': avatar_url,
	})



# accounts/views.py（debug_set_role を置換）
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from accounts.models import StoreMembership, StoreRole
from billing.models import Store
from .views import me as me_view

@api_view(['POST', 'GET'])   # ★ GETも許可（検証用）
@permission_classes([IsAuthenticated])
def debug_set_role(request):
    u = request.user
    if not u.is_superuser:
        return Response({"detail":"forbidden"}, status=status.HTTP_403_FORBIDDEN)

    role = (request.data.get('role') or request.query_params.get('role') or '').lower()
    if role not in (StoreRole.OWNER, StoreRole.MANAGER, StoreRole.STAFF, StoreRole.CAST):
        return Response({"detail":"invalid role"}, status=400)

    memberships = u.memberships.select_related('store').all()
    primary_store_id = next((m.store_id for m in memberships if m.is_primary), None)
    qp_sid = request.query_params.get('store_id')
    sid = getattr(getattr(request, 'store', None), 'id', None) or (int(qp_sid) if (qp_sid or '').isdigit() else None) or primary_store_id
    if not sid:
        return Response({"detail":"store_id required"}, status=400)

    store = get_object_or_404(Store, pk=sid)
    mem, _ = StoreMembership.objects.get_or_create(user=u, store=store, defaults={'role': role})
    if mem.role != role:
        mem.role = role
        mem.save(update_fields=['role'])

    # DRF Request→HttpRequestに戻して /api/me を返す
    return me_view(request._request)
