# accounts/form.py
from dj_rest_auth.registration.serializers import RegisterSerializer


class MyRegisterSerializer(RegisterSerializer):
    email = serializers.EmailField(required=False, allow_blank=True)