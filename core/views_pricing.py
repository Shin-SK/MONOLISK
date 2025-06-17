# views_pricing.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import CastProfile, Course, RankCourse, CastCoursePrice

class PricingAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cp_id   = request.query_params.get("cast_profile")
        course_id = request.query_params.get("course")
        if not (cp_id and course_id):
            return Response({"detail": "params missing"}, status=400)

        cp     = CastProfile.objects.select_related("rank", "store").get(pk=cp_id)
        course = Course.objects.get(pk=course_id)

        # 基準価格  (店×ランク×コース)
        rc = RankCourse.objects.get(store=cp.store, rank=cp.rank, course=course)
        price = rc.base_price + rc.star_increment * cp.star_count

        # キャスト個別上書き
        override = CastCoursePrice.objects.filter(
            cast_profile=cp, course=course
        ).first()
        if override and override.custom_price is not None:
            price = override.custom_price

        return Response({"price": price})
