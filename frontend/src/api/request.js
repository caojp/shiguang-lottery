/**
 * 请求封装（uni.request Promise 化）。
 * BASE_URL：生产同源部署留空（走 nginx 反代 /api）；本地开发走 vite 代理；小程序真机需改为正式 HTTPS 域名。
 * 登录态：带 Authorization: Bearer <token>；401 时清除本地登录态。
 */
const BASE_URL = ''
const TOKEN_KEY = 'sg_token'
const USER_KEY = 'sg_user'

export function request({ url, method = 'GET', data = {}, timeout = 30000, auth = true }) {
  return new Promise((resolve, reject) => {
    const header = { 'content-type': 'application/json' }
    const token = uni.getStorageSync(TOKEN_KEY)
    if (auth && token) header.Authorization = 'Bearer ' + token
    uni.request({
      url: BASE_URL + url,
      method,
      data,
      timeout,
      header,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else if (res.statusCode === 401 && auth) {
          // 登录已失效：清除本地登录态
          uni.removeStorageSync(TOKEN_KEY)
          uni.removeStorageSync(USER_KEY)
          reject(new Error((res.data && res.data.detail) || '登录已失效，请重新登录'))
        } else {
          reject(new Error((res.data && res.data.detail) || `请求失败（${res.statusCode}）`))
        }
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

/** 当前登录 token（无则为空串） */
export function getToken() {
  return uni.getStorageSync(TOKEN_KEY) || ''
}

/** 当前登录用户 {id, username}（无则为 null） */
export function getUser() {
  return uni.getStorageSync(USER_KEY) || null
}

/** 保存登录态 */
export function setAuth(token, user) {
  uni.setStorageSync(TOKEN_KEY, token)
  uni.setStorageSync(USER_KEY, user)
}

/** 清除登录态 */
export function clearAuth() {
  uni.removeStorageSync(TOKEN_KEY)
  uni.removeStorageSync(USER_KEY)
}
