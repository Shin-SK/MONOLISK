from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import generics
from .serializers import UserSerializer, StoreSerializer, StoreUserCastSerializer
from django.contrib.auth import get_user_model
from .models import StoreUser, Store

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()  # この行を追加
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


class StoreCastsAPIView(APIView):
    """
    指定した店舗に所属するキャスト一覧（StoreUserベース）。
    店舗IDが指定されていない場合は、全キャストを返す。
    """
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
        return Response({"casts": serializer.data})
