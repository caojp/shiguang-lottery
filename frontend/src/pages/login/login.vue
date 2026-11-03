<template>
  <view class="page">
    <view class="head">
      <view class="head-ball">彩</view>
      <text class="head-title">时光选彩</text>
      <text class="head-sub">登录后，模拟选号记录将保存到云端</text>
    </view>

    <view class="card">
      <view class="seg">
        <view class="seg-item" :class="{ on: mode === 'login' }" @click="mode = 'login'">登录</view>
        <view class="seg-item" :class="{ on: mode === 'register' }" @click="mode = 'register'">注册</view>
      </view>

      <view class="field">
        <text class="f-label">用户名</text>
        <input class="f-input" v-model="username" maxlength="20" placeholder="3-20 位字母、数字或下划线" />
      </view>
      <view class="field">
        <text class="f-label">密码</text>
        <input class="f-input" v-model="password" maxlength="64" password placeholder="6-64 位" />
      </view>

      <view class="btn-primary" :class="{ disabled: loading }" @click="submit">
        {{ loading ? '提交中…' : mode === 'login' ? '登录' : '注册并登录' }}
      </view>
      <text class="tip">
        {{ mode === 'login' ? '还没有账号？' : '已有账号？' }}
        <text class="tip-link" @click="mode = mode === 'login' ? 'register' : 'login'">
          {{ mode === 'login' ? '去注册' : '去登录' }}
        </text>
      </text>
      <text class="tip sub">账户仅用于保存模拟选号记录，与任何真实购彩、支付无关</text>
    </view>
  </view>
</template>

<script>
import { api } from '@/api/index'
import { setAuth } from '@/api/request'

export default {
  name: 'Login',
  data() {
    return {
      mode: 'login',
      username: '',
      password: '',
      loading: false,
    }
  },
  methods: {
    async submit() {
      const username = this.username.trim()
      if (username.length < 3 || username.length > 20) {
        uni.showToast({ title: '用户名需为 3-20 位', icon: 'none' })
        return
      }
      if (this.password.length < 6) {
        uni.showToast({ title: '密码至少 6 位', icon: 'none' })
        return
      }
      this.loading = true
      try {
        const payload = { username, password: this.password }
        const res = this.mode === 'login' ? await api.login(payload) : await api.register(payload)
        setAuth(res.access_token, res.user)
        uni.showToast({ title: this.mode === 'login' ? '登录成功' : '注册成功', icon: 'success' })
        setTimeout(() => {
          uni.switchTab({ url: '/pages/mine/mine' })
        }, 500)
      } catch (err) {
        uni.showToast({ title: err.message, icon: 'none' })
      } finally {
        this.loading = false
      }
    },
  },
}
</script>

<style scoped lang="scss">
@import '@/uni.scss';

.page {
  min-height: 100vh;
  background: $sg-bg;
  padding: 0 32rpx;
}
.head {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 96rpx 0 48rpx;
}
.head-ball {
  width: 96rpx;
  height: 96rpx;
  border-radius: 50%;
  background: $sg-primary;
  color: #fff;
  font-size: 48rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.head-title {
  font-size: 40rpx;
  font-weight: 700;
  margin-top: 24rpx;
}
.head-sub {
  font-size: 24rpx;
  color: $sg-t3;
  margin-top: 12rpx;
}
.seg {
  display: flex;
  background: #f1f2f5;
  border-radius: $sg-radius-inner;
  padding: 6rpx;
  margin-bottom: 32rpx;
}
.seg-item {
  flex: 1;
  text-align: center;
  padding: 16rpx 0;
  border-radius: $sg-radius-inner;
  font-size: 28rpx;
  color: $sg-t2;
}
.seg-item.on {
  background: #fff;
  color: $sg-primary;
  font-weight: 600;
}
.field {
  margin-bottom: 24rpx;
}
.f-label {
  display: block;
  font-size: 24rpx;
  color: $sg-t3;
  margin-bottom: 10rpx;
}
.f-input {
  border: 2rpx solid $sg-line;
  border-radius: $sg-radius-inner;
  padding: 20rpx 24rpx;
  font-size: 30rpx;
  background: #fff;
}
.btn-primary {
  margin-top: 32rpx;
}
.btn-primary.disabled {
  opacity: 0.6;
}
.tip {
  display: block;
  text-align: center;
  font-size: 24rpx;
  color: $sg-t3;
  margin-top: 24rpx;
}
.tip-link {
  color: $sg-primary;
}
.tip.sub {
  font-size: 20rpx;
  color: $sg-t3;
}
</style>
