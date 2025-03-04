# account/views.py

from django.contrib.auth import get_user_model
from rest_framework import viewsets, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import StoreUser, Store, Rank
from .serializers import UserSerializer, StoreSerializer, StoreUserCastSerializer, RankSerializer

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    """
    ユーザーのCRUDエンドポイント
    (クエリパラメータ ?role=cast 等でロールを絞り込み可能)
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = self.queryset
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        return queryset


class StoreListView(generics.ListAPIView):
    """
    店舗一覧を取得する API
    """
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [AllowAny]


class StoreCastsAPIView(APIView):
    """
    指定した店舗に所属するキャスト一覧。
    GETパラメータ ?store=◯◯ で絞り込み。
    指定なしの場合は全キャストを返す。
    """
    permission_classes = [AllowAny]

    def get(self, request):
        store_id = request.GET.get("store")
        if store_id:
            store_users = StoreUser.objects.filter(
                store_id=store_id,
                user__role="cast"
            )
        else:
            store_users = StoreUser.objects.filter(user__role="cast")

        serializer = StoreUserCastSerializer(store_users, many=True)
        return Response(serializer.data)


class StoreUserViewSet(viewsets.ModelViewSet):
    """
    店舗-キャスト間の中間テーブルStoreUserのCRUD。
    rank, star_count もここで更新可能にする想定。
    """
    queryset = StoreUser.objects.all()
    serializer_class = StoreUserCastSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        store_id = self.request.query_params.get('store')
        if store_id:
            queryset = queryset.filter(store_id=store_id)
        return queryset


class RankViewSet(viewsets.ModelViewSet):
    queryset = Rank.objects.all()
    serializer_class = RankSerializer
    permission_classes = [AllowAny]