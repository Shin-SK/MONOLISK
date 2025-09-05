# accounts/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .caps import get_caps_for
from .models import StoreRole  # ★ 追加

def _role_to_str(role):
    if role == StoreRole.OWNER:   return 'owner'
    if role == StoreRole.MANAGER: return 'manager'
    if role == StoreRole.STAFF:   return 'staff'
    if role == StoreRole.CAST:    return 'cast'
    return None


def _resolve_current_role(user, store_id):
    if not user.is_authenticated:
        return None
    # 1) 現在店舗の membership を最優先
    if store_id:
        role = (user.memberships
                    .filter(store_id=store_id)
                    .values_list('role', flat=True)
                    .first())
        if role is not None:
            mapping = {
                StoreRole.OWNER:   'owner',
                StoreRole.MANAGER: 'manager',
                StoreRole.STAFF:   'staff',
                StoreRole.CAST:    'cast',
            }
            return mapping.get(role)
    # 2) 店舗が取れないなどのフォールバック
    #    membershipが無い superuser は owner として扱う
    if getattr(user, 'is_superuser', False):
        return 'owner'
    # 3) 何も無ければ最初のmembershipで推定 or None
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

    # ★ current_store_id: middlewareの request.store → ?store_id → primary の順で解決
    try:
        qp_sid = int(request.query_params.get('store_id')) if request.query_params.get('store_id') else None
    except Exception:
        qp_sid = None
    current_store_id = (
        getattr(getattr(request, 'store', None), 'id', None)
        or qp_sid
        or primary_store_id
    )

    # cast_id を現在店舗優先で解決
    cast_id = None
    try:
        from billing.models import Cast
        qs = Cast.objects.filter(user=u)
        if current_store_id:
            cast_id = (qs.filter(store_id=current_store_id).values_list('id', flat=True).first()
                       or qs.values_list('id', flat=True).first())
        else:
            cast_id = qs.values_list('id', flat=True).first()
    except Exception:
        pass

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
        'current_role': _resolve_current_role(u, current_store_id),  # ★ 追加
    })
