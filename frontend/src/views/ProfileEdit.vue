<!-- src/views/ProfileEdit.vue -->
<script setup>
import { reactive, ref, onMounted, onBeforeUnmount } from 'vue'
import { useUser } from '@/stores/useUser'
import { api } from '@/api'
import Avatar from '@/components/Avatar.vue'
import { useProfile } from '@/composables/useProfile'
import CastSidebar from '@/components/sidebar/CastSidebar.vue'
import { openOffcanvas } from '@/utils/bsOffcanvas'

const meStore = useUser()
const { avatarURL } = useProfile()

const form = reactive({
  first_name: '', last_name: '', username: '',
  email: '', phone: '', department: '',
})
const saving = ref(false)
const msg = ref('')

/* ── アバター ─────────────────────────── */
const previewUrl = ref('')       // ローカルプレビューURL
const avatarFile = ref(null)     // 選択したFile
const canEditAvatar = ref(true)  // ★ 全員OKに変更

function onPick(e){
  const f = e.target.files?.[0]
  if (!f) return
  avatarFile.value = f
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = URL.createObjectURL(f)
}

onBeforeUnmount(() => { if (previewUrl.value) URL.revokeObjectURL(previewUrl.value) })

/* ── 初期ロード ──────────────────────── */
async function load() {
  let me = meStore.me
  if (!me) me = (await api.get('me/')).data

  form.first_name = me.first_name ?? ''
  form.last_name  = me.last_name  ?? ''
  form.username   = me.username   ?? ''
  form.email      = me.email      ?? ''
  form.phone      = me.phone      ?? ''
  form.department = me.department ?? ''
}

/* ── 保存（基本情報 + 画像） ─────────── */
async function save() {
  saving.value = true
  msg.value = ''
  try {
    const me = meStore.me || (await api.get('me/')).data

    // 基本情報（必要項目だけ）
    const payload = {
      first_name: form.first_name,
      last_name : form.last_name,
      email     : form.email,
    }
    if ((form.username || '') !== (me.username || '')) {
      payload.username = form.username
    }
    await api.patch('dj-rest-auth/user/', payload)

    // 画像は常にUserに送る（multipart）
    if (avatarFile.value) {
      const fd = new FormData()
      fd.append('avatar', avatarFile.value)
      await api.patch('dj-rest-auth/user/', fd)
    }

    await meStore.fetchMe?.()
    msg.value = '保存しました'
  } catch (e) {
    const d = e?.response?.data
    msg.value = d ? JSON.stringify(d) : (e?.message || '保存に失敗しました')
  } finally {
    saving.value = false
  }
}

function openSidebar(){
  openOffcanvas('#castSidebar')
}

onMounted(load)
</script>

<template>
  <div class="py-3">
    <div class="upper mb-5 d-flex align-items-center justify-content-between">
      <h2 class="fs-2 fw-bold">プロフィール編集</h2>
      <button @click="openSidebar"><IconMenuDeep class="fs-5"/></button><!-- サイドバー開く -->
    </div>
    <!-- アバター -->
    <div class="mb-4 d-flex align-items-center gap-3">
      <Avatar :url="previewUrl || avatarURL" :size="60" class="rounded-circle" />
      <div class="d-flex flex-column gap-2">
        <label class="btn btn-sm btn-outline-secondary mb-0">
          画像を選択
          <input type="file" accept="image/*" class="d-none" @change="onPick" />
        </label>
      </div>
    </div>

    <!-- 基本情報 -->
    <div class="row g-3">
      <div class="col-12">
        <label class="form-label small text-muted">姓</label>
        <input v-model="form.last_name" class="form-control" />
      </div>
      <div class="col-12">
        <label class="form-label small text-muted">名</label>
        <input v-model="form.first_name" class="form-control" />
      </div>

      <div class="col-12">
        <label class="form-label small text-muted">ログインID（ユーザーネーム）</label>
        <input v-model="form.username" class="form-control" />
      </div>

      <div class="col-12">
        <label class="form-label small text-muted">メールアドレス</label>
        <input v-model="form.email" type="email" class="form-control" />
      </div>

      <div class="col-12">
        <label class="form-label small text-muted">電話番号</label>
        <input v-model="form.phone" class="form-control" />
      </div>
    </div>

    <div class="mt-5 w-100">
      <button class="btn btn-sm btn-primary w-100" :disabled="saving" @click="save">
        {{ saving ? '保存中…' : '保存' }}
      </button>
      <span class="text-muted">{{ msg }}</span>
    </div>
  </div>

    <!-- オフキャンバス（サイドバー） -->
    <CastSidebar />

</template>

<style scoped lang="scss">
input { background: white; }
form-label { font-size: 0.8rem; }
</style>
