from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        from dj_rest_auth.views import UserDetailsView
        from .serializers import UserDetailSerializer
        UserDetailsView.serializer_class = UserDetailSerializer
