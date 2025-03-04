from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import StoreUser, Store, Rank

User = get_user_model()

class StoreUserSerializer(serializers.ModelSerializer):
    user_id = serializers.ReadOnlyField(source='user.id')
    full_name = serializers.ReadOnlyField(source='user.full_name')
    nickname = serializers.CharField()
    # 追加: rankやstar_countを返したければここで定義
    rank_name = serializers.ReadOnlyField(source='rank.name', default=None)
    star_count = serializers.IntegerField(default=0)

    class Meta:
        model = StoreUser
        fields = [
          'id',  # ← StoreUser PK
          'user_id',
          'full_name',
          'nickname',
          'rank_name',
          'star_count'
        ]


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
    id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField(source='user.id')
    full_name = serializers.CharField(source='user.full_name')
    nickname = serializers.CharField()

    rank_id = serializers.IntegerField(source='rank.id', allow_null=True)  # ← 追加
    rank_name = serializers.ReadOnlyField(source='rank.name', default=None)
    star_count = serializers.IntegerField(default=0)

    class Meta:
        model = StoreUser
        fields = [
            'id',
            'user_id',
            'nickname',
            'full_name',
            'rank_id',     # rankのPK
            'rank_name',   # rankの名称
            'star_count'
        ]



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



class RankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rank
        fields = [
            'id',
            'name',
            'price_60',
            'price_75',
            'price_90',
            'price_120',
            'price_150',
            'price_180',
            'price_extension_30',
            'plus_per_star',
        ]