<template>
  <view class="page">
    <view class="hero">
      <view class="hero-ball">竞</view>
      <view class="hero-main">
        <text class="hero-title">竞彩足球</text>
        <text class="hero-sub">赛事竞猜玩法 · 规划中</text>
      </view>
      <text class="hero-tag">敬请期待</text>
    </view>

    <!-- 示例赛事：展示版式，赔率与赛程均为演示数据 -->
    <view class="card">
      <view class="card-title">
        <text>今日赛事（示例）</text>
        <tip-dot text="以下赛程与赔率均为演示数据，未接入官方竞彩接口；正式上线后将按真实赛程与赔率展示" />
      </view>
      <view v-for="m in matches" :key="m.id" class="match">
        <view class="match-head">
          <text class="match-league">{{ m.league }}</text>
          <text class="match-time">{{ m.time }}</text>
        </view>
        <view class="match-team">
          <view class="team">
            <text class="team-name">{{ m.home }}</text>
            <text class="team-role">主</text>
          </view>
          <text class="match-vs">VS</text>
          <view class="team right">
            <text class="team-role">客</text>
            <text class="team-name">{{ m.away }}</text>
          </view>
        </view>
        <view class="odds">
          <view v-for="(o, i) in m.odds" :key="i" class="odd">
            <text class="odd-lab">{{ ['胜', '平', '负'][i] }}</text>
            <text class="odd-val">{{ o }}</text>
          </view>
        </view>
      </view>
      <text class="match-note">示例赛事仅用于版式演示，不支持投注操作</text>
    </view>

    <view class="card">
      <view class="card-title">
        <text>玩法规划</text>
        <tip-dot text="竞彩足球为体育彩票玩法，与乐透数字型玩法规则不同，需要赛事与赔率数据支撑" />
      </view>
      <view v-for="p in plays" :key="p.name" class="rowline">
        <view class="play-l">
          <text class="play-name">{{ p.name }}</text>
          <text class="play-sub">{{ p.desc }}</text>
        </view>
        <text class="play-tag">规划中</text>
      </view>
    </view>

    <view class="card">
      <view class="card-title"><text>上线前准备</text></view>
      <view v-for="r in preps" :key="r.name" class="rowline">
        <text class="l">{{ r.name }}</text>
        <text class="r">{{ r.state }}</text>
      </view>
    </view>

    <view class="banner">竞彩为体育彩票玩法，本应用仅做模拟演示，不涉及真实投注与资金往来</view>
  </view>
</template>

<script>
import TipDot from '@/components/tip-dot.vue'

export default {
  name: 'Jingcai',
  components: { TipDot },
  data() {
    return {
      // 演示赛事：仅用于展示竞彩卡片版式
      matches: [
        { id: 1, league: '英超', time: '今日 22:00', home: '曼城', away: '热刺', odds: ['1.72', '3.60', '4.20'] },
        { id: 2, league: '西甲', time: '明日 03:00', home: '皇家马德里', away: '巴塞罗那', odds: ['2.10', '3.40', '3.05'] },
        { id: 3, league: '意甲', time: '明日 21:00', home: '国际米兰', away: '尤文图斯', odds: ['1.95', '3.25', '3.60'] },
      ],
      plays: [
        { name: '胜平负', desc: '猜比赛最终胜/平/负结果' },
        { name: '让球胜平负', desc: '按官方让球数计算胜平负' },
        { name: '比分', desc: '猜具体比分，赔率更高、难度更大' },
        { name: '总进球', desc: '猜双方总进球数区间' },
        { name: '半全场', desc: '猜半场与全场胜平负组合' },
        { name: '串关过关', desc: '2串1 / 3串1 等多场组合，全部命中才中奖' },
      ],
      preps: [
        { name: '赛事与赛程数据', state: '接入中' },
        { name: '欧赔 / 亚盘赔率', state: '接入中' },
        { name: '过关与结算规则', state: '待设计' },
      ],
    }
  },
}
</script>

<style scoped lang="scss">
@import '@/uni.scss';

.hero {
  display: flex;
  align-items: center;
  gap: 20rpx;
  background: linear-gradient(135deg, #1F7A5C, #2FA07B);
  border-radius: $sg-radius-card;
  padding: 32rpx;
  margin-bottom: $sg-gap;
  box-shadow: $sg-shadow-card;
}
.hero-ball {
  width: 72rpx;
  height: 72rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.18);
  border: 2rpx solid rgba(255, 255, 255, 0.35);
  color: #fff;
  font-size: 30rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.hero-main {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}
.hero-title {
  color: #fff;
  font-size: 32rpx;
  font-weight: 600;
}
.hero-sub {
  color: rgba(255, 255, 255, 0.82);
  font-size: 22rpx;
}
.hero-tag {
  margin-left: auto;
  color: #fff;
  font-size: 22rpx;
  padding: 8rpx 20rpx;
  border-radius: $sg-radius-pill;
  border: 2rpx solid rgba(255, 255, 255, 0.45);
  flex: none;
}
/* 示例赛事卡片 */
.match {
  padding: 24rpx 0;
  border-bottom: 1rpx solid $sg-line;
}
.match:last-of-type {
  border-bottom: none;
}
.match-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16rpx;
}
.match-league {
  font-size: 22rpx;
  color: $sg-blue;
  background: #EEF2FF;
  padding: 4rpx 16rpx;
  border-radius: $sg-radius-pill;
}
.match-time {
  font-size: 22rpx;
  color: $sg-t3;
}
.match-team {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18rpx;
}
.team {
  display: flex;
  align-items: center;
  gap: 10rpx;
  flex: 1;
}
.team.right {
  justify-content: flex-end;
}
.team-name {
  font-size: 28rpx;
  font-weight: 600;
}
.team-role {
  font-size: 20rpx;
  color: $sg-t3;
  border: 1rpx solid $sg-line;
  border-radius: 6rpx;
  padding: 0 8rpx;
}
.match-vs {
  font-size: 22rpx;
  color: $sg-t3;
  padding: 0 20rpx;
  flex: none;
}
.odds {
  display: flex;
  gap: 14rpx;
}
.odd {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10rpx;
  background: #F7F8FB;
  border-radius: 12rpx;
  padding: 12rpx 0;
}
.odd-lab {
  font-size: 22rpx;
  color: $sg-t3;
}
.odd-val {
  font-size: 26rpx;
  font-weight: 600;
  color: $sg-t1;
}
.match-note {
  display: block;
  margin-top: 20rpx;
  font-size: 20rpx;
  color: $sg-t3;
  text-align: center;
}
.play-l {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
  padding-right: 20rpx;
}
.play-name {
  font-size: 28rpx;
}
.play-sub {
  font-size: 22rpx;
  color: $sg-t3;
}
.play-tag {
  flex: none;
  font-size: 22rpx;
  color: $sg-t3;
  background: #F1F2F5;
  padding: 6rpx 18rpx;
  border-radius: $sg-radius-pill;
}
</style>
