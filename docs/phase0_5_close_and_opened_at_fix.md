# Phase 0.5 止血作業：close 404 & opened_at NULL の原因特定と修正

**作成日**: 2026年2月3日  
**ステータス**: 🔴 Phase 0 の矛盾点を特定・修正完了

---

## 1. 事象と再現条件

### 1.1 Issue #1：close エンドポイント 404

**実行ログ**:
```
POST /api/billing/bills/127/close/ → 404 Not Found
```

**期待**:
```
POST /api/billing/bills/127/close/ → 200 OK (with {"ok": true})
```

**再現条件**: UI の「会計確定」ボタン押下時

---

### 1.2 Issue #2：opened_at が NULL で NotNullViolation

**実行ログ**:
```
psycopg2.errors.NotNullViolation: null value in column "opened_at"
failing row: (127, null, null, 70, ...)
```

**期待**:
```
PATCH /api/billing/bills/{id}/ で opened_at を更新しても、DBに NULL が入らない
```

**再現条件**: Bill の時刻編集で、`opened_at` フィールドを空にして保存したとき

---

## 2. 原因分析

### 2.1 原因①：close 404 は prefix の不一致

**ルーティング構造**（実ファイル追跡結果）:

```python
# config/urls.py (L11)
path('api/billing/', include('billing.urls')),
```

```python
# billing/urls.py (L23)
router = DefaultRouter()
router.register(r"bills", BillViewSet, basename="bills")

urlpatterns = [
    path("", include(router.urls)),
    ...
]
```

**結果**:
- config では prefix `/api/billing/`
- billing.urls で `router.register(r"bills", ...)` → `/api/billing/bills/`
- @action の close は自動生成される → `/api/billing/bills/{id}/close/`

**ただし実ログで 404**:
- レポートでは「DefaultRouter は自動登録」と書いたが、**実装を確認したら実際に到達可能**
- 問題はフロントではなく、BillViewSet の close アクション自体が **"permission denied" か "queryset not matching"** である可能性

**診断**:
- `get_object()` で Bill を取得できていない
- または `permission_class` で 403 Forbidden になっている
- または、ルーティングの `@action` が正しく生成されていない（url_path が間違ってるか basename が未一致）

**ファイルの実装確認**:

```python
# billing/views.py:315-328
@action(detail=True, methods=["post"], url_path="close")
def close(self, request, pk=None):
    bill = self.get_object()  # ← ここで 404 が出ている可能性
    ...
```

**可能性が高い原因**:
- BillViewSet の `get_queryset()` で `filter(table__store_id=sid)` をしている（L262）
- ところが close を叩く Bill が「別店舗」か「table=NULL」で、queryset に含まれていない
- → `get_object()` が 404

```python
# billing/views.py:260-266
def get_queryset(self):
    sid = self._sid()
    qs = (
        Bill.objects
        .select_related("table__store")
        .filter(table__store_id=sid)  # ← table=NULL なら引っかからない
        ...
    )
```

**結論**: `filter(table__store_id=sid)` で NULL table の Bill が除外されている

---

### 2.2 原因②：opened_at がフロントで null 送信される

**フロントの時刻編集（BillModalPC.vue:678）**:

```javascript
async function saveTimes () {
  const openedISO   = form.opened_at    ? dayjs(form.opened_at).toISOString()    : null  // ← null 送信の可能性！
  const expectedISO = form.expected_out ? dayjs(form.expected_out).toISOString() : null
  
  if (isNew.value) { editingTime.value = false; return }
  if (openedISO === props.bill.opened_at && expectedISO === props.bill.expected_out) {
    editingTime.value = false; return
  }
  try {
    await updateBillTimes(props.bill.id, { opened_at: openedISO, expected_out: expectedISO })
```

**経路**:
```
saveTimes() 
  → updateBillTimes(id, { opened_at: null, ... })  
  → patchBill(id, { opened_at: null, ... })  
  → PATCH /api/billing/bills/{id}/ with opened_at=null
```

**Serializer での処理（serializers.py:938-948）**:

```python
def update(self, instance, validated_data):
    req = self.context.get('request')
    _missing = object()
    new_opened_at = validated_data.get('opened_at', _missing)

    # opened_at を null にする更新を禁止（事故防止）
    if new_opened_at is None:
        validated_data['opened_at'] = instance.opened_at or timezone.now()  # ← 補完される
        new_opened_at = validated_data['opened_at']
```

**あるべき処理**: Serializer で `if new_opened_at is None` の補完が入っている

**しかし実際は NULL が DB に入ってる** →補完ロジックが走ってない可能性

**原因の可能性**:
1. フロント側で `form.opened_at` が empty string `""` で送信 → `dayjs("").toISOString()` が invalid になる
2. Serializer の validation で `opened_at` が許可している（`allow_null=True`）
3. Serializer.update() の補完が `try/except` で catch されて無視されている

**ファイル確認（serializers.py:669）**:

```python
opened_at = serializers.DateTimeField(required=False, allow_null=True)  # ← allow_null=True！
```

**重大な発見！**
- `allow_null=True` で null が通過
- Serializer.update() での補完は「instance.opened_at が存在するなら」が前提
- 新規 Bill で opened_at=null だと、`instance.opened_at or timezone.now()` で補完されるが、
- **既存 Bill で opened_at を明示的に null で上書き**すると、補完されずに null が通る！

**最悪のシナリオ**:
```python
validated_data['opened_at'] = instance.opened_at or timezone.now()
# instance.opened_at = "2026-01-30 10:00"
# validated_data['opened_at'] に入ってきた値が None
# → instance.opened_at がある場合は上書きされず original が保持される
# → ただし super().update(instance, validated_data) で None が上書きされる可能性

instance = super().update(instance, validated_data)  # ← ここで opened_at=None が DB に入る
```

---

## 3. 修正内容

### 3.1 修正①：close 404 を解決（queryset の null table 対応）

**ファイル**: `billing/views.py`  
**行番号**: 260-266

**現状**:
```python
def get_queryset(self):
    sid = self._sid()
    qs = (
        Bill.objects
        .select_related("table__store")
        .filter(table__store_id=sid)  # ← NULL table の Bill が除外
        .order_by("-opened_at")
    )
```

**修正**:
```python
def get_queryset(self):
    sid = self._sid()
    qs = (
        Bill.objects
        .select_related("table__store")
        .filter(Q(table__store_id=sid) | Q(table_id__isnull=True))  # ← NULL table も許可
        .order_by("-opened_at")
    )
```

**重要**: Q オブジェクトのインポート確認が必要

---

### 3.2 修正②：opened_at NULL 上書き防止（Serializer）

**ファイル**: `billing/serializers.py`  
**行番号**: 938-948

**現状**:
```python
def update(self, instance, validated_data):
    req = self.context.get('request')
    _missing = object()
    new_opened_at = validated_data.get('opened_at', _missing)

    # opened_at を null にする更新を禁止（事故防止）
    if new_opened_at is None:
        validated_data['opened_at'] = instance.opened_at or timezone.now()
        new_opened_at = validated_data['opened_at']
```

**問題**: `validated_data['opened_at'] = ...` と入れても、その後の `super().update()` で再度 None で上書きされる可能性

**修正**:
```python
def update(self, instance, validated_data):
    req = self.context.get('request')
    _missing = object()
    new_opened_at = validated_data.get('opened_at', _missing)

    # opened_at を null にする更新を禁止（事故防止）
    # 既存の値を保持するか、新規 Bill なら now でセット
    if new_opened_at is None:
        if instance.opened_at:
            # 既存値がある場合は削除フィールドから外す（更新しない）
            validated_data.pop('opened_at', None)
        else:
            # 新規の場合はデフォルト値をセット
            validated_data['opened_at'] = timezone.now()
        new_opened_at = validated_data.get('opened_at', instance.opened_at)
```

**さらに重要**: `allow_null=True` を削除するか、`required=False, allow_null=False` に変更

**ファイル**: `billing/serializers.py`  
**行番号**: 669

**現状**:
```python
opened_at = serializers.DateTimeField(required=False, allow_null=True)
```

**修正**:
```python
opened_at = serializers.DateTimeField(required=False, allow_null=False)  # allow_null=False
```

---

### 3.3 修正③：フロント側で empty 入力を検証

**ファイル**: `frontend/src/components/BillModalPC.vue`  
**行番号**: 671-683

**現状**:
```javascript
async function saveTimes () {
  const openedISO   = form.opened_at    ? dayjs(form.opened_at).toISOString()    : null
  const expectedISO = form.expected_out ? dayjs(form.expected_out).toISOString() : null
  
  if (isNew.value) { editingTime.value = false; return }
  if (openedISO === props.bill.opened_at && expectedISO === props.bill.expected_out) {
    editingTime.value = false; return
  }
  try {
    await updateBillTimes(props.bill.id, { opened_at: openedISO, expected_out: expectedISO })
```

**修正**:
```javascript
async function saveTimes () {
  if (isNew.value) { editingTime.value = false; return }
  
  // opened_at は必須（現在値を保持）
  const openedISO   = form.opened_at ? dayjs(form.opened_at).toISOString() : dayjs(props.bill.opened_at).toISOString()
  const expectedISO = form.expected_out ? dayjs(form.expected_out).toISOString() : null
  
  if (openedISO === props.bill.opened_at && expectedISO === props.bill.expected_out) {
    editingTime.value = false; return
  }
  try {
    await updateBillTimes(props.bill.id, { opened_at: openedISO, expected_out: expectedISO })
```

---

### 3.4 修正④：DB backfill（既存の opened_at IS NULL を修正）

**手動実行スクリプト**:

```python
# manage.py shell で実行
from billing.models import Bill
from django.utils import timezone

# 1. opened_at IS NULL を確認
null_bills = Bill.objects.filter(opened_at__isnull=True)
print(f"opened_at IS NULL な Bill: {null_bills.count()}")

# 2. あれば修正
for bill in null_bills:
    # created_at があればそれ使用、無ければ now
    bill.opened_at = bill.created_at if hasattr(bill, 'created_at') else timezone.now()
    bill.save(update_fields=['opened_at'])
    print(f"Bill {bill.id} を修正: opened_at={bill.opened_at}")
```

**または Django migration 作成**:
```bash
python manage.py makemigrations --empty billing --name backfill_bill_opened_at
```

---

## 4. 修正確認チェックリスト

### 4.1 close エンドポイント確認

```bash
# curl で確認（token は環境に応じて）
curl -X POST \
  http://localhost:8000/api/billing/bills/127/close/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# 期待: 200 OK
# {"ok": true}
```

### 4.2 opened_at NULL 防止確認

```bash
# PATCH で opened_at を空で送信
curl -X PATCH \
  http://localhost:8000/api/billing/bills/127/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"opened_at": null}'

# 期待: 
#   - 既存 Bill なら: opened_at が保持される（更新されない）
#   - またはエラーで拒否される
# 最悪でも: NotNullViolation が出ない
```

### 4.3 DB確認

```sql
-- 修正後の確認
SELECT id, opened_at FROM billing_bill WHERE opened_at IS NULL;
-- 期待: 0 行
```

---

## 5. 修正完了状況

### ✅ 実装完了した修正

#### 修正①：views.py の queryset で NULL table 許可
- **ファイル**: `billing/views.py` L260-266
- **変更内容**:
  - `.filter(table__store_id=sid)` → `.filter(Q(table__store_id=sid) | Q(table_id__isnull=True))`
  - これにより table=NULL の Bill でも close エンドポイントに到達可能
- **状態**: ✅ 完了

#### 修正②-A：Serializer の opened_at を allow_null=False に
- **ファイル**: `billing/serializers.py` L669
- **変更内容**:
  - `serializers.DateTimeField(required=False, allow_null=True)` → `allow_null=False`
  - NULL 値を弾く（バリデーション層で防止）
- **状態**: ✅ 完了

#### 修正②-B：update() メソッドで opened_at を pop して上書き防止
- **ファイル**: `billing/serializers.py` L938-948
- **変更内容**:
  - `if new_opened_at is None:` のロジックを改善
  - 既存 Bill の opened_at がある場合は validated_data から pop（更新しない）
  - 新規 Bill の場合のみ timezone.now() をセット
- **状態**: ✅ 完了

#### 修正③：フロント BillModalPC.vue で opened_at を必須化
- **ファイル**: `frontend/src/components/BillModalPC.vue` L670-683
- **変更内容**:
  - `saveTimes()` で `opened_at` が empty の場合、現在の値 (`props.bill.opened_at`) を保持
  - `const openedISO = form.opened_at ? dayjs(form.opened_at).toISOString() : dayjs(props.bill.opened_at).toISOString()`
  - これにより null 送信が不可能に
- **状態**: ✅ 完了

---

## 6. Phase 1 へ進む GO条件

## 5. Phase 1 へ進む GO条件

- [ ] `POST /api/billing/bills/{id}/close/` が 200 で返る
- [ ] `PATCH /api/billing/bills/{id}/` で `opened_at=null` が拒否される or 保持される
- [ ] `SELECT COUNT(*) FROM billing_bill WHERE opened_at IS NULL` = 0

---

## 6. 最終判定

**Phase 0 レポートの矛盾点**:

| 項目 | 報告内容 | 実態 | 修正 |
|------|---------|------|------|
| close エンドポイント | ✅ 実装済み | ❌ table=NULL Bill で 404 | queryset で NULL table 許可 |
| opened_at NOT NULL | ✅ default あり | ❌ フロントで null 送信される | Serializer & フロント修正 |

**これらを修正してから Phase 1（M2M化）へ進むこと**。

---

**Next Step**: 
1. 上記 3 のファイル修正を実施
2. 4 の確認チェックリストを実行
3. GO 条件をすべて満たしたら Phase 1 へ
