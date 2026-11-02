<template>
  <view class="page">
    <view class="card">
      <view class="rowline">
        <text class="l">彩种</text>
        <picker :range="gameNames" :value="gameIndex" @change="onGameChange">
          <view class="picker-val">{{ gameNames[gameIndex] }} ›</view>
        </picker>
      </view>
      <view class="rowline">
        <view class="l-row">
          <text class="l">回测期数</text>
          <tip-dot text="期数越多结论越稳定；需先有历史数据（见「数据」页或 fetch_history.py --seed-demo）" />
        </view>
        <picker :range="periodOptions" :value="periodIndex" @change="onPeriodChange">
          <view class="picker-val">{{ periodOptions[periodIndex] }} 期 ›</view>
        </picker>
      </view>
      <view class="rowline">
        <view class="l-row">
          <text class="l">每期注数</text>
          <tip-dot text="每期生成多少注参与回测；注数越多指标越平滑，耗时也越长" />
        </view>
        <picker :range="trialOptions" :value="trialIndex" @change="onTrialChange">
          <view class="picker-val">{{ trialOptions[trialIndex] }} 注 ›</view>
        </picker>
      </view>
      <view class="rowline">
        <text class="l">对照基线</text>
        <text class="r">纯随机机选</text>
      </view>
      <view class="strat-title">
        <text>策略组合</text>
        <tip-dot text="区间均衡：各号码区间数量均匀；奇偶约束：限制奇偶比；和值约束：控制和值区间；连号控制：限制相邻连号。回测不使用冷热权重，避免引入未来数据" />
      </view>
      <view class="chips">
        <view v-for="s in stratChips" :key="s.name" class="schip" :class="{ on: s.on }" @click="s.on = !s.on">{{ s.name }}</view>
      </view>
      <view class="btn-primary" :class="{ disabled: running }" @click="run">
        {{ running ? '回测运行中…' : '开始回测' }}
      </view>
    </view>

    <view v-if="result" class="metrics">
      <view class="metric">
        <view class="lab-row">
          <text class="lab">平均命中</text>
          <tip-dot text="策略每期命中开奖号码数量的均值，越高越好" />
        </view>
        <text class="val blue">{{ result.avg_hits }}</text>
        <text class="sub">每期命中号码数</text>
      </view>
      <view class="metric">
        <view class="lab-row">
          <text class="lab">平均相似度</text>
          <tip-dot text="号码组合与开奖号的重合程度（0-1）" />
        </view>
        <text class="val">{{ result.avg_similarity }}</text>
        <text class="sub">与开奖号的重合度</text>
      </view>
      <view class="metric">
        <view class="lab-row">
          <text class="lab">随机基线</text>
          <tip-dot text="纯随机机选的理论命中水平，作为对照基准" />
        </view>
        <text class="val">{{ result.baseline_similarity }}</text>
        <text class="sub">纯机选基准</text>
      </view>
      <view class="metric">
        <view class="lab-row">
          <text class="lab">显著性</text>
          <tip-dot text="样本内判断策略是否稳定优于基线（演示口径，非统计检验）" />
        </view>
        <text class="val gold">{{ result.is_significant ? '显著 ✓' : '不显著' }}</text>
        <text class="sub">{{ result.is_significant ? '样本内优于基线' : '样本内波动' }}</text>
      </view>
      <view class="metric">
        <view class="lab-row">
          <text class="lab">投注回报率</text>
          <tip-dot text="回测总投入与总中奖金额的比值（ROI）；彩票为负期望游戏，长期回报率为负属正常" />
        </view>
        <text class="val" :class="result.roi >= 0 ? 'gold' : 'danger'">{{ pct(result.roi) }}</text>
        <text class="sub">投入 ¥{{ result.cost }} · 中奖 ¥{{ result.total_win }}</text>
      </view>
      <view class="metric">
        <view class="lab-row">
          <text class="lab">中奖注数占比</text>
          <tip-dot text="回测期内中奖注数 / 总注数，对照基线为纯随机机选" />
        </view>
        <text class="val">{{ pct(result.win_rate) }}</text>
        <text class="sub">随机基线 {{ pct(result.baseline_win_rate) }}</text>
      </view>
    </view>

    <view v-if="result" class="card">
      <view class="card-title"><text>逐期相似度走势</text></view>
      <view class="bars">
        <view v-for="(d, i) in result.detail" :key="i" class="bar-col">
          <view class="bar" :style="{ height: barHeight(d.similarity) }" />
        </view>
      </view>
      <text class="bar-note">每根柱为该期策略相似度（相对 0-1 归一化）</text>
    </view>

    <view v-if="result" class="card">
      <view class="card-title"><text>最近 10 期明细</text></view>
      <view v-for="(d, i) in recentDetail" :key="i" class="rowline">
        <text class="l">{{ d.issue }} 期</text>
        <text class="r">命中 {{ d.hits }} · 相似 {{ d.similarity }}</text>
      </view>
    </view>

    <empty-state v-else title="还没有回测结果" hint="选择彩种、回测期数与策略后点击「开始回测」" />
  </view>
</template>

<script>
import TipDot from '@/components/tip-dot.vue'
import EmptyState from '@/components/empty-state.vue'
import { api } from '@/api/index'
import { getSessionId } from '@/api/request'
import { FALLBACK_GAMES, getCurrentGameCode, setCurrentGameCode, loadGames, gameIndexByCode } from '@/store/game'

export default {
  name: 'Backtest',
  components: { TipDot, EmptyState },
  data() {
    return {
      games: FALLBACK_GAMES,
      gameIndex: 0,
      periodIndex: 1,
      periodOptions: [50, 100, 200],
      trialIndex: 0,
      trialOptions: [10, 50, 100],
      stratChips: [
        { name: '区间均衡', on: true },
        { name: '奇偶约束', on: false },
        { name: '和值约束', on: false },
        { name: '连号控制', on: false },
      ],
      running: false,
      result: null,
    }
  },
  computed: {
    gameNames() {
      return this.games.map((g) => g.name)
    },
    recentDetail() {
      return this.result ? this.result.detail.slice(-10) : []
    },
  },
  onLoad() {
    this.initGames()
  },
  onShow() {
    const idx = gameIndexByCode(this.games, getCurrentGameCode())
    if (idx !== this.gameIndex) {
      this.gameIndex = idx
      this.result = null
    }
  },
  methods: {
    async initGames() {
      this.games = await loadGames()
      this.gameIndex = gameIndexByCode(this.games, getCurrentGameCode())
    },
    onGameChange(e) {
      this.gameIndex = Number(e.detail.value)
      setCurrentGameCode(this.games[this.gameIndex].code)
      this.result = null
    },
    onPeriodChange(e) {
      this.periodIndex = Number(e.detail.value)
      this.result = null
    },
    onTrialChange(e) {
      this.trialIndex = Number(e.detail.value)
      this.result = null
    },
    pct(v) {
      const n = Number(v || 0)
      return (n * 100).toFixed(1) + '%'
    },
    barHeight(sim) {
      return Math.max(4, Math.round(sim * 100)) + '%'
    },
    buildStrategy() {
      const g = this.games[this.gameIndex]
      const zones = (g && g.zones) || []
      const on = this.stratChips.filter((s) => s.on).map((s) => s.name)
      const strategy = {}
      const splitCounts = (pick) => {
        const base = Math.floor(pick / 3)
        const rem = pick % 3
        return [base + (rem > 0 ? 1 : 0), base + (rem > 1 ? 1 : 0), base]
      }
      if (on.includes('区间均衡')) {
        strategy.zone_split = {}
        zones.forEach((z) => (strategy.zone_split[z.name] = splitCounts(z.pick)))
      }
      if (on.includes('奇偶约束')) {
        strategy.odd_even = {}
        zones.forEach((z) => (strategy.odd_even[z.name] = Math.floor(z.pick / 2)))
      }
      if (on.includes('和值约束') && zones.length) {
        const z = zones[0]
        const minSum = (z.pick * (z.pick + 1)) / 2
        const maxSum = (z.pick * (2 * z.pool_size - z.pick + 1)) / 2
        strategy.sum_range = {
          zone: z.name,
          min: Math.floor(minSum + (maxSum - minSum) * 0.2),
          max: Math.ceil(maxSum - (maxSum - minSum) * 0.2),
        }
      }
      if (on.includes('连号控制')) strategy.consecutive = 'forbid'
      return strategy
    },
    async run() {
      if (this.running) return
      this.running = true
      try {
        const res = await api.runBacktest({
          game_code: this.games[this.gameIndex].code,
          session_id: getSessionId(),
          periods: this.periodOptions[this.periodIndex],
          strategy: this.buildStrategy(),
          trials_per_period: this.trialOptions[this.trialIndex],
        })
        this.result = res
      } catch (err) {
        uni.showToast({ title: err.message, icon: 'none', duration: 3000 })
      } finally {
        this.running = false
      }
    },
  },
}
</script>

<style scoped lang="scss">
@import '@/uni.scss';

.l-row {
  display: flex;
  align-items: center;
  gap: 10rpx;
}
.strat-title {
  display: flex;
  align-items: center;
  gap: 10rpx;
  font-size: 26rpx;
  color: $sg-t2;
  margin: 24rpx 0 16rpx;
}
.btn-primary.disabled {
  opacity: 0.6;
}
.metrics {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20rpx;
  margin-bottom: 24rpx;
}
.metric {
  background: #fff;
  border-radius: 28rpx;
  box-shadow: 0 8rpx 24rpx rgba(31, 35, 41, 0.06);
  padding: 28rpx;
}
.lab-row {
  display: flex;
  align-items: center;
  gap: 8rpx;
}
.lab {
  font-size: 24rpx;
  color: $sg-t3;
}
.val {
  font-size: 48rpx;
  font-weight: 700;
  margin-top: 8rpx;
  display: block;
  font-variant-numeric: tabular-nums;
}
.val.blue {
  color: $sg-blue;
}
.val.gold {
  color: $sg-gold;
}
.val.danger {
  color: $sg-danger;
}
.sub {
  font-size: 22rpx;
  color: $sg-t3;
  display: block;
  margin-top: 4rpx;
}
.bars {
  display: flex;
  align-items: flex-end;
  gap: 4rpx;
  height: 220rpx;
}
.bar-col {
  flex: 1;
  height: 100%;
  display: flex;
  align-items: flex-end;
}
.bar {
  width: 100%;
  background: $sg-primary;
  border-radius: 4rpx 4rpx 0 0;
  opacity: 0.85;
  min-height: 4rpx;
}
.bar-note {
  font-size: 22rpx;
  color: $sg-t3;
  display: block;
  margin-top: 12rpx;
}
</style>
