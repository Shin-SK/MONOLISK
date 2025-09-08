# accounts/resources.py
from import_export import resources, fields, widgets
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from billing.models import Cast, Staff, Store

User = get_user_model()


class UserRes(resources.ModelResource):
    # ── 基本 ───────────────────────────
    username = fields.Field(attribute="username", column_name="username")
    email    = fields.Field(attribute="email",    column_name="email")
    is_staff = fields.Field(
        attribute="is_staff", column_name="is_staff",
        widget=widgets.BooleanWidget()
    )

    # ── Cast 1:1 ───────────────────────
    stage_name = fields.Field(column_name="stage_name")
    cast_store = fields.Field(
        column_name="cast_store_slug",
        widget=widgets.ForeignKeyWidget(Store, "slug"),
    )

    # ── Staff m2m ──────────────────────
    staff_stores = fields.Field(column_name="staff_store_slugs")

    # ── Password (平文) ────────────────
    password = fields.Field(column_name="password")

    class Meta:
        model            = User
        import_id_fields = ("username",)
        skip_unchanged   = True
        report_skipped   = True

    # ---------- エクスポート用 ----------
    def dehydrate_stage_name(self, user):
        try:
            return user.cast.stage_name
        except ObjectDoesNotExist:
            return ""

    def dehydrate_cast_store(self, user):
        try:
            cast = user.cast
            return cast.store.slug if getattr(cast, "store_id", None) else ""
        except ObjectDoesNotExist:
            return ""

    def dehydrate_staff_stores(self, user):
        try:
            staff = user.staff
            return ",".join(s.slug for s in staff.stores.all())
        except ObjectDoesNotExist:
            return ""

    # ---------- インポート用 ------------
    def after_save_instance(self, instance, *args, **kwargs):
        """
        User 保存後に
          • password ハッシュ化（指定時のみ）
          • Cast (1:1) 更新/作成（stage_name 指定時）
          • Staff (m2m) 更新/作成（staff_store_slugs 指定時）
        """
        row     = kwargs.get("row") or getattr(self, "_current_row", {}) or {}
        dry_run = kwargs.get("dry_run", False)
        if dry_run:
            return  # テストインポート時は何もしない

        # --- Password（指定がある時だけ更新） ---
        raw_pw = row.get("password")
        if raw_pw:
            instance.set_password(raw_pw)
            instance.save(update_fields=["password"])

        # --- Cast (OneToOne) ---
        stage = row.get("stage_name")
        if stage:
            store_slug = row.get("cast_store_slug")
            store_obj  = Store.objects.filter(slug=store_slug).first() if store_slug else None
            Cast.objects.update_or_create(
                user=instance,
                defaults={"stage_name": stage, "store": store_obj},
            )

        # --- Staff (ManyToMany) ---
        slugs = row.get("staff_store_slugs", "")
        if slugs:
            qs = Store.objects.filter(
                slug__in=[s.strip() for s in slugs.split(",") if s.strip()]
            )
            staff, _ = Staff.objects.get_or_create(user=instance)
            staff.stores.set(qs)
