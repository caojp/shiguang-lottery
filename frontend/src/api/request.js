/**
 * 请求封装（uni.request Promise 化）。
 * BASE_URL：生产同源部署留空（走 nginx 反代 /api）；本地开发走 vite 代理；小程序真机需改为正式 HTTPS 域名。
 */
const BASE_URL = ''

export function request({ url, method = 'GET', data = {}, timeout = 30000 }) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + url,
      method,
      data,
      timeout,
      header: { 'content-type': 'application/json' },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.data)
        else reject(new Error((res.data && res.data.detail) || `请求失败（${res.statusCode}）`))
      },
      fail: (err) => reject(new Error(err.errMsg || '网络错误')),
    })
  })
}

export function getSessionId() {
  let sid = uni.getStorageSync('sg_session_id')
  if (!sid) {
    sid = 'sg-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10)
    uni.setStorageSync('sg_session_id', sid)
  }
  return sid
}
