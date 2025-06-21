# core/forms.py
from dal import autocomplete
from django import forms
from .models import Reservation, CastProfile, Course, RankCourse, ReservationCast

class ReservationForm(forms.ModelForm):
    # 追加した独自フィールド ──────────────
    cast_profile = forms.ModelChoiceField(
        queryset=CastProfile.objects.all(),
        label='キャスト',
        widget=autocomplete.ModelSelect2(
            url='cast-by-store',
            forward=['store'],
            attrs={
                'data-placeholder': 'キャストを入力…',
                'data-minimum-input-length': 0,
            }
        ),
        required=True,
    )
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        label='コース',
        required=True,
    )


    class Meta:
        model = Reservation
        # モデルに存在するフィールドだけ
        fields = [
            'store', 'start_at', 'customer',
            'manual_extra_price', 'received_amount',
            'driver', 'status',
        ]
        widgets = {
            "customer": autocomplete.ModelSelect2(
                url="customer-by-phone",
                attrs={
                    "data-placeholder": "電話番号を入力…",
                    "data-minimum-input-length": 2,
                },
            ),
        }


    # --- 予約保存時に ReservationCast を 1 行だけ同期 ---
    def save(self, commit=True):
        res = super().save(commit)
        rc_obj = RankCourse.objects.get(
            store  = res.store,
            rank   = self.cleaned_data['cast_profile'].rank,
            course = self.cleaned_data['course'],
        )
        ReservationCast.objects.update_or_create(
            reservation = res,
            defaults = {
                'cast_profile': self.cleaned_data['cast_profile'],
                'course':        self.cleaned_data['course'],
                'rank_course':   rc_obj,
            }
        )
        return res
