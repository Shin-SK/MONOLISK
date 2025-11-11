# billing/resources.py
from import_export import resources, fields, widgets
from import_export.widgets import ForeignKeyWidget
from django.core.exceptions import ObjectDoesNotExist
from .models import ItemCategory, ItemMaster, Store, Table, SeatType, DiscountRule

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




# === Table (座席) の CSV ===
class TableRes(resources.ModelResource):
    store = fields.Field(
        column_name="store_slug",
        attribute="store",
        widget=widgets.ForeignKeyWidget(Store, "slug"),
    )
    seat_type = fields.Field(
        column_name="seat_type_code",
        attribute="seat_type",
        widget=widgets.ForeignKeyWidget(SeatType, "code"),
    )
    code = fields.Field(attribute="code", column_name="code")

    class Meta:
        model = Table
        import_id_fields = ("code", "store")          # 取り込み時用（任意）
        fields = ("store", "code", "seat_type")
        export_order = ("store", "code", "seat_type")

# === DiscountRule (割引ルール) の CSV ===
class DiscountRuleRes(resources.ModelResource):
    store = fields.Field(
        column_name="store_slug",
        attribute="store",
        widget=widgets.ForeignKeyWidget(Store, "slug"),
    )
    code           = fields.Field(attribute="code",           column_name="code")
    name           = fields.Field(attribute="name",           column_name="name")
    amount_off     = fields.Field(attribute="amount_off",     column_name="amount_off")
    percent_off    = fields.Field(attribute="percent_off",    column_name="percent_off")
    is_active      = fields.Field(attribute="is_active",      column_name="is_active",
                                  widget=widgets.BooleanWidget())
    is_basic       = fields.Field(attribute="is_basic",       column_name="is_basic",
                                  widget=widgets.BooleanWidget())
    show_in_basics = fields.Field(attribute="show_in_basics", column_name="show_in_basics",
                                  widget=widgets.BooleanWidget())
    show_in_pay    = fields.Field(attribute="show_in_pay",    column_name="show_in_pay",
                                  widget=widgets.BooleanWidget())
    sort_order     = fields.Field(attribute="sort_order",     column_name="sort_order")
    created_at     = fields.Field(attribute="created_at",     column_name="created_at")

    class Meta:
        model = DiscountRule
        import_id_fields = ("store", "code")   # 取り込み時の一意キー（任意）
        fields = ("store","code","name","amount_off","percent_off",
                  "is_active","is_basic","show_in_basics","show_in_pay",
                  "sort_order","created_at")
        export_order = ("store","code","name","amount_off","percent_off",
                        "is_active","is_basic","show_in_basics","show_in_pay",
                        "sort_order","created_at")




class TableRes(resources.ModelResource):
    # store 外部キーは slug で入出力
    store = fields.Field(
        attribute="store",
        column_name="store_slug",
        widget=ForeignKeyWidget(Store, "slug"),
    )
    # seat_type 外部キーは code で入出力
    seat_type = fields.Field(
        attribute="seat_type",
        column_name="seat_type_code",
        widget=ForeignKeyWidget(SeatType, "code"),
    )
    # 任意の識別子（UIで使ってれば）
    code = fields.Field(attribute="code", column_name="code")
    # テーブル番号を出したい場合（モデルに number があるなら）
    # number = fields.Field(attribute="number", column_name="number", widget=widgets.IntegerWidget())

    class Meta:
        model = Table
        # 取り込み時の一意キー（必要なら code を追加／変更）
        import_id_fields = ("store", "code",)
        # 出力/入力カラム順
        fields = ("store", "code", "seat_type")
        export_order = ("store", "code", "seat_type")
        skip_unchanged = True
        report_skipped = True
        use_transactions = True
        batch_size = 1000