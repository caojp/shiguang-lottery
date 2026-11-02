<template>
  <view class="empty-state">
    <view class="es-ball">{{ icon }}</view>
    <text class="es-title">{{ title }}</text>
    <text v-if="hint" class="es-hint">{{ hint }}</text>
    <view v-if="actionText" class="es-action" @click="$emit('action')">{{ actionText }}</view>
  </view>
</template>

<script>
export default {
  name: 'EmptyState',
  props: {
    icon: { type: String, default: '' },
    title: { type: String, default: '暂无数据' },
    hint: { type: String, default: '' },
    actionText: { type: String, default: '' },
  },
  emits: ['action'],
}
</script>

<style scoped lang="scss">
@import '@/uni.scss';

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 64rpx 0 48rpx;
}
.es-ball {
  width: 96rpx;
  height: 96rpx;
  border-radius: 50%;
  border: 2rpx dashed $sg-line;
  background: $sg-bg;
  color: $sg-t3;
  font-size: 32rpx;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}
.es-title {
  margin-top: 24rpx;
  font-size: 28rpx;
  color: $sg-t2;
}
.es-hint {
  margin-top: 8rpx;
  font-size: 24rpx;
  color: $sg-t3;
  text-align: center;
  line-height: 1.5;
}
.es-action {
  margin-top: 28rpx;
  padding: 14rpx 44rpx;
  border-radius: $sg-radius-pill;
  border: 2rpx solid $sg-blue;
  color: $sg-blue;
  font-size: 26rpx;
}
</style>
