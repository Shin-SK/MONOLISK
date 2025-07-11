// src/plugins/dayjs.js
import dayjs from 'dayjs'
import isBetween     from 'dayjs/plugin/isBetween'
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter'
import 'dayjs/locale/ja'  // ← 日本語ロケールを読み込み
dayjs.locale('ja')        // ← デフォルトを日本語に

dayjs.extend(isBetween)
dayjs.extend(isSameOrAfter)

// 何か返す必要はない。import するだけで副作用として拡張が完了。
