# accounts/serializers.py  （※ 下記だけを残す）
from dj_rest_auth.serializers import LoginSerializer, UserDetailsSerializer
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.conf import settings
from django.templatetags.static import static
from cloudinary.utils import cloudinary_url


class UserDetailsWithStoreSerializer(UserDetailsSerializer):
    store_id   = serializers.IntegerField(read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta(UserDetailsSerializer.Meta):
        fields = UserDetailsSerializer.Meta.fields + ("store_id","store_name","avatar_url")

    def get_avatar_url(self, obj):
        # 1) ユーザー直下にURLがあれば最優先
        url = getattr(obj, "avatar_url", None)
        if url:
            return url

        # 2) Cast.avatar からCloudinary URLを生成（現在店舗優先）
        try:
            from billing.models import Cast
            store_id = self.context.get("store_id")
            if store_id is None:
                req = self.context.get("request")
                if req:
                    sid = req.query_params.get("store_id")
                    if sid and str(sid).isdigit():
                        store_id = int(sid)
                    elif getattr(req, "store", None):
                        store_id = req.store.id

            qs = Cast.objects.filter(user=obj)
            cast = qs.filter(store_id=store_id).first() if store_id else qs.first()
            if not cast:
                return None

            av = getattr(cast, "avatar", None)
            if av and getattr(av, "public_id", None):
                url, _ = cloudinary_url(av.public_id, format=(getattr(av, "format", "jpg") or "jpg"), secure=True)
                return url
        except Exception:
            pass

        # 3) ないなら None（フロントの <Avatar> がアイコン表示）
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
