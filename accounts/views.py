# accounts/views.py
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from django.conf import settings
from django.utils import timezone
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
        'first_name': u.first_name,
        'last_name': u.last_name,
        'name': getattr(u, 'display_name', None)
               or (f'{u.last_name} {u.first_name}'.strip() if (u.last_name or u.first_name) else '')
               or u.get_username(),
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


# ---------- お問い合わせ ---------- #
class ContactThrottle(AnonRateThrottle):
    rate = '5/min'

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([ContactThrottle])
def contact(request):
    name = (request.data.get('name') or '').strip()
    email = (request.data.get('email') or '').strip()
    body = (request.data.get('body') or '').strip()
    honeypot = (request.data.get('website') or '').strip()

    # honeypot
    if honeypot:
        return Response({'ok': True})

    # バリデーション
    errors = {}
    if not name:
        errors['name'] = 'お名前を入力してください'
    if not email:
        errors['email'] = 'メールアドレスを入力してください'
    else:
        try:
            validate_email(email)
        except DjangoValidationError:
            errors['email'] = '正しいメールアドレスを入力してください'
    if not body:
        errors['body'] = 'お問い合わせ内容を入力してください'
    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    # メール本文
    now = timezone.now().strftime('%Y-%m-%d %H:%M:%S %Z')
    ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR', '')
    ua = request.META.get('HTTP_USER_AGENT', '')

    message = (
        f"お名前: {name}\n"
        f"メールアドレス: {email}\n\n"
        f"お問い合わせ内容:\n{body}\n\n"
        f"---\n"
        f"送信日時: {now}\n"
        f"IP: {ip}\n"
        f"User-Agent: {ua}\n"
    )

    send_mail(
        subject='【MONOLISK お問い合わせ】',
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=['info@monolisk-app.com'],
        fail_silently=False,
    )

    return Response({'ok': True}, status=status.HTTP_201_CREATED)
