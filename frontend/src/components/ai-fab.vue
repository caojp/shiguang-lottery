<template>
  <view>
    <!-- 悬浮球 -->
    <view class="fab" @click="openPanel">
      <text class="fab-text">AI</text>
      <view class="fab-badge" />
    </view>

    <!-- 聊天面板 -->
    <view v-if="panelOpen" class="ai-panel">
      <view class="ai-head">
        <text class="ai-title">AI 智能分析</text>
        <view class="ai-actions">
          <text class="ai-action" @click="shareChat">分享</text>
          <view class="ai-close" @click="panelOpen = false">×</view>
        </view>
      </view>
      <scroll-view scroll-y scroll-with-animation class="ai-chat" :scroll-into-view="scrollTarget">
        <view v-for="(m, i) in messages" :id="`msg-${i}`" :key="i" class="msg" :class="m.role">
          <!-- AI 回复按 Markdown 渲染，用户消息保持纯文本 -->
          <rich-text v-if="m.role === 'ai'" class="md-body" :nodes="renderMd(m.text)" />
          <text v-else class="msg-text">{{ m.text }}</text>
          <view class="msg-tools" @click.stop="copyMessage(m)">复制</view>
        </view>
        <view v-if="loading" id="msg-loading" class="msg ai"><text>思考中…</text></view>
      </scroll-view>
      <view class="ai-input">
        <input v-model="input" placeholder="试试「帮我选一注双色球」" confirm-type="send" @confirm="send" />
        <view class="ai-send" @click="send"><text>发送</text></view>
      </view>
    </view>
  </view>
</template>

<script>
import { marked } from 'marked'
import { api } from '@/api/index'

const STORAGE_KEY = 'sg_ai_chat_history'
const MAX_MESSAGES = 50
const GREETING = { role: 'ai', text: '你好，我是时光选彩的 AI 分析助手。可以让我帮你选一注号码、解读冷热号、解释某个奖级规则。' }

marked.setOptions({ gfm: true, breaks: true })

export default {
  name: 'AiFab',
  data() {
    return {
      panelOpen: false,
      input: '',
      loading: false,
      scrollTarget: '',
      messages: [{ ...GREETING }],
    }
  },
  created() {
    this.restoreHistory()
  },
  methods: {
    restoreHistory() {
      try {
        const saved = uni.getStorageSync(STORAGE_KEY)
        if (saved && Array.isArray(saved) && saved.length) this.messages = saved
      } catch (err) {
        this.messages = [{ ...GREETING }]
      }
    },
    saveHistory() {
      try {
        uni.setStorageSync(STORAGE_KEY, this.messages.slice(-MAX_MESSAGES))
      } catch (err) {
        // 存储失败时忽略，不影响当前会话
      }
    },
    openPanel() {
      this.panelOpen = !this.panelOpen
      if (this.panelOpen) this.scrollToEnd()
    },
    scrollToEnd() {
      this.$nextTick(() => {
        this.scrollTarget = this.loading ? 'msg-loading' : (this.messages.length ? `msg-${this.messages.length - 1}` : '')
      })
    },
    // Markdown -> HTML，并做基础脚本过滤，避免模型输出中的可执行内容被渲染
    renderMd(text) {
      const html = marked.parse(text || '')
      return html
        .replace(/<script[\s\S]*?<\/script>/gi, '')
        .replace(/\son\w+=(?:"[^"]*"|'[^']*')/gi, '')
        .replace(/javascript:/gi, '')
    },
    copyText(text, tip) {
      uni.setClipboardData({
        data: text,
        success: () => uni.showToast({ title: tip, icon: 'none' }),
      })
    },
    copyMessage(m) {
      this.copyText(m.text, '已复制')
    },
    // 分享整段对话：支持系统分享时直接调起，否则复制全文供粘贴
    async shareChat() {
      const text = this.messages
        .map((m) => `${m.role === 'me' ? '我' : 'AI'}：${m.text}`)
        .join('\n\n')
      if (typeof navigator !== 'undefined' && navigator.share) {
        try {
          await navigator.share({ title: '时光选彩 · AI 分析', text })
          return
        } catch (err) {
          if (err && err.name === 'AbortError') return
        }
      }
      this.copyText(text, '聊天内容已复制，可粘贴分享')
    },
    async send() {
      const text = this.input.trim()
      if (!text || this.loading) return
      this.messages.push({ role: 'me', text })
      this.input = ''
      this.loading = true
      this.saveHistory()
      this.scrollToEnd()
      try {
        const res = await api.agentChat(text)
        this.messages.push({ role: 'ai', text: res.text || '已完成。' })
      } catch (err) {
        this.messages.push({ role: 'ai', text: '网络异常，请确认后端已启动。' })
      } finally {
        this.loading = false
        this.saveHistory()
        this.scrollToEnd()
      }
    },
  },
}
</script>

<style scoped lang="scss">
@import '@/uni.scss';

.fab {
  position: fixed;
  right: 26rpx;
  bottom: calc(180rpx + env(safe-area-inset-bottom));
  width: 96rpx;
  height: 96rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #E03C31, #FF7A45);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 16rpx 40rpx rgba(224, 60, 49, 0.4);
  z-index: 998;
}
.fab-text {
  font-size: 26rpx;
  font-weight: 600;
}
.fab-badge {
  position: absolute;
  top: -4rpx;
  right: -4rpx;
  width: 24rpx;
  height: 24rpx;
  border-radius: 50%;
  background: $sg-gold;
  border: 6rpx solid #fff;
}
.ai-panel {
  position: fixed;
  left: 20rpx;
  right: 20rpx;
  bottom: calc(20rpx + env(safe-area-inset-bottom));
  height: 72vh;
  max-height: 1100rpx;
  background: #fff;
  border-radius: 32rpx;
  box-shadow: 0 -16rpx 60rpx rgba(0, 0, 0, 0.15);
  z-index: 999;
  display: flex;
  flex-direction: column;
  padding: 28rpx;
}
.ai-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 20rpx;
  border-bottom: 2rpx solid $sg-line;
}
.ai-title {
  font-size: 28rpx;
  font-weight: 600;
}
.ai-actions {
  display: flex;
  align-items: center;
  gap: 20rpx;
}
.ai-action {
  font-size: 24rpx;
  color: $sg-blue;
}
.ai-close {
  width: 48rpx;
  height: 48rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36rpx;
  color: $sg-t3;
}
.ai-chat {
  flex: 1;
  height: 0;
  min-height: 0;
  padding: 20rpx 0;
}
.msg {
  max-width: 88%;
  padding: 16rpx 22rpx 8rpx;
  border-radius: 24rpx;
  font-size: 24rpx;
  line-height: 1.5;
  margin-bottom: 16rpx;
  position: relative;
}
.msg.ai {
  background: #F1F2F5;
  align-self: flex-start;
  border-top-left-radius: 8rpx;
}
.msg.me {
  background: $sg-blue;
  color: #fff;
  margin-left: auto;
  border-top-right-radius: 8rpx;
}
.msg-text {
  white-space: pre-wrap;
  word-break: break-all;
}
.msg-tools {
  margin-top: 4rpx;
  font-size: 20rpx;
  color: $sg-t3;
  text-align: right;
}
.msg.me .msg-tools {
  color: rgba(255, 255, 255, 0.75);
}
.ai-input {
  display: flex;
  gap: 16rpx;
  border-top: 2rpx solid $sg-line;
  padding-top: 20rpx;
}
.ai-input input {
  flex: 1;
  border: 2rpx solid $sg-line;
  border-radius: 999rpx;
  padding: 16rpx 28rpx;
  font-size: 28rpx;
}
.ai-send {
  background: $sg-blue;
  color: #fff;
  border-radius: 999rpx;
  padding: 0 36rpx;
  display: flex;
  align-items: center;
  font-size: 28rpx;
}
</style>

<!-- Markdown 内容由 rich-text 动态生成，需使用非 scoped 样式 -->
<style lang="scss">
@import '@/uni.scss';

.md-body {
  font-size: 24rpx;
  line-height: 1.65;
  color: $sg-t1;
  word-break: break-word;
}
.md-body p {
  margin: 6rpx 0;
}
.md-body h1,
.md-body h2,
.md-body h3,
.md-body h4 {
  font-size: 26rpx;
  font-weight: 600;
  margin: 14rpx 0 6rpx;
}
.md-body ul,
.md-body ol {
  padding-left: 36rpx;
  margin: 6rpx 0;
}
.md-body li {
  margin: 4rpx 0;
}
.md-body strong {
  font-weight: 600;
}
.md-body code {
  background: #E8EAEF;
  padding: 2rpx 8rpx;
  border-radius: 6rpx;
  font-size: 22rpx;
}
.md-body pre {
  background: #1F2329;
  color: #fff;
  padding: 16rpx;
  border-radius: 12rpx;
  overflow-x: auto;
  margin: 10rpx 0;
}
.md-body pre code {
  background: transparent;
  color: inherit;
  padding: 0;
}
.md-body table {
  border-collapse: collapse;
  width: 100%;
  margin: 10rpx 0;
  font-size: 22rpx;
}
.md-body th,
.md-body td {
  border: 1rpx solid $sg-line;
  padding: 8rpx;
}
.md-body a {
  color: $sg-blue;
}
</style>
