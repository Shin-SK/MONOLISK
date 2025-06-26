// src/plugins/dayjs.js
import dayjs from 'dayjs'
import isBetween     from 'dayjs/plugin/isBetween'
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter'

dayjs.extend(isBetween)
dayjs.extend(isSameOrAfter)

// 何か返す必要はない。import するだけで副作用として拡張が完了。
