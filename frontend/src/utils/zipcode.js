// utils/zipcode.js
import axios from 'axios'
import debounce from 'lodash.debounce'
import { ref, watch } from 'vue'

export default function useZipcode(selectedAddress, newAddress) {
  const zipcode = ref('')
  const zipErr  = ref('')

  const query = debounce(async () => {
    zipErr.value = ''
    const z = zipcode.value.replace(/-/g, '')
    if (!/^\d{7}$/.test(z)) return          // 7桁揃うまで待つ

    try {
      const { data } = await axios.get(
        'https://api.zipaddress.net/',
        { params: { zipcode: z } }
      )

      if (data.code === 200) {
        const d = data.data

        // ① フルアドレス → ② address → ③ 自前連結 の順でフォールバック
        const full =
          d.fullAddress      ||
          d.address          ||
          `${d.pref}${d.city}${d.town || ''}`

        // UI 側に反映
        selectedAddress.value = '__new__'
        newAddress.value = {
          label  : ``,    // ラベルは県+市だけ
          address: full                     // textarea に入る方
        }
      } else {
        zipErr.value = data.message || '該当なし'
      }
    } catch {
      zipErr.value = '通信エラー'
    }
  }, 400)

  watch(zipcode, query)

  return { zipcode, zipErr }
}
