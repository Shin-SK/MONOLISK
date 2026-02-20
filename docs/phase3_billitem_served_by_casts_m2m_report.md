# Phase 3 Backend Report: BillItem 担当キャスト M2M 保存対応

**実装完了日**: 2026年2月20日

## 実装概要

BillItem に「担当キャスト複数」を保存できる M2M を追加し、API 入出力で `served_by_cast_ids: [1,2,3]` を扱えるようにしました。既存の単一FK `served_by_cast` は互換用途として維持し、`served_by_cast_ids` の先頭IDを同期します。

> スコープ外のため、給与/バック計算ロジックは変更していません。

---

## 変更内容

### 1) モデル変更

**ファイル**: [billing/models.py](billing/models.py)

- `BillItemCast` 中間モデルを追加
  - `bill_item` FK (`related_name='served_by_links'`)
  - `cast` FK (`related_name='served_bill_item_links'`)
  - `created_at` (`auto_now_add=True`)
  - 一意制約: `uniq_billitem_cast`（`bill_item`, `cast`）
- `BillItem` に M2M フィールド追加
  - `served_by_casts = models.ManyToManyField('billing.Cast', through='BillItemCast', related_name='served_items_m2m', blank=True)`
- 既存 `served_by_cast` はそのまま維持（互換）

### 2) マイグレーション

**ファイル**: [billing/migrations/0127_billitemcast_billitem_served_by_casts_and_more.py](billing/migrations/0127_billitemcast_billitem_served_by_casts_and_more.py)

- `BillItemCast` テーブル作成
- `BillItem.served_by_casts` 追加
- 一意制約 `uniq_billitem_cast` 追加

### 3) Serializer 変更

**ファイル**: [billing/serializers.py](billing/serializers.py)

- `BillItemSerializer` に `served_by_cast_ids`（ListField[Integer]）を追加
- `to_representation` で `served_by_cast_ids` を返却
  - `list(instance.served_by_casts.values_list('id', flat=True))`
- `create` / `update` で `served_by_cast_ids` を受け取り、M2M を置換
  - `obj.served_by_casts.set(ids)`
  - 互換同期: `obj.served_by_cast_id = ids[0] if ids else None`
- store lock を維持
  - `served_by_cast_ids` に他店舗キャスト/存在しないIDが含まれる場合はValidationError

### 4) API経路確認

**ファイル**: [billing/views.py](billing/views.py)

- `BillItemViewSet.serializer_class = BillItemSerializer` のため、
  - `addBillItem`（POST相当）
  - `patchBillItem`（PATCH相当）
  で `served_by_cast_ids` を受け取り可能

---

## 互換性ポリシー

- 既存クライアントのため `served_by_cast` 単一FKは残置
- 新規クライアントは `served_by_cast_ids` を使用
- 更新時は `served_by_cast_ids` の先頭を `served_by_cast` に同期

---

## 動作確認手順（ターミナル / manage.py shell）

以下を **`python manage.py shell` の `>>>` で順に実行**してください。

```python
from types import SimpleNamespace
from django.utils import timezone
from django.contrib.auth import get_user_model
from billing.models import Store, Table, Bill, Cast, ItemMaster
from billing.serializers import BillItemSerializer

User = get_user_model()
store = Store.objects.order_by('id').first()
table = Table.objects.filter(store=store).order_by('id').first() or Table.objects.create(store=store, code=f'AUTO{store.id}')
bill = Bill.objects.filter(table__store=store, closed_at__isnull=True).order_by('id').first() or Bill.objects.create(table=table, opened_at=timezone.now())

casts = list(Cast.objects.filter(store=store).order_by('id')[:3])
for i in range(3 - len(casts)):
    u = User.objects.create_user(username=f'm2m_cast_{store.id}_{timezone.now().strftime("%Y%m%d%H%M%S%f")}_{i}', password='x')
    casts.append(Cast.objects.create(user=u, store=store, stage_name=f'M2M Cast {i+1}'))

cast_ids = [c.id for c in casts[:3]]
payload = {'name': 'M2M確認用', 'price': 1000, 'qty': 1, 'served_by_cast_ids': cast_ids[:2]}
im = ItemMaster.objects.filter(store=store).order_by('id').first() or ItemMaster.objects.filter(store__isnull=True).order_by('id').first()
if im:
    payload['item_master'] = im.id

ctx = {'request': SimpleNamespace(store=store)}

# POST相当
s = BillItemSerializer(data=payload, context=ctx)
s.is_valid(raise_exception=True)
obj = s.save(bill=bill)
post_data = BillItemSerializer(instance=obj, context=ctx).data
print('POST served_by_cast_ids:', post_data.get('served_by_cast_ids'))
print('POST served_by_cast FK:', (post_data.get('served_by_cast') or {}).get('id'))

# PATCH相当
p = BillItemSerializer(instance=obj, data={'served_by_cast_ids': cast_ids}, partial=True, context=ctx)
p.is_valid(raise_exception=True)
obj = p.save()
obj.refresh_from_db()
print('PATCH served_by_cast_ids:', list(obj.served_by_casts.values_list('id', flat=True)))
print('PATCH served_by_cast FK:', obj.served_by_cast_id)
```

期待結果:
- POST: `served_by_cast_ids == [A, B]`
- PATCH: `served_by_cast_ids == [A, B, C]`
- `served_by_cast`（単数FK）は常に先頭（`A`）

---

## 影響範囲

- 追加: BillItem の担当キャスト複数保存
- 互換: 既存 `served_by_cast` 維持
- 非変更: 給与/バック計算ロジック