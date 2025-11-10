# billing/api_debug.py（新規）
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([AllowAny])  # 認証不要で可視化したいなら一時的に
def whoami_store(request):
    s = getattr(request, 'store', None)
    return Response({
        "got_header_id": request.META.get('HTTP_X_STORE_ID'),
        "got_header_slug": request.META.get('HTTP_X_STORE_SLUG'),
        "store_id": getattr(s, 'id', None),
        "store_slug": getattr(s, 'slug', None),
    })
