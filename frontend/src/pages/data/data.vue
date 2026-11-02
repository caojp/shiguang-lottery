<template>
  <view class="page">
    <view class="card">
      <!-- 可折叠头部：点击整行展开/收起 -->
      <view class="card-title title-toggle" @click="srcOpen = !srcOpen">
        <view class="title-l">
          <text>数据源状态</text>
          <text v-if="!srcOpen" class="title-sum">{{ statusSummary }}</text>
        </view>
        <view class="title-r">
          <view @click.stop>
            <tip-dot text="历史开奖由后端幂等写入 PostgreSQL（同期限号自动覆盖）并记录来源；展开后可点击「立即拉取」手动补数" />
          </view>
          <text class="chev" :class="{ open: srcOpen }">⌄</text>
        </view>
      </view>

      <block v-if="srcOpen">
        <view class="rowline">
          <view class="l-wrap">
            <text class="row-name">自动同步</text>
          </view>
          <text class="r">每日 21:35 · 开奖后</text>
        </view>
        <view v-if="loading" class="empty">加载中…</view>
        <view v-for="d in status" :key="d.game_code" class="rowline">
          <view class="l-wrap">
            <view class="dot" :class="d.state" />
            <view>
              <text class="row-name">{{ d.name }}</text>
              <text class="row-sub">{{ d.total ? `已入库 ${d.total} 期 · 最新 ${d.latest_issue}` : '未拉取' }}（{{ sourceName(d.source) }}）</text>
            </view>
          </view>
          <text v-if="d.total" class="ok-tag">连续</text>
        </view>
        <view class="btn-blue fetch-btn" :class="{ loading: fetching }" @click="runFetch">
          {{ fetching ? '拉取中…' : '立即拉取' }}
        </view>
        <text class="fetch-note">系统每日自动同步，此按钮仅用于手动补拉</text>
      </block>
    </view>

    <view class="card">
      <view class="card-title">
        <text>最近开奖</text>
        <view class="hist-range">
          <view
            v-for="r in [10, 20, 30]"
            :key="r"
            class="range-chip"
            :class="{ on: histLimit === r }"
            @click="setLimit(r)"
          >{{ r }} 期</view>
        </view>
      </view>
      <scroll-view scroll-x class="hist-games">
        <view
          v-for="g in games"
          :key="g.code"
          class="schip"
          :class="{ on: histCode === g.code }"
          @click="switchHist(g.code)"
        >{{ g.name }}</view>
      </scroll-view>
      <view v-if="histLoading" class="empty">加载中…</view>
      <view v-else-if="histError" class="empty">数据服务暂不可用，请检查后端连接</view>
      <view v-else-if="!history.length" class="empty">暂无该彩种历史开奖，可展开上方「数据源状态」手动拉取</view>
      <view v-for="h in history" :key="h.issue" class="hist-row">
        <view class="hist-head">
          <text class="hist-issue">第 {{ h.issue }} 期</text>
          <text class="hist-date">{{ h.draw_date || '—' }}</text>
        </view>
        <view class="balls">
          <template v-if="!histGame || histGame.digits">
            <text class="hist-digits">{{ (h.numbers && h.numbers.digits) || '—' }}</text>
          </template>
          <template v-else>
            <template v-for="(z, zi) in histGame.zones" :key="z.name">
              <ball
                v-for="n in ((h.numbers && h.numbers.zones && h.numbers.zones[z.name]) || [])"
                :key="`${z.name}-${n}`"
                :num="n"
                :color="zoneColor(z.name)"
                size="sm"
              />
              <view v-if="zi < histGame.zones.length - 1" class="plus">+</view>
            </template>
            <ball v-if="h.numbers && h.numbers.special" :num="h.numbers.special" color="gold" size="sm" />
          </template>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import TipDot from '@/components/tip-dot.vue'
import Ball from '@/components/ball.vue'
import { api } from '@/api/index'
import { loadGames } from '@/store/game'

export default {
  name: 'DataPage',
  components: { TipDot, Ball },
  data() {
    return {
      status: [],
      loading: false,
      srcOpen: true,
      // 最近开奖浏览
      games: [],
      histCode: 'ssq',
      histLimit: 10,
      history: [],
      histLoading: false,
      histError: false,
      fetching: false,
    }
  },
  computed: {
    statusSummary() {
      if (!this.status.length) return '暂无数据'
      const total = this.status.reduce((sum, d) => sum + (d.total || 0), 0)
      const latest = this.status
        .map((d) => d.latest_issue)
        .filter(Boolean)
        .sort()
        .pop()
      return latest ? `${total} 期 · 最新 ${latest}` : `${total} 期`
    },
    histGame() {
      return this.games.find((g) => g.code === this.histCode) || null
    },
  },
  onLoad() {
    this.load()
    this.loadGames()
  },
  methods: {
    async load() {
      this.loading = true
      try {
        this.status = await api.dataStatus()
      } catch (e) {
        uni.showToast({ title: '加载失败，请确认后端已启动', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    async loadGames() {
      // 后端未启动时自动回退到内置彩种列表，保证筛选条可见
      this.games = await loadGames()
      await this.loadHistory()
    },
    async loadHistory() {
      this.histLoading = true
      this.histError = false
      try {
        const rows = await api.dataHistory(this.histCode, this.histLimit)
        // 后端已按期号倒序，这里再做一次防御性排序，保证最新期在最上方
        this.history = [...(rows || [])].sort((a, b) => String(b.issue).localeCompare(String(a.issue)))
      } catch (e) {
        this.history = []
        this.histError = true
      } finally {
        this.histLoading = false
      }
    },
    switchHist(code) {
      if (this.histCode === code) return
      this.histCode = code
      this.loadHistory()
    },
    setLimit(n) {
      if (this.histLimit === n) return
      this.histLimit = n
      this.loadHistory()
    },
    zoneColor(name) {
      const code = this.histCode
      if (code === 'ssq') return name === 'blue' ? 'blue' : 'red'
      if (code === 'dlt') return name === 'front' ? 'orange' : 'blue'
      if (code === 'qlc') return 'blue'
      if (code === 'pl3') return 'orange'
      if (code === 'pl5') return 'blue'
      return 'red'
    },
    sourceName(s) {
      return s === 'demo' ? '演示' : s === 'official' ? '官方' : '手动'
    },
    // 移动端直接触发后端入库：按钮内联 loading，完成后刷新状态与最近开奖
    async runFetch() {
      if (this.fetching) return
      this.fetching = true
      try {
        const res = await api.fetchData({ periods: 30 })
        uni.showToast({
          title: res.updated ? `已更新 ${res.updated} 期` : '数据已是最新',
          icon: 'none',
        })
        await Promise.all([this.load(), this.loadHistory()])
      } catch (e) {
        uni.showToast({ title: e.message || '拉取失败，请稍后重试', icon: 'none' })
      } finally {
        this.fetching = false
      }
    },
  },
}
</script>

<style scoped lang="scss">
@import '@/uni.scss';

.l-wrap {
  display: flex;
  align-items: center;
  gap: 16rpx;
}
/* 数据源状态：折叠头 */
.title-toggle {
  cursor: pointer;
}
.title-l {
  display: flex;
  align-items: baseline;
  gap: 16rpx;
  min-width: 0;
}
.title-sum {
  font-size: 22rpx;
  font-weight: 400;
  color: $sg-t3;
}
.title-r {
  display: flex;
  align-items: center;
  gap: 12rpx;
  flex: none;
}
.chev {
  font-size: 32rpx;
  color: $sg-t3;
  line-height: 1;
  transition: transform 0.2s;
  transform: rotate(0deg);
}
.chev.open {
  transform: rotate(180deg);
}
.fetch-btn {
  margin-top: 28rpx;
}
.dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  flex: none;
}
.dot.ok {
  background: $sg-success;
}
.dot.warn {
  background: $sg-gold;
}
.dot.no {
  background: $sg-t3;
}
.row-name {
  display: block;
  font-size: 28rpx;
}
.row-sub {
  display: block;
  font-size: 22rpx;
  color: $sg-t3;
  margin-top: 4rpx;
}
.ok-tag {
  font-size: 22rpx;
  color: $sg-success;
}

/* 最近开奖 */
.hist-range {
  display: flex;
  gap: 10rpx;
}
.range-chip {
  font-size: 22rpx;
  color: $sg-t3;
  padding: 6rpx 16rpx;
  border-radius: $sg-radius-pill;
  border: 2rpx solid $sg-line;
}
.range-chip.on {
  color: $sg-blue;
  border-color: $sg-blue;
  background: #EEF2FF;
}
.hist-games {
  white-space: nowrap;
  margin: 8rpx 0 20rpx;
}
.hist-games .schip {
  display: inline-flex;
  margin-right: 14rpx;
}
.hist-row {
  padding: 20rpx 0;
  border-bottom: 1rpx solid $sg-line;
}
.hist-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.hist-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}
.hist-issue {
  font-size: 26rpx;
  font-weight: 600;
}
.hist-date {
  font-size: 22rpx;
  color: $sg-t3;
}
.balls {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  align-items: center;
}
.plus {
  color: $sg-t3;
  font-weight: 700;
  font-size: 24rpx;
}
.hist-digits {
  font-size: 32rpx;
  font-weight: 700;
  letter-spacing: 6rpx;
  color: $sg-t1;
}
/* 拉取中：降低透明度并屏蔽重复点击，避免移动端连点产生重复请求 */
.btn-blue.loading {
  opacity: 0.6;
  pointer-events: none;
}
.fetch-note {
  display: block;
  margin-top: 14rpx;
  font-size: 22rpx;
  color: $sg-t3;
  text-align: center;
}
</style>
