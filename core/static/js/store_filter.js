// static/js/store_filter.js
console.log('store_filter.js loaded');  // ← まずこれで読まれているか確認

function redirectByStore(val) {
  const url = new URL(window.location.href);
  val ? url.searchParams.set('store', val)
     : url.searchParams.delete('store');
  window.location.href = url.toString();
}

document.addEventListener('DOMContentLoaded', () => {
  // ❶ 初期化直後に「change」で拾う (非 Select2 環境でも効く)
  const storeSelect = document.getElementById('id_store');
  if (storeSelect) {
    storeSelect.addEventListener('change', e => redirectByStore(e.target.value));
  }

  // ❷ Select2 が後から走っても届くように「document」でキャッチ
  document.addEventListener('select2:select', e => {
    if (e.target && e.target.id === 'id_store') {
      console.log('select2 fired', e.target.value);
      redirectByStore(e.target.value);
    }
  });
});
