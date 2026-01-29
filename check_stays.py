#!/usr/bin/env python
"""Bill.stays の中身を確認（特に本指名の cast 情報）"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from billing.models import Bill

# bill=117を取得
b = Bill.objects.select_related('table').prefetch_related('stays__cast').get(id=117)
print(f"\n【Bill ID: {b.id}, pax: {b.pax}】")

# stays を確認
print(f"\n✅ stays の件数: {b.stays.count()}")

print("\n📋 各 stay の詳細:")
for s in b.stays.all():
    print(f"\n  Stay ID: {s.id}")
    print(f"    stay_type: {s.stay_type}")
    print(f"    is_help: {s.is_help}")
    print(f"    entered_at: {s.entered_at}")
    print(f"    left_at: {s.left_at}")
    
    # cast 情報を確認
    if s.cast:
        print(f"    cast.id: {s.cast.id}")
        print(f"    cast.stage_name: {s.cast.stage_name}")
        # avatarフィールドの確認（.urlでアクセス）
        avatar = getattr(s.cast, 'avatar', None)
        if avatar:
            print(f"    cast.avatar: {avatar.url if avatar else '(なし)'}")
        else:
            print(f"    cast.avatar: (なし)")
    else:
        print(f"    ❌ cast: None （関連データなし）")

# 本指名だけフィルタ
nom_stays = b.stays.filter(stay_type='nom', left_at__isnull=True)
print("\n" + "="*60)
print(f"📍 本指名（nom）で現在着席中の stay: {nom_stays.count()}件")
print("="*60)

for s in nom_stays:
    print(f"\n  Stay ID: {s.id}, Cast ID: {s.cast_id if s.cast_id else '(なし)'}")
    if s.cast:
        print(f"    ✅ stage_name: {s.cast.stage_name}")
        avatar = getattr(s.cast, 'avatar', None)
        if avatar:
            print(f"    ✅ avatar: {avatar.url if avatar else '(なし)'}")
        else:
            print(f"    ✅ avatar: (なし)")
    else:
        print(f"    ❌ cast情報が取得できていません")

print("\n" + "="*60)
print("結論:")
all_have_cast = all(s.cast is not None for s in nom_stays)
if all_have_cast:
    print("✅ すべての本指名に cast 情報がある → フロントエンド側の問題")
else:
    print("❌ cast 情報が欠けている stay がある → バックエンド serializer の問題")
print("="*60)
