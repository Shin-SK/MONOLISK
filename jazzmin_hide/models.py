from core import models as c


# ───────── マスタ系 ─────────
class StoreProxy(c.Store):
    class Meta:
        proxy = True
        app_label = "jazzmin_hide"
        verbose_name = "店舗"
        verbose_name_plural = verbose_name


class RankProxy(c.Rank):
    class Meta:
        proxy = True
        app_label = "jazzmin_hide"
        verbose_name = "ランク"
        verbose_name_plural = verbose_name


class CourseProxy(c.Course):
    class Meta:
        proxy = True
        app_label = "jazzmin_hide"
        verbose_name = "コース"
        verbose_name_plural = verbose_name


class RankCourseProxy(c.RankCourse):
    class Meta:
        proxy = True
        app_label = "jazzmin_hide"
        verbose_name = "ランク別料金"
        verbose_name_plural = verbose_name


class GroupOptionPriceProxy(c.GroupOptionPrice):
    class Meta:
        proxy = True
        app_label = "jazzmin_hide"
        verbose_name = "グループオプション料金"
        verbose_name_plural = verbose_name


# ───────── 人員／会計系 ─────────
class DriverProxy(c.Driver):
    class Meta:
        proxy = True
        app_label = "jazzmin_hide"
        verbose_name = "スタッフ"
        verbose_name_plural = verbose_name


class CashFlowProxy(c.CashFlow):
    class Meta:
        proxy = True
        app_label = "jazzmin_hide"
        verbose_name = "入出金"
        verbose_name_plural = verbose_name


# ───────── 予約サブテーブル系 ─────────
class ReservationCastProxy(c.ReservationCast):
    class Meta:
        proxy = True
        app_label = "jazzmin_hide"
        verbose_name = "予約-キャスト行"
        verbose_name_plural = verbose_name


class ReservationChargeProxy(c.ReservationCharge):
    class Meta:
        proxy = True
        app_label = "jazzmin_hide"
        verbose_name = "予約-追加料金行"
        verbose_name_plural = verbose_name


# ───────── キャスト個別価格系 ─────────
class CastCoursePriceProxy(c.CastCoursePrice):
    class Meta:
        proxy = True
        app_label = "jazzmin_hide"
        verbose_name = "キャスト-コース個別価格"
        verbose_name_plural = verbose_name


class CastOptionProxy(c.CastOption):
    class Meta:
        proxy = True
        app_label = "jazzmin_hide"
        verbose_name = "キャスト-オプション個別価格"
        verbose_name_plural = verbose_name
