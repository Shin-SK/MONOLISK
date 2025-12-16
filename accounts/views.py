# accounts/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from billing.models import Store
from accounts.utils import choose_current_store_id
from .caps import get_caps_for
from .models import StoreRole, StoreMembership
from .serializers import UserDetailsWithStoreSerializer

ROLE_MAP = {
    StoreRole.OWNER: 'owner', StoreRole.MANAGER: 'manager',
    StoreRole.STAFF: 'staff', StoreRole.CAST: 'cast',
}

def _role_for(user, store_id):
    if not user.is_authenticated:
        return None
    # 1) 現在店舗の membership を最優先
    if store_id:
        r = (
            user.memberships
                .filter(store_id=store_id)
                .values_list('role', flat=True)
                .first()
        )
        if r:
            return ROLE_MAP.get(r)
    # 2) membership が無い superuser は owner 相当
    if getattr(user, 'is_superuser', False):
        return 'owner'
    # 3) 何も無ければ最初の membership で推定
    r0 = user.memberships.values_list('role', flat=True).first()
    return ROLE_MAP.get(r0)

# ★ /api/me のペイロードを共通化
def _me_payload(request):
    u = request.user
    current_store_id, store_ids, primary_store_id, mems = choose_current_store_id(request, u)

    # cast_id
    cast_id = None
    try:
        from billing.models import Cast
        qs = Cast.objects.filter(user=u)
        cast_id = (qs.filter(store_id=current_store_id).values_list('id', flat=True).first()
                   or qs.values_list('id', flat=True).first())
    except Exception:
        pass

    avatar_url = UserDetailsWithStoreSerializer(
        u, context={'request': request, 'store_id': current_store_id}
    ).data.get('avatar_url')

    # store_name を付与（N+1回避：まとめて取得）
    try:
        name_map = dict(Store.objects.filter(id__in=store_ids).values_list('id', 'name'))
    except Exception:
        name_map = {}
    memberships = [
        {
            'store_id': m['store_id'],
            'store_name': name_map.get(m['store_id']),
            'role': ROLE_MAP.get(m.get('role')),
            'is_primary': m['is_primary'],
        }
        for m in mems
    ]

    return {
        'id': u.id,
        'username': u.get_username(),
        'name': getattr(u, 'display_name', None) or u.get_full_name() or u.get_username(),
        'is_superuser': u.is_superuser,
        'stores': store_ids,
        'memberships': memberships,
        'primary_store_id': primary_store_id,
        'current_store_id': current_store_id,
        'store_id': current_store_id,  # 互換
        'cast_id': cast_id,
        'current_role': _role_for(u, current_store_id),
        'claims': sorted(list(get_caps_for(u, current_store_id))),
        'avatar_url': avatar_url,
    }

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(_me_payload(request))

@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
def debug_set_role(request):
    u = request.user
    if not u.is_superuser:
        return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    role = (request.data.get('role') or request.query_params.get('role') or '').lower()
    if role not in (StoreRole.OWNER, StoreRole.MANAGER, StoreRole.STAFF, StoreRole.CAST):
        return Response({"detail": "invalid role"}, status=400)

    memberships = u.memberships.select_related('store').all()
    primary_store_id = next((m.store_id for m in memberships if m.is_primary), None)
    qp_sid = request.query_params.get('store_id')
    sid = (getattr(getattr(request, 'store', None), 'id', None)
           or (int(qp_sid) if (qp_sid or '').isdigit() else None)
           or primary_store_id)
    if not sid:
        return Response({"detail": "store_id required"}, status=400)

    store = get_object_or_404(Store, pk=sid)
    mem, _ = StoreMembership.objects.get_or_create(user=u, store=store, defaults={'role': role})
    if mem.role != role:
        mem.role = role
        mem.save(update_fields=['role'])

    # ★ 直接ペイロードを返す（me()は呼ばない）
    return Response(_me_payload(request))
