<!-- views/BillList.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import dayjs              from 'dayjs'
import { useBills }       from '@/stores/useBills'
import BillModal          from '@/components/BillModal.vue'

const bills     = useBills()
const showModal = ref(false)
onMounted(() => bills.loadAll())

function open(id){ bills.open(id).then(() => (showModal.value = true)) }

/* ======== 一覧表示ヘルパ ========== */

/** ① セット(コース)名を返す（アイテム名で判定） */
function setName(b){
  const it = (b.items || []).find(i => /^セット\d+分/.test(i.name))
  return it ? it.name : '‑'
}

/* === ① テーブル全体の OUT 時間 ============================= */
function calcOut(b){
  if (!b.opened_at) return '‑'

  let minutes = 0
  ;(b.items || []).forEach(it => {
    /* ─ セット: 「セット60分」「セット90分VIP」など ─ */
    const mSet = it.name.match(/^セット(\d+)分/)
    if (mSet){
      minutes += Number(mSet[1])      // ← qty は掛けない
      return
    }

    /* ─ 延長: 「延長30分」「セット延長」など ─ */
    if (/延長/.test(it.name)){
      const mExt = it.name.match(/(\d+)分/)
      minutes += mExt ? Number(mExt[1]) : 30   // 数字が無ければ 30 固定
    }
  })

  return minutes
         ? dayjs(b.opened_at).add(minutes,'minute').format('HH:mm')
         : '‑'
}

/* === ② 延長の “回数” と “分数” を知りたい場合 =============== */
function extStats(b){
  let count = 0, totalMin = 0
  ;(b.items || []).forEach(it => {
    if (/延長/.test(it.name)){
      count++
      const m = it.name.match(/(\d+)分/)
      totalMin += m ? Number(m[1]) : 30
    }
  })
  return { count, totalMin }   // 例: {count:2, totalMin:60}
}


function liveCasts(b){
  return (b.stays||[])
    .filter(s=>!s.left_at)        // ← serializer で left_at に合わせました
    .map(s=>{
      const c = s.cast || {}
      const cid = c.id
      let tag='', color=''
      if(cid === (b.nominated_casts?.[0]||null)){ tag='本指名' ; color='danger'}
      else if((b.inhouse_casts||[]).includes(cid)){ tag='場内' ; color='success'}

      return {
        id   : cid,
        name : c.stage_name || 'N/A',
        avatar: c.avatar_url || '/img/user-default.png',
        tag,
        color,
      }
    })
}
/* avatar URL を拾う簡易関数（無ければデフォルト）*/
function castAvatar(id){
  // ① items から探す
  const it = (bills.current?.items||[]).find(i => i.served_by_cast===id && i.cast_avatar_url)
  if(it) return it.cast_avatar_url
  // ② プリロード済み辞書があればそちら
  return '/img/user-default.png'
}


</script>



<template>
  <table class="table table-bordered table-hover align-middle table-striped">
    <thead>
      <tr>
        <th>ID</th><th>卓</th><th>in</th>
        <th>out</th><th>キャスト</th><th class="text-end">小計</th>
        <th class="text-end">合計</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="b in bills.list" :key="b.id"
          @click="open(b.id)" style="cursor:pointer">
        <td>{{ b.id }}</td>
        <td>{{ b.table.number }}</td>
        <td>
			<span class="badge bg-dark text-light">{{ setName(b) }}</span>
			<span class="fs-3 fw-bold d-block">{{ dayjs(b.opened_at).format('HH:mm') }}</span>
		</td>  <!-- タイムとセット -->
        <td>
			<!-- 延長 2 回 / 計 60 分 のように表示したい場合 -->
			<template v-if="extStats(b).count">
				<span class="badge bg-dark text-light">延長 {{ extStats(b).count }} 回</span>
			</template>
			<span class="fs-3 fw-bold d-block">{{ calcOut(b) }}</span>
		</td>                           <!-- out -->
			
		<td>
		<div class="d-flex flex-wrap gap-2">
			<div v-for="p in liveCasts(b)" :key="p.id"
				class="d-flex align-items-center btn btn-light p-2">
				<img :src="p.avatar" class="rounded-circle me-1" width="40" height="40">
				
				<div class="wrap d-flex flex-column align-items-start">
					<span v-if="p.tag" class="badge text-light"
							:class="`bg-${p.color}`">{{ p.tag }}</span>
					<span class="fw-bold">{{ p.name }}</span>
				</div>
			</div>
		</div>
		</td>
                      <!-- キャスト -->
        <td class="text-end">{{ b.subtotal.toLocaleString() }}</td>
        <td class="text-end">{{ (b.closed_at ? b.total : b.grand_total).toLocaleString() }}</td>
      </tr>
    </tbody>
  </table>

  <BillModal v-model="showModal" :bill="bills.current" />
</template>

