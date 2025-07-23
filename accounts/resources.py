from import_export import resources, fields, widgets
from django.contrib.auth import get_user_model
from billing.models import Cast, Staff, Store

User = get_user_model()


class UserRes(resources.ModelResource):
    # ── 基本 ───────────────────────────
    username = fields.Field("username")
    email    = fields.Field("email")
    is_staff = fields.Field(
        "is_staff", widget=widgets.BooleanWidget()
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
        return getattr(user.cast, "stage_name", "")

    def dehydrate_cast_store(self, user):
        cast = getattr(user, "cast", None)
        return cast.store.slug if cast and cast.store else ""

    def dehydrate_staff_stores(self, user):
        staff = getattr(user, "staff", None)
        return ",".join(s.slug for s in staff.stores.all()) if staff else ""

    # ---------- インポート用 ------------
    def after_save_instance(self, instance, *args, **kwargs):
        """
        User 保存後に
          • password ハッシュ化
          • Cast (1:1) 更新/作成
          • Staff (m2m) 更新/作成
        """
        row     = kwargs.get("row") or getattr(self, "_current_row", {})
        dry_run = kwargs.get("dry_run", False)
        if dry_run:
            return  # テストインポート時は何もしない

        # --- Password ---
        raw_pw = row.get("password")
        if raw_pw:
            instance.set_password(raw_pw)
        else:
            instance.set_unusable_password()
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
