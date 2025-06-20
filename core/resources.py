# admin.py か resources.py に追記
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import RankCourse, Store, Rank, Course

class RankCourseRes(resources.ModelResource):
    # ─── 外部キー列を “人間が読める値” でやり取り ───
    store  = fields.Field(
        column_name="store",
        attribute="store",
        widget=ForeignKeyWidget(Store, "name"),
    )
    rank   = fields.Field(
        column_name="rank",
        attribute="rank",
        widget=ForeignKeyWidget(Rank, "name"),
    )
    course = fields.Field(
        column_name="course",
        attribute="course",
        widget=ForeignKeyWidget(Course, "minutes"),
    )

    class Meta:
        model = RankCourse
        # ─ 既存レコードを一意に特定する列 ─
        import_id_fields = ("store", "rank", "course")
        fields = (
            "store", "rank", "course",
            "base_price", "star_increment",
        )
        skip_unchanged  = True
        report_skipped  = True
