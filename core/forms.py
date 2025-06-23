from dal import autocomplete
from django import forms
from .models import (
    Reservation, CastProfile, Course,
    RankCourse, ReservationCast
)

class ReservationForm(forms.ModelForm):
    # 追加フィールド ──────────
    cast_profile = forms.ModelChoiceField(
        queryset=CastProfile.objects.all(),
        label='キャスト',
        widget=autocomplete.ModelSelect2(
            url='cast-by-store',
            forward=['store'],
            attrs={'data-placeholder': 'キャストを入力…'}
        ),
        required=True,
    )
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        label='コース',
        required=True,
    )

    class Meta:
        model  = Reservation
        fields = [
            'store', 'start_at', 'customer',
            'manual_extra_price', 'received_amount',
            'driver', 'status',
        ]
        widgets = {
            'customer': autocomplete.ModelSelect2(
                url='customer-by-phone',
                attrs={'data-placeholder': '電話番号を入力…',
                       'data-minimum-input-length': 2},
            ),
        }

    def __init__(self, *args, **kwargs):
        """
        - add_view → instance=None なので何もしない
        - change_view → instance=<Reservation …> が来るので
          予約に紐づく最初の ReservationCast を使って初期値を入れる
        """
        super().__init__(*args, **kwargs)

        instance = kwargs.get("instance")
        if not instance:                    # 追加モードのときはスキップ
            return

        # 予約に紐づく 1 行目のキャスト／コースを取得
        rc = instance.casts.first()
        if rc:
            self.fields["cast_profile"].initial = rc.cast_profile
            self.fields["course"].initial       = rc.course

    # -----------------------------
    # ここからフォーム全体の save
    # -----------------------------
    def save(self, commit=True):
        # ① モデル本体を生成（admin からは commit=False で来る）
        reservation = super().save(commit=False)
        reservation.total_time = self.cleaned_data['course'].minutes

        # ★ まだ pk が無ければ一度 save して pk を確定させる
        if reservation.pk is None:
            reservation.save()

        # ② 子テーブルを同期
        rc_obj = RankCourse.objects.get(
            store = reservation.store,
            rank  = self.cleaned_data['cast_profile'].rank,
            course= self.cleaned_data['course'],
        )

        ReservationCast.objects.update_or_create(
            reservation   = reservation,                # ← もう pk あり
            defaults = {
                'cast_profile': self.cleaned_data['cast_profile'],
                'course':       self.cleaned_data['course'],
                'rank_course':  rc_obj,
            }
        )

        # ③ commit=False で呼ばれている場合は、呼び出し元(admin)が
        #    最終的に save() してくれるのでそのまま返す
        if commit:
            reservation.save()
        return reservation
