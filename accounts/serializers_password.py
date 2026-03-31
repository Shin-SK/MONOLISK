# accounts/serializers_password.py
from urllib.parse import urlencode

from django.conf import settings
from dj_rest_auth.serializers import PasswordResetSerializer
from allauth.account.utils import user_pk_to_url_str


def frontend_url_generator(request, user, temp_key):
    """パスワードリセットメールのリンク先をフロントエンドURLにする"""
    uid = user_pk_to_url_str(user)
    params = urlencode({'uid': uid, 'token': temp_key})
    return f"{settings.FRONTEND_URL}/password-reset/confirm?{params}"


class FrontendPasswordResetSerializer(PasswordResetSerializer):
    def get_email_options(self):
        return {'url_generator': frontend_url_generator}
