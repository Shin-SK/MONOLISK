# accounts/serializers.py
from dj_rest_auth.serializers import LoginSerializer, UserDetailsSerializer
from rest_framework import serializers

class UserDetailsWithStoreSerializer(UserDetailsSerializer):
    store_id   = serializers.IntegerField(read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True)

    # ←★ 追加 : Cast 側にだけある avatar_url を引っ張ってくる
    avatar_url = serializers.SerializerMethodField()

    class Meta(UserDetailsSerializer.Meta):
        # avatar_url を追加する
        fields = UserDetailsSerializer.Meta.fields + (
            "store_id",
            "store_name",
            "avatar_url",
        )

    def get_avatar_url(self, obj):
        """
        - User モデル自体に avatar_url フィールドが無い場合は
          related 名 `cast_profile.avatar_url` (例) を見る
        - どちらも無ければ None を返す
        """
        # ① User.avatar_url があれば優先
        url = getattr(obj, "avatar_url", None)
        if url:
            return url

        # ② User → CastProfile (OneToOne) 側
        cast = getattr(obj, "cast_profile", None)  # related_name は適宜変更
        return getattr(cast, "avatar_url", None)


class LoginWithStoreSerializer(LoginSerializer):
    """
    /dj-rest-auth/login/ のレスポンスを拡張
    """
    def validate(self, attrs):
        data = super().validate(attrs)

        data["store_id"]   = self.user.store_id
        data["store_name"] = getattr(self.user.store, "name", None)

        # ★ avatar_url を追加
        data["avatar_url"] = (
            getattr(self.user, "avatar_url", None)
            or getattr(getattr(self.user, "cast_profile", None), "avatar_url", None)
        )
        return data
