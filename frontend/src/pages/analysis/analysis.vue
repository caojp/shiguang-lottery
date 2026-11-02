<template>
  <view class="page">
    <view class="card">
      <view class="mode-row">
        <view class="seg">
          <view v-for="m in segs" :key="m.key" class="seg-item" :class="{ on: seg === m.key }" @click="switchSeg(m.key)">{{ m.label }}</view>
        </view>
        <tip-dot text="基于历史开奖统计，非预测工具；每期开奖结果相互独立，数据仅供娱乐观察" />
      </view>
      <view class="game-line">
        <text class="l">彩种</text>
        <picker :range="gameNames" :value="gameIndex" @change="onGameChange">
          <view class="picker-val">{{ gameNames[gameIndex] }} ›</view>
        </picker>
      </view>
      <view v-if="loading" class="empty">加载中…</view>

      <empty-state
        v-if="!loading && !data"
        title="分析数据加载失败"
        hint="请确认后端已启动，并已在「数据」页拉取历史开奖"
        action-text="去数据页"
        @action="goData"
      />
      <empty-state
        v-else-if="!loading && data && !data.periods"
        title="暂无历史数据"
        hint="先去「数据」页拉取历史开奖，才能统计冷热、遗漏与形态"
        action-text="去数据页"
        @action="goData"
      />

      <!-- 热号 / 冷号 -->
      <block v-if="data && data.periods && (seg === 'hot' || seg === 'cold')">
        <block v-if="!isDigit">
          <view v-for="zkey in zoneKeys" :key="zkey">
            <view class="sub-title">
              <text>{{ zoneLabel(zkey) }} · {{ seg === 'hot' ? '热号 Top8' : '冷号 Top8' }}</text>
              <tip-dot :text="`近 ${data.periods} 期${seg === 'hot' ? '出现次数最多' : '出现次数最少'}的 8 个号码（演示口径）`" />
            </view>
            <view v-for="it in segList(zkey)" :key="it.number" class="hot-row">
              <ball :num="it.number" :color="ballColor(zkey)" size="sm" />
              <text class="hot-count">出现 {{ it.count }} 次</text>
            </view>
          </view>
        </block>
        <block v-else>
          <view v-for="(pos, pi) in digitHot" :key="pi">
            <view class="sub-title">
              <text>{{ pos.label }} · {{ seg === 'hot' ? '热号 Top8' : '冷号 Top8' }}</text>
              <tip-dot text="数字型按位统计 0-9 的出现次数；出现频率不改变下期概率" />
            </view>
            <view v-for="it in (seg === 'hot' ? pos.hot : pos.cold)" :key="it.number" class="hot-row">
              <ball :num="it.number" color="orange" size="sm" :pad="false" />
              <text class="hot-count">出现 {{ it.count }} 次</text>
            </view>
          </view>
        </block>
      </block>

      <!-- 频率热力图 -->
      <block v-if="data && data.periods && seg === 'heat'">
        <block v-if="!isDigit && heatZone">
          <view class="sub-title">
            <text>{{ heatZone.label }} 1-{{ heatZone.pool_size }} 出现频率</text>
            <tip-dot text="颜色越深代表该号码出现次数越多；冷热不代表未来中奖概率" />
          </view>
          <view class="heatgrid">
            <view v-for="(item, i) in heatCells" :key="i" class="hcell" :style="{ background: heatColor(item.count, heatMax) }">
              <text :class="{ dim: item.count < 3 }">{{ item.number }}</text>
            </view>
          </view>
          <text class="bar-note">格子数字为该号码近 {{ data.periods }} 期出现次数</text>
        </block>
        <block v-else-if="isDigit">
          <view v-for="(pos, pi) in digitHeat" :key="pi">
            <view class="sub-title">
              <text>{{ pos.label }} 0-9 出现频率</text>
              <tip-dot text="数字型按位统计；位置独立，互不影响" />
            </view>
            <view class="heatgrid digit-grid">
              <view v-for="(item, i) in pos.cells" :key="i" class="hcell" :style="{ background: heatColor(item.count, pos.max) }">
                <text>{{ item.number }}</text>
              </view>
            </view>
            <text class="bar-note">格子数字为该位近 {{ data.periods }} 期出现次数</text>
          </view>
        </block>
      </block>

      <!-- 遗漏 -->
      <block v-if="seg === 'omission'">
        <view v-if="!statsData || !statsData.periods" class="empty">暂无遗漏数据</view>
        <block v-else-if="!isDigit">
          <view v-for="zkey in statZoneKeys" :key="zkey">
            <view class="sub-title">
              <text>{{ statZones[zkey].label }} · 当前遗漏 Top8</text>
              <tip-dot text="当前遗漏＝该号码距最近一次出现的期数；遗漏大不代表即将出现" />
            </view>
            <view v-for="it in statZones[zkey].omission_top" :key="it.number" class="hot-row">
              <ball :num="it.number" :color="ballColor(zkey)" size="sm" />
              <text class="hot-count">遗漏 {{ it.omission }} 期</text>
            </view>
            <text class="bar-note">该区平均遗漏 {{ statZones[zkey].avg_omission }} 期</text>
          </view>
        </block>
        <block v-else>
          <view v-for="(pos, pi) in digitStats" :key="pi">
            <view class="sub-title">
              <text>{{ pos.label }} · 当前遗漏 Top8</text>
              <tip-dot text="每位数字 0-9 的当前遗漏期数" />
            </view>
            <view v-for="it in pos.omission_top" :key="it.number" class="hot-row">
              <ball :num="it.number" color="orange" size="sm" :pad="false" />
              <text class="hot-count">遗漏 {{ it.omission }} 期</text>
            </view>
          </view>
        </block>
      </block>

      <!-- 形态：和值 / 跨度 / 奇偶 / 012 路 -->
      <block v-if="seg === 'form'">
        <view v-if="!statsData || !statsData.periods" class="empty">暂无形态统计数据</view>
        <block v-else-if="!isDigit">
          <view v-for="zkey in statZoneKeys" :key="zkey" class="form-block">
            <view class="sub-title">
              <text>{{ statZones[zkey].label }} · 形态分布</text>
              <tip-dot text="和值＝每期号码之和；跨度＝最大号-最小号；012 路＝号码除以 3 的余数分布" />
            </view>
            <view class="rowline">
              <text class="l">和值均值（范围）</text>
              <text class="r">{{ statZones[zkey].form.sum.avg }}（{{ statZones[zkey].form.sum.min }}-{{ statZones[zkey].form.sum.max }}）</text>
            </view>
            <view class="rowline">
              <text class="l">跨度均值（范围）</text>
              <text class="r">{{ statZones[zkey].form.span.avg }}（{{ statZones[zkey].form.span.min }}-{{ statZones[zkey].form.span.max }}）</text>
            </view>
            <view class="rowline">
              <text class="l">奇偶比</text>
              <text class="r">{{ statZones[zkey].form.odd_even.odd }} : {{ statZones[zkey].form.odd_even.even }}</text>
            </view>
            <view class="rowline">
              <text class="l">012 路</text>
              <text class="r">0路 {{ statZones[zkey].form.road_012['0'] }} · 1路 {{ statZones[zkey].form.road_012['1'] }} · 2路 {{ statZones[zkey].form.road_012['2'] }}</text>
            </view>
            <view class="bars">
              <view v-for="(b, i) in statZones[zkey].form.sum.buckets" :key="i" class="bar-col">
                <view class="bar" :style="{ height: bucketHeight(b.count, statZones[zkey].form.sum.buckets) }" />
              </view>
            </view>
            <text class="bar-note">和值分布区间（由低到高）</text>
          </view>
        </block>
        <block v-else-if="digitForm">
          <view class="form-block">
            <view class="sub-title">
              <text>数字形态分布</text>
              <tip-dot text="和值＝各位数字之和；跨度＝最大位-最小位；012 路＝数字除以 3 的余数" />
            </view>
            <view class="rowline">
              <text class="l">和值均值（范围）</text>
              <text class="r">{{ digitForm.sum.avg }}（{{ digitForm.sum.min }}-{{ digitForm.sum.max }}）</text>
            </view>
            <view class="rowline">
              <text class="l">跨度均值（范围）</text>
              <text class="r">{{ digitForm.span.avg }}（{{ digitForm.span.min }}-{{ digitForm.span.max }}）</text>
            </view>
            <view class="rowline">
              <text class="l">奇偶比</text>
              <text class="r">{{ digitForm.odd_even.odd }} : {{ digitForm.odd_even.even }}</text>
            </view>
            <view class="rowline">
              <text class="l">012 路</text>
              <text class="r">0路 {{ digitForm.road_012['0'] }} · 1路 {{ digitForm.road_012['1'] }} · 2路 {{ digitForm.road_012['2'] }}</text>
            </view>
            <view class="bars">
              <view v-for="(b, i) in digitForm.sum.buckets" :key="i" class="bar-col">
                <view class="bar" :style="{ height: bucketHeight(b.count, digitForm.sum.buckets) }" />
              </view>
            </view>
            <text class="bar-note">和值分布区间（由低到高）</text>
          </view>
        </block>
      </block>
    </view>

    <view class="banner">历史数据仅供娱乐观察，不能预测未来开奖——每期开奖相互独立</view>
  </view>
</template>

<script>
import Ball from '@/components/ball.vue'
import TipDot from '@/components/tip-dot.vue'
import EmptyState from '@/components/empty-state.vue'
import { api } from '@/api/index'
import { FALLBACK_GAMES, getCurrentGameCode, setCurrentGameCode, loadGames, gameIndexByCode } from '@/store/game'

export default {
  name: 'Analysis',
  components: { Ball, TipDot, EmptyState },
  data() {
    return {
      games: FALLBACK_GAMES,
      gameIndex: 0,
      seg: 'hot',
      segs: [
        { key: 'hot', label: '热号' },
        { key: 'cold', label: '冷号' },
        { key: 'heat', label: '热力图' },
        { key: 'omission', label: '遗漏' },
        { key: 'form', label: '形态' },
      ],
      data: null,
      statsData: null,
      loading: false,
    }
  },
  computed: {
    gameNames() {
      return this.games.map((g) => g.name)
    },
    curGame() {
      return this.games[this.gameIndex] || null
    },
    isDigit() {
      return !!(this.curGame && this.curGame.digits)
    },
    zoneKeys() {
      return this.data && this.data.zones ? Object.keys(this.data.zones) : []
    },
    heatZone() {
      return this.zoneKeys.length ? this.data.zones[this.zoneKeys[0]] : null
    },
    heatCells() {
      if (!this.heatZone) return []
      return Object.keys(this.heatZone.frequency)
        .map((n) => ({ number: n, count: this.heatZone.frequency[n] }))
        .sort((a, b) => Number(a.number) - Number(b.number))
    },
    heatMax() {
      return Math.max(1, ...this.heatCells.map((c) => c.count))
    },
    digitHot() {
      const positions = (this.data && this.data.digit_positions) || []
      return positions.map((freq, i) => {
        const entries = Object.keys(freq)
          .map((d) => ({ number: d, count: freq[d] }))
          .sort((a, b) => a.count - b.count)
        return {
          label: `第 ${i + 1} 位`,
          hot: entries.slice(-8).reverse(),
          cold: entries.slice(0, 8),
        }
      })
    },
    digitHeat() {
      const positions = (this.data && this.data.digit_positions) || []
      return positions.map((freq, i) => {
        const cells = Object.keys(freq)
          .map((d) => ({ number: d, count: freq[d] }))
          .sort((a, b) => Number(a.number) - Number(b.number))
        return {
          label: `第 ${i + 1} 位`,
          cells,
          max: Math.max(1, ...cells.map((c) => c.count)),
        }
      })
    },
    statZones() {
      return (this.statsData && this.statsData.zones) || {}
    },
    statZoneKeys() {
      return Object.keys(this.statZones)
    },
    digitStats() {
      return (this.statsData && this.statsData.digit_positions) || []
    },
    digitForm() {
      return this.statsData ? this.statsData.digit_form : null
    },
  },
  onLoad() {
    this.initGames()
  },
  onShow() {
    // 其他页面切换彩种后同步过来
    const idx = gameIndexByCode(this.games, getCurrentGameCode())
    if (idx !== this.gameIndex) {
      this.gameIndex = idx
      this.fetchData()
    }
  },
  methods: {
    async initGames() {
      this.games = await loadGames()
      this.gameIndex = gameIndexByCode(this.games, getCurrentGameCode())
      this.fetchData()
    },
    onGameChange(e) {
      this.gameIndex = Number(e.detail.value)
      setCurrentGameCode(this.games[this.gameIndex].code)
      this.fetchData()
    },
    switchSeg(key) {
      this.seg = key
    },
    goData() {
      uni.switchTab({ url: '/pages/data/data' })
    },
    async fetchData() {
      this.loading = true
      const code = this.games[this.gameIndex].code
      this.data = null
      this.statsData = null
      try {
        this.data = await api.hotCold(code, 60)
      } catch (e) {
        this.data = null
      }
      try {
        this.statsData = await api.analysisStats(code, 60)
      } catch (e) {
        this.statsData = null
      }
      this.loading = false
      if (!this.data) {
        uni.showToast({ title: '加载失败，请确认后端已启动', icon: 'none' })
      }
    },
    zoneLabel(zkey) {
      return (this.data.zones[zkey] || {}).label || zkey
    },
    segList(zkey) {
      const z = this.data.zones[zkey]
      return this.seg === 'hot' ? z.hot : z.cold
    },
    ballColor(zkey) {
      const code = this.games[this.gameIndex].code
      if (code === 'ssq') return zkey === 'blue' ? 'blue' : 'red'
      if (code === 'dlt') return zkey === 'front' ? 'orange' : 'blue'
      return 'blue'
    },
    heatColor(count, max) {
      const ratio = count / (max || 1)
      // 白 → 浅红 → 深红（与 UI 规范色板一致）
      if (ratio <= 0.25) return '#F5F6FA'
      if (ratio <= 0.5) return '#FBD1CE'
      if (ratio <= 0.75) return '#F07A70'
      return '#E03C31'
    },
    bucketHeight(count, buckets) {
      const max = Math.max(1, ...buckets.map((b) => b.count))
      return Math.max(4, Math.round((count / max) * 100)) + '%'
    },
  },
}
</script>

<style scoped lang="scss">
@import '@/uni.scss';

.mode-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 20rpx;
}
.game-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12rpx 0 20rpx;
  border-bottom: 2rpx solid $sg-line;
  font-size: 28rpx;
}
.sub-title {
  display: flex;
  align-items: center;
  gap: 10rpx;
  font-size: 28rpx;
  font-weight: 600;
  margin: 24rpx 0 16rpx;
}
.hot-row {
  display: flex;
  align-items: center;
  gap: 20rpx;
  padding: 12rpx 0;
  border-bottom: 2rpx dashed $sg-line;
}
.hot-row:last-child {
  border-bottom: none;
}
.hot-count {
  margin-left: auto;
  font-size: 24rpx;
  color: $sg-t2;
}
.heatgrid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 10rpx;
}
.heatgrid.digit-grid {
  grid-template-columns: repeat(5, 1fr);
}
.hcell {
  aspect-ratio: 1;
  border-radius: 12rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  font-weight: 600;
}
.hcell .dim {
  color: $sg-t3;
}
.bar-note {
  font-size: 22rpx;
  color: $sg-t3;
  display: block;
  margin-top: 16rpx;
}
.form-block {
  margin-bottom: 24rpx;
}
.bars {
  display: flex;
  align-items: flex-end;
  gap: 4rpx;
  height: 160rpx;
  margin-top: 20rpx;
}
.bar-col {
  flex: 1;
  height: 100%;
  display: flex;
  align-items: flex-end;
}
.bar {
  width: 100%;
  background: $sg-blue;
  border-radius: 4rpx 4rpx 0 0;
  opacity: 0.85;
  min-height: 4rpx;
}
</style>
