from django.contrib import admin
from . import models as m

proxy_models = [
    m.StoreProxy, m.RankProxy, m.CourseProxy, m.RankCourseProxy,
    m.GroupOptionPriceProxy, m.DriverProxy, m.CashFlowProxy,
    m.ReservationCastProxy, m.ReservationChargeProxy,
    m.CastCoursePriceProxy, m.CastOptionProxy,
]

for mdl in proxy_models:
    admin.site.register(mdl)          # 1 行登録
