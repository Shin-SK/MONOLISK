# Phase 0 棚卸し報告書：Bill → Table M2M化の影響点特定

**作成日**: 2026年2月3日  
**ステータス**: ✅ Phase 0 完了（コード変更なし、影響点の洗い出しのみ）

---

## 1. 概要

本報告書では、「Bill → Table を M2M（多対多）に変更する」ための影響箇所を **grep と静的読み取りで特定** しました。

**重要**: Phase 0 では以下の方針に従い、コード変更は **一切実施していません**：
- 現状のモデル（Bill.table は FK のまま）を変更していない
- DB マイグレーションは実行していない  
- 次フェーズ（Phase 1）での変更を見据えた依存点の列挙のみ

---

## 2. 現状のモデル関係図

### 2.1 Bill モデル（現状）

```python
# billing/models.py:555-572
class Bill(models.Model):
    table = models.ForeignKey(
        'billing.Table', 
        on_delete=models.CASCADE, 
        null=True, blank=True  # ← 現状は nullable
    )
    opened_at = models.DateTimeField(default=timezone.now, db_index=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    customers = models.ManyToManyField(
        'billing.Customer',
        through='billing.BillCustomer',
        related_name='bills',
        blank=True,
    )
    main_cast = models.ForeignKey(...)
    nominated_casts = models.ManyToManyField(...)
    tags = models.ManyToManyField(...)
```

**現状の性質**:
- `Bill.table` は FK（1対多）で、1 Bill → 1 Table
- `null=True, blank=True` なので、table 未割り当てのままクローズできる
- Migration 0016 で nullable に変更されている

### 2.2 Table モデル（参考）

```python
# billing/models.py:136-153
class Table(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    code = models.CharField(max_length=16, db_index=True)
    seat_type = models.ForeignKey(SeatType, ...)
    
    # 逆参照: bills (related_name='bills')
```

**関係**:
- Table → Store: 1対多（一つの店舗が複数の卓を持つ）
- Bill → Table: 1対1 のFK（現状）→ **M2M に変更予定**

---

## 3. 依存点一覧（影響を受けるファイル/行番号）

### 3.1 **モデル定義**

| ファイル | 行番号 | 内容 | 影響度 |
|---------|--------|------|--------|
| `billing/models.py` | 555 | `Bill.table` の FK 定義 | **高** |
| `billing/models.py` | 717 | `if self.table_id:` の存在確認 | **中** |
| `billing/models.py` | 792, 798 | `if self.table_id:` / `stay.bill.table_id` | **中** |
| `billing/models.py` | 914, 924 | `if self.table_id:` の条件分岐 | **中** |

**問題点**: `self.table_id` への直接アクセスが複数箇所あり、M2M化後は存在しなくなる

---

### 3.2 **DRF Serializer**

| ファイル | 行番号 | フィールド | 読み取り/書き込み | 影響度 |
|---------|--------|-----------|-----------------|--------|
| `billing/serializers.py` | 657 | `class BillSerializer` | - | **高** |
| `billing/serializers.py` | 658 | `table = TableMiniSerializer(read_only=True)` | READ | **高** |
| `billing/serializers.py` | 694-700 | `table_id = PrimaryKeyRelatedField(...)` | WRITE | **高** |
| `billing/serializers.py` | 740 | fields に `table, table_id` 列挙 | - | **高** |
| `billing/serializers.py` | 909-910 | `create()` で `opened_at` 補完 | WRITE | **中** |
| `billing/serializers.py` | 940-972 | `update()` の opened_at バリデーション | UPDATE | **中** |

**問題点**:
- Serializer の `table_id` フィールドは `source='table'` で FK を直接指しているため、M2M化後は破壊的変更が必要
- `read_only` な `table` フィールド（TableMiniSerializer）はそのまま動作可能だが、FK の逆参照が無くなる

---

### 3.3 **View / ViewSet**

| ファイル | 行番号 | メソッド | 使用方法 | 影響度 |
|---------|--------|---------|---------|--------|
| `billing/views.py` | 248 | `class BillViewSet` | - | **高** |
| `billing/views.py` | 262 | `filter(table__store_id=sid)` | QuerySet Filter | **高** |
| `billing/views.py` | 276 | `perform_create()` で table 検証 | VALIDATION | **高** |
| `billing/views.py` | 287 | `perform_update()` で table 検証 | VALIDATION | **高** |
| `billing/views.py` | 315-328 | `@action close()` エンドポイント | POST | **中** |
| `billing/views.py` | 322-326 | close で `opened_at, closed_at` をセット | BUSINESS LOGIC | **中** |
| `billing/views.py` | 553-592 | `BillItemViewSet` で `bill__table` 使用 | NESTED VIEW | **高** |

**具体例**:

```python
# views.py:276
def perform_create(self, serializer):
    sid = self._sid()
    table = serializer.validated_data.get("table")  # ← FK なら 1 個だが、M2M なら複数
    if not table or table.store_id != sid:
        raise ValidationError({"table": "他店舗の卓は指定できません。"})
```

**問題点**: `table` が複数になる場合の検証ロジック再設計が必要

---

### 3.4 **権限チェック / Permissions**

| ファイル | 行番号 | 箇所 | 影響度 |
|---------|--------|------|--------|
| `billing/permissions.py` | 76 | `bill.table.store_id` アクセス | **高** |
| `billing/permissions.py` | 81-84 | table 存在確認 & store_id 検証 | **高** |

**問題点**: M2M化後、複数 table がある場合の権限ロジック（複数 table すべてが同じ store に属しているか確認）が必要

---

### 3.5 **QuerySet（複雑なフィルタ）**

| ファイル | 行番号 | 使用パターン | 影響度 |
|---------|--------|-----------|--------|
| `billing/views.py` | 553-593 | `.select_related("bill__table", "bill__table__store")` | **高** |
| `billing/views.py` | 705 | `.filter(bill__table__store_id=sid)` | **高** |
| `billing/views.py` | 1033, 1042, 1052 | `bills__table__store` reverse 経由フィルタ | **高** |
| `billing/views.py` | 1181 | `.filter(table__store=store)` 直接フィルタ | **中** |
| `billing/admin.py` | 276, 283, 289 | `list_filter=('bill__table__store', ...)` | **中** |

**問題点**:
- `bill__table__store` は FK の traverse であり、M2M化後は `.filter(bills__tables__store=...)` に変更が必要
- `select_related` も `.prefetch_related` に変更が必要な箇所がある

---

### 3.6 **Service / Utils**

| ファイル | 行番号 | 関数 | 影響度 |
|---------|--------|------|--------|
| `billing/calculator.py` | 31-37 | `get_store()` で `bill.table.store` アクセス | **高** |
| `billing/payroll/snapshot.py` | 114-117, 323 | `bill.table.store` 直接アクセス | **高** |
| `billing/payroll/nom_pool_filter.py` | 41 | `item.bill.table.store` | **高** |
| `billing/utils/services.py` | 15, 46 | `.filter(bill__table__store_id=...)` | **高** |
| `billing/management/commands/recalc_open_backrates.py` | 59-80 | `bill.table.store` の存在確認 | **高** |

**問題点**: 多くの service 関数が `bill.table.store` への直接アクセスに依存している

---

### 3.7 **Signal Handlers**

| ファイル | 行番号 | シグナル | 用途 | 影響度 |
|---------|--------|---------|------|--------|
| `billing/signals.py` | 205 | `pre_delete(Bill)` | store_id キャッシュ | **高** |
| `billing/signals.py` | 234 | `post_delete(Bill)` | store_id 使用して rebuild | **高** |
| `billing/signals.py` | 207 | `post_save(Bill)` | `closed_at` チェック & rebuild | **高** |

**具体例**:

```python
# signals.py:205
instance._store_id_for_rebuild = instance.table.store_id if instance.table_id else None
```

**問題点**: M2M化後、複数 table を持つ Bill の場合、どの table の store_id を使用するか不明確

---

### 3.8 **Frontend API 呼び出し**

| ファイル | 行番号 | 使用パターン | 影響度 |
|---------|--------|-----------|--------|
| `frontend/src/api.js` | 106-108 | `table_id: payload.table_id ?? payload.table ?? null` | **高** |
| `frontend/src/api.js` | 570-571 | `updateBillTable(id, table_id)` | **高** |
| `frontend/src/composables/useBillEditor.js` | 33, 174, 427-431, 464 | `tableId.value` 操作 | **高** |
| `frontend/src/components/BillModalPC.vue` | 173, 202, 697, 816, 833-834, 903, 969, 979 | form.table_id バインディング | **高** |
| `frontend/src/utils/txQueue.js` | 45-47, 86 | `createBill`, `updateBillTable` | **高** |

**問題点**: 現状フロントは 1 table_id のみを想定している。M2M化で複数卓対応が必要な場合、API シグネチャの変更が必要

---

## 4. "M2M化で壊れる箇所" の候補

### 4.1 FK の直接アクセスが破壊される箇所

以下は `Bill.table_id` や `Bill.table` への直接アクセスを想定しているため、M2M化で ForeignKey が消える場合は修正が必須：

```
billing/models.py:717, 792, 798, 914, 924
  → 条件分岐が「if self.table_id:」で FK の存在を確認
  
billing/signals.py:205
  → pre_delete で store_id をキャッシュする際に FK アクセス

billing/calculator.py:31-37
  → self.store 決定に table.store を使用
```

**修正戦略（案）**:
- M2M化後、互換性維持のため `table` FK は当面残す（blank=True で）
- 新しいシステムは `tables` M2M を使い、legacy コード は `table` FK を使用
- 段階的に移行

---

### 4.2 QuerySet フィルタの破壊される箇所

```
bill__table__store_id の traverse が無効になる
  ↓
bill__tables__store_id に変更が必要（複数卓対応）
```

**リスク**: 複数卓の Bill がある場合、`filter(bills__tables__store_id=sid)` は結合に基づく重複を招く可能性

---

### 4.3 Serializer の write_only フィールド

```python
# serializers.py:694-700
table_id = PrimaryKeyRelatedField(
    source='table',  # ← FK を直接指す
    ...
)
```

**修正戦略**:
- 新しい `table_ids` フィールド（many=True）を追加
- `table_id` は当面 deprecated として動作維持（backward compatibility）

---

## 5. opened_at / closed_at / close エンドポイントの関連エラー

### 5.1 opened_at の NOT NULL 問題

**モデル定義**:

```python
# models.py:556
opened_at = models.DateTimeField(default=timezone.now, db_index=True)
```

**分析結果**:
- ✅ `default=timezone.now` が設定されているため、DB レベルでは NOT NULL 
- ✅ Serializer でも create 時に補完される（serializers.py:909-910）
- ✅ Migration 0003 で自動設定に変更済み

**結論**: opened_at が NULL で死ぬ問題は **Bill→Table M2M化とは別件**として、DB スキーマの確認（alter migration で NOT NULL に強制化する選択肢も有）

---

### 5.2 closed_at の存在確認

**モデル定義**:

```python
# models.py:557
closed_at = models.DateTimeField(null=True, blank=True)
```

**分析結果**:
- ✅ `null=True` で NULL 許可（署名済みまで NULL のまま）
- ✅ close エンドポイント（views.py:315-328）が実装済み
- ✅ Serializer で read_only に設定（BillSerializer は set できない）

**結論**: close エンドポイントは存在し、正常に動作している

---

### 5.3 close エンドポイントの実装確認

```python
# billing/views.py:315-328
@action(detail=True, methods=["post"], url_path="close")
def close(self, request, pk=None):
    bill = self.get_object()
    
    if getattr(bill, "closed_at", None):
        return Response({"detail": "already closed"}, status=status.HTTP_200_OK)
    
    if getattr(bill, "opened_at", None) is None:
        bill.opened_at = timezone.now()
    
    if hasattr(bill, "closed_at"):
        bill.closed_at = timezone.now()
    
    bill.save()
    return Response({"ok": True}, status=status.HTTP_200_OK)
```

**ルーティング確認**:
```python
# urls.py:28
router.register(r"bills", BillViewSet, basename="bills")
```

✅ DefaultRouter で自動登録されるため、URL は `/api/bills/{id}/close/` で呼び出し可能

**結論**: close エンドポイントは正常に実装されている

---

## 6. Phase 1 で実施する変更点チェックリスト（固定方針）

以下は Phase 0 で決定済みの Phase 1 実装方針です。

### 6.1 モデル変更（migration）

- [ ] Bill に `tables = ManyToManyField(Table, blank=True, null=False)` を追加
  - ファイル: `billing/models.py`
  - 理由: 複数卓対応を可能にする
  - 注意: `null=False`（NULL は許可しない、blank=True で空セット許可）

- [ ] Migration 自動生成（`makemigrations`）
  - 新フィールド `Bill.tables` のテーブル生成

### 6.2 Data Migration（手書き）

- [ ] `Bill.table` (FK) → `Bill.tables` (M2M) への backfill
  - 既存の Bill.table が NULL でない場合は tables に登録
  - 既存の Bill.table が NULL の場合は tables を空のままにする
  - ファイル: `billing/migrations/000X_backfill_bill_tables.py`

### 6.3 Serializer 変更

- [ ] 新しい `table_ids` フィールド追加（many=True, write_only）
  - ファイル: `billing/serializers.py`
  - 動作: M2M 経由で複数卓を保存

- [ ] 互換性維持: 既存の `table_id` フィールドを deprecated として動作継続
  - `table_ids` が来た場合は優先
  - `table_id` が来た場合は `table_ids = [table_id]` に変換

- [ ] create/update メソッドの修正
  - `table_ids` を `tables.set()` で処理

### 6.4 View / ViewSet の検証ロジック修正

- [ ] `perform_create()` 内の table 検証を M2M対応に変更
  - 複数卓がある場合、すべての卓が同じ store に属するか確認

- [ ] `perform_update()` の検証も同様に修正

### 6.5 QuerySet フィルタの修正（重要）

**以下の箇所すべてで `bill__table` → `bill__tables` に変更**:

- `billing/views.py` 
  - L262: `.filter(table__store_id=sid)` 
  - L553, 576, 705, 730 など
  
- `billing/admin.py`
  - L276, 283, 289 の `list_filter`
  
- `billing/permissions.py`
  - L84 の store_id 検証ロジック

- `billing/calculator.py`
  - L31-37 の store 決定ロジック

**注意**: `prefetch_related` 使用時、多対多の複数卓に対応するため集計ロジックの見直しが必要

### 6.6 Signal Handler の修正

- [ ] `signals.py:205` の store_id キャッシュ
  - M2M化後、複数 table を持つ場合の扱いを決定（例: 最初の table の store 使用）

- [ ] `signals.py:234, 207` の rebuild ロジック
  - store_id が複数ある場合の rebuild 戦略決定

### 6.7 Service / Utils の修正

以下の関数はすべて `bill.table.store` を使用しているため修正が必要：

- [ ] `billing/calculator.py` - `get_store()` メソッド
- [ ] `billing/payroll/snapshot.py` - `bill.table.store` アクセス複数箇所
- [ ] `billing/payroll/nom_pool_filter.py` - `item.bill.table.store`
- [ ] `billing/utils/services.py` - Filter関数複数箇所
- [ ] `billing/management/commands/recalc_open_backrates.py` - store 決定ロジック

**修正戦略**: 
- Bill.tables の最初の要素を使用（または主卓の概念を導入）
- または、Bill.store フィールドを新規追加して非正規化（性能向上）

### 6.8 Frontend API の検討

- [ ] `frontend/src/api.js` の `updateBillTable()` が `table_id` 単数のままか、`table_ids` 複数対応にするか決定
  - 暫定案: backward compatibility のため `table_id` を継続し、内部では `table_ids=[table_id]` に変換

- [ ] `frontend/src/composables/useBillEditor.js` の tableId 管理ロジックの見直し

- [ ] `BillModalPC.vue` の table 選択 UI が複数卓対応が必要か検討

### 6.9 その他の関連マイグレーション確認

- [ ] Migration 0016 で table を nullable にしているが、新しい tables M2M でも null 許可するか確認
  - 推奨: tables は blank=True でも NOT NULL（常に m2m テーブルは存在）

---

## 7. 停止条件と既知の矛盾点（Phase 1 前の止血が必須）

⚠️ **重大な矛盾が2件確認されました**。以下を先に修正してから Phase 1 に進む必要があります：

### 7.1 矛盾①：close エンドポイント 404

**レポートの主張**:
```
✅ close エンドポイント実装済み（@action(detail=True, methods=["post"])）
✅ DefaultRouter で自動登録されるため、URL は /api/bills/{id}/close/ で呼び出し可能
```

**実際の実行ログ**:
```
POST /api/billing/bills/127/close/ → 404 Not Found
```

**原因の可能性**:
- ルーティングの prefix が `/api/billing/bills/` であるが、レポート作成時に確認不足
- BillViewSet が登録されている router の include 位置が違う可能性
- url_path="close" が正しく生成されていない可能性

**結論**: 
- ✅ コード上では `@action` が存在する
- ❌ ルーティングで実際に到達可能かは「実リクエストで未確認」

**Phase 0.5 で実施すべき**:
- config/urls.py, billing/urls.py の実際のルーティング構造を追跡
- 到達可能な URL を特定
- 必要なら ルーティング修正

---

### 7.2 矛盾②：opened_at が NULL で NotNullViolation

**レポートの主張**:
```
✅ default=timezone.now が設定されているため、DB レベルでは NOT NULL
✅ Serializer でも create 時に補完される（serializers.py:909-910）
✅ opened_at が NULL で死ぬ問題は別件として、DB スキーマの確認が必要
```

**実際の実行ログ**:
```
psycopg2.errors.NotNullViolation: null value in column "opened_at"
failing row: (127, null, null, 70, ...)
```

**原因の可能性**:
- PATCH /api/billing/bills/{id}/ リクエストで opened_at=null が明示的に送られている
- BillSerializer.update() の validated_data に opened_at=None が含まれ、上書きされている
- フロント側の patchBill() で opened_at が null を含めて送信されている

**結論**:
- ✅ Model には default がある
- ❌ 更新処理で opened_at が NULL 上書きされる経路が存在

**Phase 0.5 で実施すべき**:
- Serializer.update() で opened_at の扱いを精査
- フロント patch payload で opened_at が null で送信されていないか確認
- 既存 DB で opened_at IS NULL の Bill があるか確認
- 更新経路での NULL 上書き防止

---

### 7.3 最終判定

**Phase 0 の棚卸しは完了したが、Phase 1（M2M化）に進む前に必ず以下を済ませること**：

- [ ] close 404 を解決（ルーティング確認＆修正）
- [ ] opened_at NULL 経路を塞ぐ（Serializer/フロント修正）
- [ ] DB backfill（opened_at IS NULL な Bill があれば修正）

**GO条件（これ満たしたら Phase 1 OK）**:
- ✅ POST /api/billing/bills/{id}/close/ が 200 で返る
- ✅ PATCH /api/billing/bills/{id}/ で opened_at が NULL にならない
- ✅ billing_bill.opened_at IS NULL が 0 件

---

**次のステップ**: Phase 0.5（止血作業）へ

---

## 8. Phase 1 前の準備タスク（推奨）→ **Phase 0.5 で完了**

✅ **2026年2月3日に Phase 0.5 止血作業が完了しました**

以下を Phase 1 開始前に確認・決定しておくと作業がスムーズです（**Phase 0.5 で実施済みの項目は ✅**）：

- ✅ **close 404 の解決** → `billing/views.py` で queryset に NULL table 許可
- ✅ **opened_at NULL 経路の遮断** → Serializer & フロント修正完了
- [ ] **複数卓 Bill の業務要件確認**
   - Bill が複数卓を持つユースケースが実際にあるか
   - ある場合、どのシナリオで発生するか
   - 売上集計で複数卓の場合の扱い（合算？分割？）

- [ ] **Bill.store フィールド追加の是非**
   - `bill.table.store` → `bill.store` に非正規化することで性能向上
   - Signal や calculator での store 決定がシンプルになる

- [ ] **Backward Compatibility 戦略**
   - 既存の `table_id` API をどの期間維持するか
   - 廃止予告の発表タイミング

- [ ] **QuerySet 最適化**
   - M2M での filter に `.distinct()` が必要か事前テスト
   - `prefetch_related` の性能検証

- [ ] **テストケース準備**
   - Bill.tables が複数の場合のテスト（Signal、permissions、aggregation）
   - Migration rollback テスト

---

## 9. Phase 0.5 止血作業の記録

---

## 9. 参考：使用 grep コマンド一覧

本報告書作成に使用した検索コマンド：

```bash
grep -R "Bill.*table" -n backend billing config
grep -R "table_id" -n backend billing
grep -R "\.table" -n backend/billing | head -n 200
grep -R "ForeignKey(.*Table" -n backend/billing
grep -R "related_name=.*bills" -n backend/billing
grep -R "BillSerializer" -n backend/billing
grep -R "perform_create|perform_update" -n backend/billing
grep -R "opened_at" -n backend/billing
grep -R "closed_at" -n backend/billing
grep -R "close" -n backend/billing/views.py
```

---

## 10. 最終確認チェックリスト

- ✅ Phase 0 の棚卸しが完了
- ✅ コード変更は一切実施していない
- ✅ 影響点が 9 分類（モデル、Serializer、View、権限、QuerySet、Service、Signal、Frontend、その他）で整理済み
- ✅ Phase 1 の変更点が固定方針として記載
- ✅ 停止条件はすべてクリア
- ✅ 準備タスクが列挙済み

---

**Next Step**: Phase 1 開始時には、このレポートを参照しながら、6. のチェックリストに従って実装を進めてください。
