# billing/api_kds.py
import time
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_events(request):
    """
    KDS用のロングポーリング・スタブ
    ?station=drinker|kitchen|hall
    ?since=<cursor文字列>
    ?wait=<秒(最大25)>
    """
    wait = int(request.query_params.get('wait', '1'))
    wait = max(0, min(wait, 25))
    since = request.query_params.get('since') or ''
    time.sleep(wait)  # 疑似で待つ
    return Response({'events': [], 'cursor': since, 'retryAfter': 800})
