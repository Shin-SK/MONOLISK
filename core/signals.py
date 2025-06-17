# core/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Cast, Course, Option, CastCoursePrice, CastOption

@receiver(post_save, sender=Cast)
def create_full_lines(sender, instance, created, **kwargs):
    if not created:
        return
    # Course 全件
    CastCoursePrice.objects.bulk_create([
        CastCoursePrice(cast=instance, course=c)
        for c in Course.objects.all()
    ])
    # Option 全件
    CastOption.objects.bulk_create([
        CastOption(cast=instance, option=o)
        for o in Option.objects.all()
    ])
