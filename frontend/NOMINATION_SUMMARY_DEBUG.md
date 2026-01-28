# NominationSummaryPanel が空表示になる原因と対策

## 🔍 調査結果

### コードレベルの実装状況

✅ **TableCustomersPanel（顧客管理）**
- **INボタン**: 正しく実装されている
  - `useBillCustomerTimeline.markArrived()` が `PATCH /billing/bill-customers/{id}/` で `arrived_at` を設定
- **本指名保存ボタン**: 正しく実装されている
  - `useNominations.setNominations()` が `POST /billing/bills/{id}/nominations/` で本指名を作成

✅ **NominationSummaryPanel（本指名サマリー）**
- 正しく実装されている（読み取り専用）
  - `GET /billing/bills/{id}/nomination-summaries/` でデータ取得

**結論: フロントエンドのコードに問題なし**

---

## 🐛 実際の問題

### 現在のAPI応答（空の理由）

```json
// GET /api/billing/bills/104/customers/
{
  "id": 108,
  "bill": 104,
  "customer": 105,
  "arrived_at": null,    // ← 問題1: INされていない
  "left_at": null
}

// GET /api/billing/bills/104/nominations/
{
  "results": []          // ← 問題2: 本指名が作成されていない
}

// GET /api/billing/bills/104/nomination-summaries/
{
  "results": []          // ← 当然空（上記2つが揃ってないため）
}
```

### サマリーが表示される条件

NominationSummaryPanel は以下の**両方**が揃わないと1件も表示されません：

1. ✅ `BillCustomer.arrived_at` が入っていること（IN状態）
2. ✅ `BillCustomerNomination` が存在すること（本指名キャストの紐づけ）

---

## ✅ 検証方法（最短）

以下の2つのAPIを手動で叩いて、サマリーが表示されることを確認：

### A) arrived_at を設定（INする）

```bash
curl -X PATCH "http://localhost:8000/api/billing/bill-customers/108/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Token <your-token>" \
  -H "X-Store-Id: 13" \
  -d '{"arrived_at":"2026-01-27T18:05:35+09:00"}'
```

### B) 本指名を作成

```bash
curl -X POST "http://localhost:8000/api/billing/bills/104/nominations/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Token <your-token>" \
  -H "X-Store-Id: 13" \
  -d '{"customer_id":105,"cast_ids":[68]}'
```

### C) サマリーを確認

```bash
curl -s "http://localhost:8000/api/billing/bills/104/nomination-summaries/" \
  -H "Authorization: Token <your-token>" \
  -H "X-Store-Id: 13"
```

→ この時点で `results` にデータが入っていればOK

---

## 🔧 UI操作で確認する手順

1. **伝票を開く**
   - 伝票 #104 を開く
   - PayPanel（会計タブ）に切り替える

2. **顧客・本指名管理カードを開く**
   - 「顧客・本指名管理」カードのヘッダーをクリック
   - アコーディオンが開いて TableCustomersPanel が表示される

3. **INボタンを押す**
   - 顧客（例：Guest-105）の「IN」ボタンをクリック
   - **Network タブで確認**: `PATCH /api/billing/bill-customers/108/` が飛んでいるか
   - **Response を確認**: `arrived_at` に日時が入っているか

4. **本指名キャストを選択**
   - キャストのチェックボックス（例：cast_id=68）を選択
   - **「保存」ボタン**をクリック
   - **Network タブで確認**: `POST /api/billing/bills/104/nominations/` が飛んでいるか
   - **Payload を確認**: `{"customer_id":105,"cast_ids":[68]}` が正しいか

5. **サマリーを確認**
   - NominationSummaryPanel に本指名期間の卓小計が表示される
   - **Network タブで確認**: `GET /api/billing/bills/104/nomination-summaries/` の response に `results` が入っているか

---

## 🚨 よくある問題

### 1. INボタンを押してもAPIが飛ばない
**原因**: イベントハンドラーが動作していない
**確認**:
- Console に JavaScript エラーが出ていないか
- Vue Devtools で `timelineComposable.markArrived` が定義されているか

### 2. 保存ボタンを押してもAPIが飛ばない
**原因**: `selectedCastsByCustomer` が正しく更新されていない
**確認**:
- Console に `handleNominationChange` のログを追加して、`castIds` が正しく渡されているか確認

```javascript
const handleNominationChange = async (customerId) => {
  const castIds = selectedCastsByCustomer.value[customerId] || []
  console.log('[handleNominationChange]', { customerId, castIds }) // ← 追加
  
  loadingNominations.value = true
  try {
    await nominationsComposable.setNominations(props.billId, customerId, castIds)
  } catch (e) {
    alert('本指名設定に失敗しました: ' + e.message)
  } finally {
    loadingNominations.value = false
  }
}
```

### 3. display_name が undefined と表示される
**原因**: `BillCustomer` API が `display_name` を返していない
**対策（フロント側）**:

```vue
<!-- TableCustomersPanel.vue -->
<strong>{{ bc.display_name || `Guest-${bc.customer_id}` }}</strong>
```

**対策（バック側）**:
- `BillCustomer` のシリアライザーに `display_name` フィールドを追加
- または `customer` オブジェクト全体を返す

---

## 💡 運用改善提案

現場で必ず起きる問題なので、以下の自動化をおすすめします：

### 1. BillCustomer 作成時に arrived_at を自動設定

```python
# backend: billing/models.py または serializers.py
class BillCustomer(models.Model):
    # ...
    
    def save(self, *args, **kwargs):
        # 新規作成時に arrived_at を自動で now() に設定
        if not self.pk and not self.arrived_at:
            self.arrived_at = timezone.now()
        super().save(*args, **kwargs)
```

### 2. 本指名料アイテム追加時に nomination を自動作成

```python
# backend: billing/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import BillItem, BillCustomerNomination

@receiver(post_save, sender=BillItem)
def auto_create_nomination(sender, instance, created, **kwargs):
    """本指名料アイテムが追加されたら、自動で nomination を作成"""
    if created and instance.item_master.is_nomination:
        # instance.customer と instance.served_by_cast から自動作成
        if instance.customer and instance.served_by_cast:
            BillCustomerNomination.objects.get_or_create(
                bill_customer__bill=instance.bill,
                bill_customer__customer=instance.customer,
                cast=instance.served_by_cast
            )
```

---

## 📝 まとめ

1. **コードは正しい**: フロントエンドの実装に問題なし
2. **データが未入力**: `arrived_at` と `nominations` が作成されていないだけ
3. **確認方法**: Network タブで PATCH/POST が飛んでいるか確認
4. **改善案**: 自動化で運用ミスを防止

---

## 🔗 関連ファイル

- `/frontend/src/components/billing/TableCustomersPanel.vue` - 顧客管理UI
- `/frontend/src/components/billing/NominationSummaryPanel.vue` - サマリー表示UI
- `/frontend/src/composables/useBillCustomerTimeline.js` - IN/OUT操作
- `/frontend/src/composables/useNominations.js` - 本指名操作
- `/frontend/src/components/panel/PayPanel.vue` - 統合パネル
