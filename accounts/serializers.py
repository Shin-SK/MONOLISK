# accounts/serializers.py

from dj_rest_auth.serializers import LoginSerializer, UserDetailsSerializer, TokenSerializer
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
from accounts.utils import choose_current_store_id
from billing.models_profile import get_user_avatar_url

User = get_user_model()


class UserDetailsWithStoreSerializer(UserDetailsSerializer):
    store_id   = serializers.IntegerField(read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta(UserDetailsSerializer.Meta):
        fields = UserDetailsSerializer.Meta.fields + (
            "store_id", "store_name", "avatar_url",
        )

    def get_avatar_url(self, obj: User):
        """
        優先: UserProfile.avatar → フォールバック: Cast.avatar
        """
        url = get_user_avatar_url(obj)              # ← user ではなく obj を渡す
        if not url:
            return None
        req = self.context.get("request")
        return req.build_absolute_uri(url) if req and not str(url).startswith("http") else url


class LoginWithStoreSerializer(LoginSerializer):
    """
    Token / JWT どちらでも動く。
    - TokenAuthentication: key を返す
    - JWT: access / refresh を返す
    """
    def validate(self, attrs):
        data  = super().validate(attrs)    # {"user": user}
        user  = data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        data["key"] = token.key
        data["store_id"] = getattr(user, "store_id", None)
        return data


class TokenWithStoreSerializer(TokenSerializer):
    """ログインレスポンスに store_id（= current_store_id）を同梱"""
    store_id = serializers.IntegerField(read_only=True)

    class Meta(TokenSerializer.Meta):
        fields = TokenSerializer.Meta.fields + ('store_id',)

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
