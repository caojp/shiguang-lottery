<template>
  <view class="tip-wrap">
    <view class="tip-dot" :class="{ on: show }" @click.stop="show = true">
      <text class="q">?</text>
    </view>

    <!-- 居中弹窗：内容超长可滚动，必须提供关闭按钮 -->
    <view v-if="show" class="tip-mask" @click="show = false">
      <view class="tip-dialog" @click.stop>
        <view class="tip-head">
          <text class="tip-title">说明</text>
          <view class="tip-close" @click="show = false">×</view>
        </view>
        <scroll-view scroll-y class="tip-body">
          <text class="tip-text">{{ text }}</text>
        </scroll-view>
        <view class="tip-ok" @click="show = false">知道了</view>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  name: 'TipDot',
  props: {
    text: { type: String, required: true },
  },
  data() {
    return { show: false }
  },
  onUnload() {
    this.show = false
  },
}
</script>

<style scoped lang="scss">
@import '@/uni.scss';

.tip-wrap {
  display: inline-flex;
  position: relative;
  flex: none;
}
.tip-dot {
  width: 30rpx;
  height: 30rpx;
  border-radius: 50%;
  background: #E8EAEF;
  color: $sg-t3;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20rpx;
  font-weight: 700;
}
.tip-dot.on {
  background: $sg-blue;
  color: #fff;
}
.tip-mask {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 1200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48rpx;
}
.tip-dialog {
  width: 100%;
  max-width: 620rpx;
  max-height: 70vh;
  background: #fff;
  border-radius: 24rpx;
  padding: 32rpx;
  box-shadow: 0 20rpx 60rpx rgba(0, 0, 0, 0.25);
  display: flex;
  flex-direction: column;
}
.tip-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 20rpx;
  border-bottom: 2rpx solid $sg-line;
}
.tip-title {
  font-size: 30rpx;
  font-weight: 600;
}
.tip-close {
  width: 48rpx;
  height: 48rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40rpx;
  line-height: 1;
  color: $sg-t3;
}
.tip-body {
  max-height: 44vh;
  padding: 24rpx 0;
}
.tip-text {
  font-size: 26rpx;
  line-height: 1.7;
  color: $sg-t2;
  white-space: pre-wrap;
}
.tip-ok {
  height: 80rpx;
  border-radius: $sg-radius-pill;
  background: $sg-blue;
  color: #fff;
  font-size: 28rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
