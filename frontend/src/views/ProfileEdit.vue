<!-- src/views/ProfileEdit.vue（丸ごと置換） -->
<script setup>
import { reactive, ref, onMounted, onBeforeUnmount } from 'vue'
import { useUser } from '@/stores/useUser'
import { api } from '@/api'
import Avatar from '@/components/Avatar.vue'
import { useProfile } from '@/composables/useProfile'

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
const canEditAvatar = ref(false) // cast_idがあるときだけ編集

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

  canEditAvatar.value = !!me.cast_id   // Castがある人だけアバター編集
}

/* ── 保存（基本情報 + 画像） ─────────── */
async function save() {
  saving.value = true
  msg.value = ''
  try {
    // 1) プロフィール基本
    const payload = {
      first_name: form.first_name,
      last_name : form.last_name,
      username  : form.username,
      email     : form.email,
      phone     : form.phone,
      department: form.department,
    }
    try {
      await api.patch('me/', payload)
    } catch {
      // フォールバック（基本フィールドのみ）
      const p2 = (({first_name,last_name,username,email}) => ({first_name,last_name,username,email}))(payload)
      await api.patch('dj-rest-auth/user/', p2)
    }

    // 2) アバター（あれば）
    if (canEditAvatar.value && avatarFile.value) {
      const castId = meStore.me?.cast_id ?? (await api.get('me/')).data.cast_id
      if (castId) {
        const fd = new FormData()
        fd.append('avatar', avatarFile.value)
        // InterceptorがFormDataのContent-Type除去＆store_id付与を実施
        await api.patch(`billing/casts/${castId}/`, fd)
      }
    }

    // 3) meを更新（サイドバー等へ即反映）
    await meStore.fetchMe?.()
    msg.value = '保存しました'
    if (avatarFile.value) msg.value += '（画像も更新）'
  } catch (e) {
    msg.value = e?.response?.data?.detail || e?.message || '保存に失敗しました'
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container py-3">
    <!-- アバター -->
    <div class="mb-4 d-flex align-items-center gap-3">
      <Avatar :url="previewUrl || avatarURL" :size="72" class="rounded-circle" />
      <div class="d-flex flex-column gap-2">
        <label class="btn btn-outline-secondary mb-0" :class="{disabled: !canEditAvatar}">
          画像を選択
          <input type="file" accept="image/*" class="d-none" :disabled="!canEditAvatar" @change="onPick" />
        </label>
        <small class="text-muted" v-if="!canEditAvatar">※キャストプロフィールが無いアカウントは、画像変更は不可です。</small>
      </div>
    </div>

    <!-- 基本情報 -->
    <div class="row g-3">
      <div class="col-sm-6">
        <label class="form-label">姓</label>
        <input v-model="form.last_name" class="form-control" />
      </div>
      <div class="col-sm-6">
        <label class="form-label">名</label>
        <input v-model="form.first_name" class="form-control" />
      </div>

      <div class="col-sm-6">
        <label class="form-label">ログインID（ユーザーネーム）</label>
        <input v-model="form.username" class="form-control" />
      </div>

      <div class="col-sm-6">
        <label class="form-label">メールアドレス</label>
        <input v-model="form.email" type="email" class="form-control" />
      </div>

      <div class="col-sm-6">
        <label class="form-label">電話番号</label>
        <input v-model="form.phone" class="form-control" />
      </div>

    </div>

    <div class="mt-4 d-flex align-items-center gap-3">
      <button class="btn btn-primary" :disabled="saving" @click="save">
        {{ saving ? '保存中…' : '保存' }}
      </button>
      <span class="text-muted">{{ msg }}</span>
    </div>
  </div>
</template>
