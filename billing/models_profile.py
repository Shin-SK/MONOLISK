# billing/models_profile.py
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from cloudinary.models import CloudinaryField

class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='ユーザー',
    )
    avatar = CloudinaryField(
        'アバター',
        folder='avatars',
        format='jpg',
        blank=True, null=True,
    )

    class Meta:
        verbose_name = 'ユーザープロファイル'
        verbose_name_plural = 'ユーザープロファイル'

    def __str__(self):
        return f'Profile(user={self.user_id})'

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

def get_user_avatar_url(user) -> str | None:
    # UserProfile 優先
    prof = getattr(user, 'profile', None)
    if prof:
        try:
            if prof.avatar:
                return prof.avatar.url
        except Exception:
            pass
    # Cast をフォールバック
    cast = getattr(user, 'cast', None)
    if cast:
        try:
            if cast.avatar:
                return cast.avatar.url
        except Exception:
            pass
    return None
