from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import StoreUser, Store

User = get_user_model()

class StoreUserSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name")  # 店舗名
    nickname = serializers.CharField()  # ニックネーム

    class Meta:
        model = StoreUser
        fields = ["store_name", "nickname"]


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ["id", "name"]  # 必要なら他のフィールドも追加


class UserSerializer(serializers.ModelSerializer):
    stores = StoreUserSerializer(source="storeuser_set", many=True)  # `StoreUser` の情報をネスト

    class Meta:
        model = User
        fields = ["id", "username", "full_name", "role", "stores"]  # `stores` を追加


class StoreUserCastSerializer(serializers.ModelSerializer):
    """
    店舗に紐づく User（role=cast）を取得する際、
    storeごとのニックネームを返す。
    """
    user_id = serializers.IntegerField(source='user.id')
    full_name = serializers.CharField(source='user.full_name')

    class Meta:
        model = StoreUser
        fields = ['user_id', 'nickname', 'full_name']


class CastWithNicknamesSerializer(serializers.ModelSerializer):
    # 全店舗のニックネームをリストとして返すフィールド
    nicknames = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "full_name", "nicknames"]

    def get_nicknames(self, obj):
        # obj.storeuser_set.all() で関連するStoreUserレコードを取得し、
        # その中のnicknameを抽出
        return [store_user.nickname for store_user in obj.storeuser_set.all()]