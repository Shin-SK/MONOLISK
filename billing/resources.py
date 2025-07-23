# billing/resources.py  ← 新規
from import_export import resources, fields
from .models import ItemCategory, ItemMaster, Store

class ItemCategoryRes(resources.ModelResource):
    class Meta:
        model = ItemCategory
        import_id_fields = ("code",)          # ← 主キーなのでこれでユニーク判定
        fields = ("code", "name",
                  "back_rate_free",
                  "back_rate_nomination",
                  "back_rate_inhouse")

class ItemMasterRes(resources.ModelResource):
    # store を “slug” で読めるように追加フィールドを定義
    store = fields.Field(
        column_name="store_slug",
        attribute="store",
        widget=resources.widgets.ForeignKeyWidget(Store, "slug"),
    )

    class Meta:
        model = ItemMaster
        import_id_fields = ("code",)          # ← 店舗別なら (store,code) を推奨
        fields = ("store", "store_slug",      # store_slug はヘッダに必要！
                  "code", "name",
                  "category", "duration_min",
                  "price_regular", "price_late",
                  "apply_service",
                  "exclude_from_payout", "track_stock")
