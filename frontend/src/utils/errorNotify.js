// src/utils/errorNotify.js
export async function notifyError(message){
	// 権限が無ければリクエスト
	if(Notification.permission === 'default'){
		await Notification.requestPermission()
	}
	// 許可されていればネイティブ通知、拒否なら alert
	if(Notification.permission === 'granted'){
		new Notification('エラー', { body: message })
	}else{
		alert(message)
	}
}
