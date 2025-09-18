<!-- src/views/settings/GlobalSetting.vue -->
<script setup>
import { computed } from 'vue'
import { useRoute, RouterLink } from 'vue-router'

const route  = useRoute()
const isRoot = computed(() => route.name === 'settings') // 親そのもの = ハブ表示

const cards = [
  { to: { name: 'settings-store' },  title: 'ストア',   desc: '営業時間・サービス料・税率・指名プール率' },
  { to: { name: 'settings-menu' },   title: 'メニュー', desc: 'メニュー（ItemMaster）の追加・編集・在庫フラグ' },
  { to: { name: 'settings-table' },  title: 'テーブル', desc: 'テーブル番号の追加・並び順' },
  { to: { name: 'settings-staff-list' }, title: 'スタッフ', desc: 'スタッフ一覧・詳細編集' },
  { to: { name: 'settings-cast-list' },  title: 'キャスト', desc: 'キャスト一覧・詳細編集' },
  { to: { name: 'settings-news-list' },  title: 'お知らせ', desc: '店舗からのお知らせ（公開／予約公開／画像1枚）' },
]
</script>

<template>
  <div class="container-fluid py-4">

    <!-- サブナビ（常に表示。現在地で .active が付く） -->
    <ul class="nav nav-pills gap-2 mb-3 flex-wrap">
      <li class="nav-item" v-for="c in cards" :key="c.title">
        <RouterLink class="nav-link" :to="c.to" active-class="active">
          {{ c.title }}
        </RouterLink>
      </li>
    </ul>

    <!-- ハブ（/bills/settings に来たときだけ見せる） -->
    <div v-if="isRoot" class="row g-3 mb-4">
      <div class="col-12 col-sm-6 col-lg-4" v-for="c in cards" :key="c.title">
        <RouterLink class="card h-100 text-decoration-none" :to="c.to">
          <div class="card-body">
            <div class="fw-bold mb-1">{{ c.title }}</div>
            <div class="small text-muted">{{ c.desc }}</div>
          </div>
        </RouterLink>
      </div>
    </div>

    <!-- 子ページをここに描画（store/menu/table/staff/casts など） -->
    <router-view v-else />
  </div>
</template>

<style scoped>

input,select{
  background-color: white;
}

.nav-link { cursor: pointer; }

</style>