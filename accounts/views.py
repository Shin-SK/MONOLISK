# accounts/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .caps import get_caps_for

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    u = request.user
    memberships = u.memberships.select_related('store').all()
    store_ids = [m.store_id for m in memberships]
    primary_store_id = next((m.store_id for m in memberships if m.is_primary), None)
    current_store_id = getattr(request, 'store', None).id if getattr(request, 'store', None) else primary_store_id

    # cast_id を現在店舗優先で解決
    cast_id = None
    try:
        from billing.models import Cast
        qs = Cast.objects.filter(user=u)
        if current_store_id:
            cast_id = qs.filter(store_id=current_store_id).values_list('id', flat=True).first() or \
                      qs.values_list('id', flat=True).first()
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
    })
