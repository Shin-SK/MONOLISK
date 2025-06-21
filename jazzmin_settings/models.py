from core.models import (
    Store, Rank, Course, RankCourse,
    GroupOptionPrice, Driver
)

# ───────── ここから下はコピペで量産 ─────────
class StoreSetting(Store):
    class Meta:
        proxy = True
        verbose_name = "店舗"
        verbose_name_plural = "店舗"
        app_label = "jazzmin_settings"

class RankSetting(Rank):
    class Meta:
        proxy = True
        verbose_name = "ランク"
        verbose_name_plural = "ランク"
        app_label = "jazzmin_settings"

class CourseSetting(Course):
    class Meta:
        proxy = True
        verbose_name = "コース"
        verbose_name_plural = "コース"
        app_label = "jazzmin_settings"

class RankCourseSetting(RankCourse):
    class Meta:
        proxy = True
        verbose_name = "ランク別料金"
        verbose_name_plural = "ランク別料金"
        app_label = "jazzmin_settings"

class GroupOptionPriceSetting(GroupOptionPrice):
    class Meta:
        proxy = True
        verbose_name = "グループオプション料金"
        verbose_name_plural = "グループオプション料金"
        app_label = "jazzmin_settings"

class DriverSetting(Driver):
    class Meta:
        proxy = True
        verbose_name = "スタッフ"
        verbose_name_plural = "スタッフ"
        app_label = "jazzmin_settings"
