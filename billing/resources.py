# billing/resources.py
from import_export import resources, fields, widgets
from import_export.widgets import ForeignKeyWidget
from .models import ItemCategory, ItemMaster, Store

class ItemCategoryRes(resources.ModelResource):
    class Meta:
        model = ItemCategory
        import_id_fields = ("code",)
        fields = (
            "code","name",
            "back_rate_free","back_rate_nomination","back_rate_inhouse",
            "show_in_menu","route",
        )
        export_order = (
            "code","name",
            "back_rate_free","back_rate_nomination","back_rate_inhouse",
            "show_in_menu","route",
        )
        skip_unchanged = True
        report_skipped = True
        use_transactions = True
        batch_size = 1000



# billing/resources.py
from import_export import resources, fields, widgets
from import_export.widgets import ForeignKeyWidget
from .models import ItemCategory, ItemMaster, Store
from django.core.exceptions import ObjectDoesNotExist

class ItemMasterRes(resources.ModelResource):
    # CSV: store_slug -> Store.slug
    store = fields.Field(
        attribute="store",
        column_name="store_slug",
        widget=ForeignKeyWidget(Store, "slug"),
    )
    # CSV: category -> ItemCategory.code
    category = fields.Field(
        attribute="category",
        column_name="category",
        widget=ForeignKeyWidget(ItemCategory, "code"),
    )

    # ★ ここから “attribute” を明示
    code          = fields.Field(attribute="code",          column_name="code")
    name          = fields.Field(attribute="name",          column_name="name")
    duration_min  = fields.Field(attribute="duration_min",  column_name="duration_min",  widget=widgets.IntegerWidget())
    price_regular = fields.Field(attribute="price_regular", column_name="price_regular", widget=widgets.IntegerWidget())
    price_late    = fields.Field(attribute="price_late",    column_name="price_late",    widget=widgets.IntegerWidget())
    apply_service       = fields.Field(attribute="apply_service",       column_name="apply_service",       widget=widgets.BooleanWidget())
    exclude_from_payout = fields.Field(attribute="exclude_from_payout", column_name="exclude_from_payout", widget=widgets.BooleanWidget())
    track_stock         = fields.Field(attribute="track_stock",         column_name="track_stock",         widget=widgets.BooleanWidget())
    route               = fields.Field(attribute="route",               column_name="route")

    class Meta:
        model = ItemMaster
        import_id_fields = ("store", "code")  # 文字列のみ
        fields = (
            "store","code","name","category","duration_min",
            "price_regular","price_late",
            "apply_service","exclude_from_payout","track_stock","route",
        )
        export_order = (
            "store","code","name","category","duration_min",
            "price_regular","price_late",
            "apply_service","exclude_from_payout","track_stock","route",
        )
        skip_unchanged = True
        report_skipped = True
        use_transactions = True
        batch_size = 1000

    # code が空のときの既存検索で落ちないよう保険
    def get_instance(self, instance_loader, row):
        store_slug = row.get(self.fields['store'].column_name)
        code_val   = row.get(self.fields['code'].column_name)
        if not code_val:
            return None
        store_obj = self.fields['store'].clean(row)
        try:
            return ItemMaster.objects.get(store=store_obj, code=code_val)
        except ObjectDoesNotExist:
            return None
