<!-- src/views/ProfileEdit.vue -->
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
// src/views/ProfileEdit.vue の save() 内
async function save() {
  saving.value = true
  msg.value = ''
  try {
    const me = meStore.me || (await api.get('me/')).data

    // 送れるのは first_name / last_name / email / （必要なら username）
    const payload = {
      first_name: form.first_name,
      last_name : form.last_name,
      email     : form.email,
    }
    // username を本当に変更した時だけ付ける（＝一意チェックを回避）
    if ((form.username || '') !== (me.username || '')) {
      payload.username = form.username
    }

    await api.patch('dj-rest-auth/user/', payload)

    // 画像は今まで通り
    if (canEditAvatar.value && avatarFile.value) {
      const castId = me.cast_id ?? (await api.get('me/')).data.cast_id
      if (castId) {
        const fd = new FormData()
        fd.append('avatar', avatarFile.value)
        await api.patch(`billing/casts/${castId}/`, fd)
      }
    }

    await meStore.fetchMe?.()
    msg.value = '保存しました'
  } catch (e) {
    // サーバのフィールドエラーをそのまま表示
    const d = e?.response?.data
    msg.value = d ? JSON.stringify(d) : (e?.message || '保存に失敗しました')
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


<style scoped lang="scss">

input{
  background: white;
}

</style>