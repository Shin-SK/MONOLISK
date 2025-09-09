# accounts/serializers.py  （※ 下記だけを残す）
from dj_rest_auth.serializers import LoginSerializer, UserDetailsSerializer
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.conf import settings
from django.templatetags.static import static
from cloudinary.utils import cloudinary_url
from dj_rest_auth.serializers import TokenSerializer
from accounts.utils import choose_current_store_id

class UserDetailsWithStoreSerializer(UserDetailsSerializer):
    store_id   = serializers.IntegerField(read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta(UserDetailsSerializer.Meta):
        fields = UserDetailsSerializer.Meta.fields + ("store_id","store_name","avatar_url")

    def _abs(self, req, url:str|None):
        if not url: return None
        return req.build_absolute_uri(url) if req and not url.startswith('http') else url

    def get_avatar_url(self, obj):
        """
        優先度:
          0) obj.avatar_url（ユーザー直下にURLがあれば）
          1) 現在店舗の Cast.avatar
          2) 他店舗の Cast.avatar（最初に見つかったもの）
          3) 無ければ None（＝フロント側でデフォルトアイコン）
        """
        # 0) ユーザー直下
        if getattr(obj, "avatar_url", None):
            return self._abs(self.context.get("request"), obj.avatar_url)

        # 現在店舗IDの推定（context.store_id → Header → request.store → query）
        req = self.context.get("request")
        store_id = self.context.get("store_id")
        if store_id is None and req:
            hs = req.headers.get("X-Store-Id")
            if hs and hs.isdigit():
                store_id = int(hs)
            elif getattr(req, "store", None):
                store_id = req.store.id
            else:
                qs = req.query_params.get("store_id")
                if qs and qs.isdigit():
                    store_id = int(qs)

        # 1) 現在店舗 → 2) 他店舗
        try:
            from billing.models import Cast
            qs = Cast.objects.filter(user=obj)
            cand = None
            if store_id:
                cand = qs.filter(store_id=store_id, avatar__isnull=False).first()
            if not cand:
                cand = qs.filter(avatar__isnull=False).first()
            if not cand:
                return None

            av = getattr(cand, "avatar", None)
            # CloudinaryField
            if getattr(av, "public_id", None):
                url, _ = cloudinary_url(
                    av.public_id,
                    format=(getattr(av, "format", "jpg") or "jpg"),
                    secure=True
                )
                return url
            # ImageField 等
            if hasattr(av, "url") and av.url:
                return self._abs(req, av.url)
        except Exception:
            pass
        return None


class LoginWithStoreSerializer(LoginSerializer):
    """
    Token / JWT どちらでも動く。
    - TokenAuthentication:   key を返す
    - JWT (REST_USE_JWT=True): access / refresh を返す
    フロントは常に 'key' (＝アクセストークン) を読む想定
    """

    def validate(self, attrs):
        data  = super().validate(attrs)      # ← ここで {"user": user} が入る
        user  = data["user"]

        token, _      = Token.objects.get_or_create(user=user)
        data["key"]   = token.key
        data["store_id"] = getattr(user, "store_id", None)

        return data   # ※ user は残したまま（LoginView が使う）


class TokenWithStoreSerializer(TokenSerializer):
    """ログインレスポンスに store_id（= current_store_id）を同梱"""
    store_id = serializers.IntegerField(read_only=True)

    class Meta(TokenSerializer.Meta):
        fields = TokenSerializer.Meta.fields + ('store_id',)  # ★ これを追加

    def to_representation(self, instance):
        data = super().to_representation(instance)  # {"key": "..."}
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        store_id = None
        if user and user.is_authenticated:
            try:
                store_id, *_ = choose_current_store_id(request, user)
            except Exception:
                store_id = getattr(user, 'store_id', None)
        data['store_id'] = store_id
        return data
