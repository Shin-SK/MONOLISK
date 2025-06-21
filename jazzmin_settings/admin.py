from django.contrib import admin

from jazzmin_settings.models import (
    StoreSetting, RankSetting, CourseSetting,
    RankCourseSetting, GroupOptionPriceSetting, DriverSetting
)

# core 側の Admin クラスを再利用
from core.admin import (
    StoreAdmin, RankAdmin, CourseAdmin,
    RankCourseAdmin, GroupOptionPriceAdmin, DriverAdmin
)

admin.site.register(StoreSetting,          StoreAdmin)
admin.site.register(RankSetting,           RankAdmin)
admin.site.register(CourseSetting,         CourseAdmin)
admin.site.register(RankCourseSetting,     RankCourseAdmin)
admin.site.register(GroupOptionPriceSetting, GroupOptionPriceAdmin)
admin.site.register(DriverSetting,         DriverAdmin)
