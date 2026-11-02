<template>
  <view class="page">
    <!-- 累计战绩：仅统计含金额字段的记录（旧版记录不参与汇总） -->
    <view v-if="hasStats" class="card sum-card">
      <view class="sum-row">
        <view class="sum-item">
          <text class="sum-val">{{ stats.times }}</text>
          <text class="sum-lab">模拟次数</text>
        </view>
        <view class="sum-item">
          <text class="sum-val">¥{{ stats.cost.toLocaleString() }}</text>
          <text class="sum-lab">累计投入</text>
        </view>
        <view class="sum-item">
          <text class="sum-val win">¥{{ stats.win.toLocaleString() }}</text>
          <text class="sum-lab">累计中奖</text>
        </view>
        <view class="sum-item">
          <text class="sum-val" :class="stats.profit >= 0 ? 'win' : 'lose'">
            {{ stats.profit >= 0 ? '+' : '' }}{{ stats.profit.toLocaleString() }}
          </text>
          <text class="sum-lab">净盈亏</text>
        </view>
      </view>
      <text class="sum-note">仅统计本地模拟记录，不代表真实购彩结果</text>
    </view>

    <view class="card">
      <view class="card-title">
        <text>模拟记录</text>
        <text class="clear" @click="clearHist">清空</text>
      </view>
      <empty-state
        v-if="!records.length"
        title="暂无模拟记录"
        hint="去「选号」页机选一注，模拟开奖后会记录在这里"
        action-text="去选号"
        @action="goPick"
      />
      <view v-for="(r, i) in records" :key="i" class="rec">
        <view class="rec-badge" :style="{ background: badgeColor(r) }">{{ badgeText(r) }}</view>
        <view class="rec-main">
          <text class="rec-game">{{ r.game }}<text v-if="r.count" class="rec-count"> · {{ r.count }} 注</text></text>
          <text class="rec-nums">{{ r.nums }}</text>
          <text class="rec-time">{{ r.time }}</text>
        </view>
        <view class="rec-right">
          <text class="res" :class="r.result.startsWith('中奖') ? 'win' : 'lose'">{{ r.result }}</text>
          <text v-if="r.cost != null" class="rec-cost">投入 ¥{{ r.cost }}</text>
        </view>
      </view>
    </view>

    <view class="card">
      <view class="card-title"><text>偏好设置</text></view>
      <view class="rowline">
        <view class="l-wrap">
          <text class="row-name">一等奖模拟值</text>
          <text class="row-sub">浮动奖简化模型</text>
        </view>
        <view class="r-wrap">
          <text class="r">500 万</text>
          <tip-dot text="浮动奖在原型中按固定模拟值展示；接入后端后按官方口径与奖池联动模拟" />
        </view>
      </view>
      <view class="rowline">
        <view class="l-wrap">
          <text class="row-name">大乐透奖池 ≥ 8 亿联动</text>
          <text class="row-sub">三至七等奖自动上调</text>
        </view>
        <view class="r-wrap">
          <tip-dot text="奖池≥8亿时三至七等奖自动上调：5000→6666、300→380、150→200、15→18、5→7" />
          <switch :checked="poolHigh" color="#E03C31" @change="onPoolChange" style="transform: scale(0.8)" />
        </view>
      </view>
      <view class="rowline">
        <view class="l-wrap">
          <text class="row-name">默认注数</text>
        </view>
        <view class="r-wrap">
          <text class="r">1 注</text>
          <tip-dot text="机选模式下默认生成的注数，可在选号页临时调整" />
        </view>
      </view>
    </view>

    <view class="card">
      <view class="card-title"><text>关于</text></view>
      <view class="rowline" @click="disclaimer = !disclaimer">
        <text class="l">免责声明</text>
        <text class="r blue">{{ disclaimer ? '收起' : '展开' }}</text>
      </view>
      <view v-if="disclaimer" class="disc">
        时光选彩为学习/娱乐模拟工具，不涉及任何真实投注。所有号码由程序随机生成，任何选号策略均不改变中奖概率。请理性看待彩票，远离赌博。
      </view>
      <view class="rowline">
        <text class="l">数据来源</text>
        <text class="r">中国福彩网 / 中国体彩网</text>
      </view>
      <view class="rowline">
        <text class="l">版本</text>
        <text class="r">V0.1.0</text>
      </view>
    </view>
  </view>
</template>

<script>
import TipDot from '@/components/tip-dot.vue'
import EmptyState from '@/components/empty-state.vue'

export default {
  name: 'Mine',
  components: { TipDot, EmptyState },
  data() {
    return {
      records: [],
      poolHigh: uni.getStorageSync('sg_pool_high') !== '0',
      disclaimer: false,
    }
  },
  computed: {
    // 汇总仅基于带金额字段的新记录，旧记录（无 cost）跳过
    stats() {
      const s = { times: 0, cost: 0, win: 0, profit: 0 }
      for (const r of this.records) {
        if (r.cost == null) continue
        s.times += 1
        s.cost += r.cost || 0
        s.win += r.win || 0
      }
      s.profit = s.win - s.cost
      return s
    },
    hasStats() {
      return this.stats.times > 0
    },
  },
  onShow() {
    this.records = uni.getStorageSync('sg_records') || []
  },
  methods: {
    badgeText(r) {
      return (r.game || '?').slice(0, 1)
    },
    badgeColor(r) {
      const map = {
        ssq: '#E03C31',
        dlt: '#2456A6',
        fc3d: '#C0392B',
        pl3: '#16A085',
        pl5: '#D35400',
        qlc: '#8E44AD',
        kl8: '#2C3E50',
      }
      return map[r.code] || '#E03C31'
    },
    goPick() {
      uni.switchTab({ url: '/pages/pick/pick' })
    },
    clearHist() {
      uni.showModal({
        title: '清空记录',
        content: '确定清空全部模拟记录吗？',
        success: (res) => {
          if (res.confirm) {
            this.records = []
            uni.removeStorageSync('sg_records')
          }
        },
      })
    },
    onPoolChange(e) {
      this.poolHigh = e.detail.value
      uni.setStorageSync('sg_pool_high', this.poolHigh ? '1' : '0')
    },
  },
}
</script>

<style scoped lang="scss">
@import '@/uni.scss';

.clear {
  font-size: 24rpx;
  color: $sg-t3;
}

/* 累计战绩卡 */
.sum-card {
  padding-bottom: 24rpx;
}
.sum-row {
  display: flex;
  align-items: flex-start;
}
.sum-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
}
.sum-val {
  font-size: 32rpx;
  font-weight: 700;
}
.sum-val.win {
  color: $sg-gold;
}
.sum-val.lose {
  color: $sg-t3;
}
.sum-lab {
  font-size: 22rpx;
  color: $sg-t3;
}
.sum-note {
  display: block;
  margin-top: 20rpx;
  font-size: 20rpx;
  color: $sg-t3;
  text-align: center;
}

/* 记录条目：徽标 + 主信息 + 结果 */
.rec {
  display: flex;
  align-items: center;
  gap: 20rpx;
  padding: 24rpx 0;
  border-bottom: 1rpx solid $sg-line;
}
.rec:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.rec-badge {
  width: 64rpx;
  height: 64rpx;
  border-radius: 50%;
  color: #fff;
  font-size: 28rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.rec-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}
.rec-game {
  font-size: 28rpx;
  font-weight: 600;
}
.rec-count {
  font-size: 22rpx;
  color: $sg-t3;
  font-weight: 400;
}
.rec-nums {
  font-size: 22rpx;
  color: $sg-t3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rec-time {
  font-size: 20rpx;
  color: $sg-t3;
}
.rec-right {
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4rpx;
}
.rec-cost {
  font-size: 20rpx;
  color: $sg-t3;
}
.l-wrap {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
  padding-right: 20rpx;
}
.r-wrap {
  display: flex;
  align-items: center;
  gap: 14rpx;
  flex: none;
}
.row-name {
  font-size: 28rpx;
}
.row-sub {
  font-size: 22rpx;
  color: $sg-t3;
}
.res {
  display: block;
  font-size: 24rpx;
  font-weight: 600;
  text-align: right;
}
.res.win {
  color: $sg-gold;
}
.res.lose {
  color: $sg-t3;
}
.time {
  display: block;
  font-size: 20rpx;
  color: $sg-t3;
  text-align: right;
}
.r {
  font-size: 26rpx;
  color: $sg-t2;
}
.r.blue {
  color: $sg-blue;
}
.disc {
  font-size: 24rpx;
  color: $sg-t2;
  line-height: 1.7;
  padding: 20rpx 0;
}
</style>
