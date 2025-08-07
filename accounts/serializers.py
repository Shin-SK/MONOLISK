# accounts/serializers.py  （※ 下記だけを残す）
from dj_rest_auth.serializers import LoginSerializer, UserDetailsSerializer
from rest_framework import serializers


class UserDetailsWithStoreSerializer(UserDetailsSerializer):
    store_id   = serializers.IntegerField(read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta(UserDetailsSerializer.Meta):
        fields = UserDetailsSerializer.Meta.fields + (
            "store_id", "store_name", "avatar_url",
        )

    def get_avatar_url(self, obj):
        url = getattr(obj, "avatar_url", None)
        if url:
            return url
        cast = getattr(obj, "cast_profile", None)   # related_name は環境に合わせて
        return getattr(cast, "avatar_url", None)


from dj_rest_auth.serializers import LoginSerializer
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.conf import settings

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
