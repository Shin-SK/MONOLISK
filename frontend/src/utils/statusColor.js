// src/utils/statusColor.js
export const STATUS_META = {
	CALL_PENDING : { long:'電話確認[未]', short:'確未',  color:'#6c757d', badge:'secondary' },
	CALL_DONE    : { long:'電話確認[済]', short:'確済',  color:'#0dcaf0', badge:'info'      },
	BOOKED       : { long:'仮予約',       short:'仮予',  color:'#ffc107', badge:'warning'   },
	IN_SERVICE   : { long:'接客中',       short:'接中',  color:'#dc3545', badge:'danger'    },
	CASH_COLLECT : { long:'集金済',       short:'集済',  color:'#0d6efd', badge:'primary'   },
}

export const ganttColor = s => STATUS_META[s]?.color || '#ced4da'
export const bstrapBg   = s => `bg-${STATUS_META[s]?.badge || 'secondary'}`
export const textColor  = s => ['warning'].includes(STATUS_META[s]?.badge) ? 'text-dark' : 'text-white'
