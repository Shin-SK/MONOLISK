# billing/serializers_user_details.py
from dj_rest_auth.serializers import UserDetailsSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models_profile import UserProfile, get_user_avatar_url

User = get_user_model()

class UserDetailsWithAvatarSerializer(UserDetailsSerializer):
    avatar_url = serializers.SerializerMethodField(read_only=True)
    avatar     = serializers.ImageField(write_only=True, required=False)

    class Meta(UserDetailsSerializer.Meta):
        fields = tuple(UserDetailsSerializer.Meta.fields) + ('avatar_url', 'avatar')

    def get_avatar_url(self, user: User):
        return get_user_avatar_url(user)

    def update(self, instance: User, validated_data):
        avatar_file = validated_data.pop('avatar', None)
        user = super().update(instance, validated_data)
        if avatar_file is not None:
            prof, _ = UserProfile.objects.get_or_create(user=user)
            prof.avatar = avatar_file
            prof.save(update_fields=['avatar'])
        return user
