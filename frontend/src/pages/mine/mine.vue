<template>
  <view class="page">
    <!-- 账户卡：未登录引导登录 / 已登录展示用户名与退出 -->
    <view class="card user-card">
      <block v-if="user">
        <view class="u-avatar">{{ (user.username || '?').slice(0, 1).toUpperCase() }}</view>
        <view class="u-main">
          <text class="u-name">{{ user.username }}</text>
          <text class="u-sub">选号记录已同步到云端</text>
        </view>
        <text class="u-logout" @click="logout">退出</text>
      </block>
      <block v-else>
        <view class="u-avatar plain">登</view>
        <view class="u-main">
          <text class="u-name">未登录</text>
          <text class="u-sub">登录后选号记录保存到云端，多设备可查看</text>
        </view>
        <text class="u-login" @click="goLogin">登录 / 注册</text>
      </block>
    </view>

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
      <text class="sum-note">{{ user ? '仅统计云端选号记录' : '仅统计本地模拟记录，不代表真实购彩结果' }}</text>
    </view>

    <view class="card">
      <view class="card-title">
        <text>{{ user ? '云端记录' : '模拟记录' }}</text>
        <text v-if="!user" class="clear" @click="clearHist">清空</text>
      </view>
      <empty-state
        v-if="!shownRecords.length"
        :title="user ? '暂无云端记录' : '暂无模拟记录'"
        :hint="user ? '去「选号」页生成号码并保存，记录会同步到云端' : '去「选号」页机选一注，模拟开奖后会记录在这里'"
        action-text="去选号"
        @action="goPick"
      />
      <view v-for="(r, i) in shownRecords" :key="i" class="rec">
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
import { api } from '@/api/index'
import { getUser, clearAuth } from '@/api/request'
import { FALLBACK_GAMES } from '@/store/game'

export default {
  name: 'Mine',
  components: { TipDot, EmptyState },
  data() {
    return {
      user: getUser(),
      records: [],
      serverRecords: [],
      poolHigh: uni.getStorageSync('sg_pool_high') !== '0',
      disclaimer: false,
    }
  },
  computed: {
    // 登录后展示云端记录，未登录展示本地记录
    shownRecords() {
      if (this.user) {
        return this.serverRecords.map((r) => this.toLocalRecord(r))
      }
      return this.records
    },
    // 汇总仅基于带金额字段的新记录，旧记录（无 cost）跳过
    stats() {
      const s = { times: 0, cost: 0, win: 0, profit: 0 }
      for (const r of this.shownRecords) {
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
    this.user = getUser()
    if (this.user) {
      this.loadServerRecords()
    } else {
      this.records = uni.getStorageSync('sg_records') || []
    }
  },
  methods: {
    gameName(code) {
      const g = FALLBACK_GAMES.find((x) => x.code === code)
      return g ? g.name : code
    },
    toLocalRecord(r) {
      const shown = (r.tickets || [])
        .map((t) => t.display || t.digits || '')
        .filter(Boolean)
        .slice(0, 3)
      return {
        game: this.gameName(r.game_code),
        code: r.game_code,
        nums: shown.join(' / ') + (r.count > 3 ? ` 等 ${r.count} 注` : ''),
        result: r.win > 0 ? `中奖 ${r.win.toLocaleString()} 元` : r.draw ? '未中奖' : '仅选号',
        count: r.count,
        cost: r.cost,
        win: r.win,
        time: r.created_at ? new Date(r.created_at).toLocaleString() : '',
      }
    },
    async loadServerRecords() {
      try {
        this.serverRecords = await api.myPicks(50)
      } catch (err) {
        // 401 已由请求层清除登录态；其余错误静默，保留空列表
        if (String(err.message).includes('登录')) this.user = null
      }
    },
    logout() {
      uni.showModal({
        title: '退出登录',
        content: '确定退出当前账号吗？本地记录会保留',
        success: (res) => {
          if (res.confirm) {
            clearAuth()
            this.user = null
            this.serverRecords = []
            this.records = uni.getStorageSync('sg_records') || []
          }
        },
      })
    },
    goLogin() {
      uni.navigateTo({ url: '/pages/login/login' })
    },
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

/* 账户卡 */
.user-card {
  display: flex;
  align-items: center;
  gap: 20rpx;
  padding: 28rpx;
}
.u-avatar {
  width: 72rpx;
  height: 72rpx;
  border-radius: 50%;
  background: $sg-primary;
  color: #fff;
  font-size: 30rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.u-avatar.plain {
  background: #f1f2f5;
  color: $sg-t3;
}
.u-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}
.u-name {
  font-size: 30rpx;
  font-weight: 600;
}
.u-sub {
  font-size: 22rpx;
  color: $sg-t3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.u-login {
  font-size: 26rpx;
  color: $sg-primary;
  font-weight: 600;
  flex: none;
}
.u-logout {
  font-size: 24rpx;
  color: $sg-t3;
  flex: none;
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
