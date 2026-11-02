<script>
export default {
  onLaunch() {
    // 首次启动生成匿名会话标识（不做账户体系）
    if (!uni.getStorageSync('sg_session_id')) {
      uni.setStorageSync('sg_session_id', 'sg-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10))
    }
  },
}
</script>

<style lang="scss">
@import '@/uni.scss';

/* 全局基础样式（与 UI 设计规范 Design Tokens 对齐） */
page {
  background: $sg-bg;
  color: $sg-t1;
  font-size: 28rpx;
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
}

/* 页面统一内边距：底部预留悬浮 AI 与 tabBar 空间 */
.page {
  padding: 20rpx $sg-page-x calc(180rpx + env(safe-area-inset-bottom));
}

.card {
  background: $sg-card;
  border-radius: $sg-radius-card;
  box-shadow: $sg-shadow-card;
  padding: 32rpx;
  margin-bottom: $sg-gap;
}

.card-title {
  font-size: 30rpx;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $sg-gap;
}

.banner {
  background: #FFF7E6;
  color: #AD6800;
  font-size: 24rpx;
  line-height: 1.5;
  padding: 16rpx 24rpx;
  border-radius: $sg-radius-inner;
  margin-bottom: $sg-gap;
}

/* 通用行：左右两端对齐 + 分隔线 */
.rowline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20rpx 0;
  font-size: 28rpx;
  border-bottom: 2rpx solid $sg-line;
}
.rowline:last-child {
  border-bottom: none;
}
.rowline .l {
  color: $sg-t1;
}
.rowline .r {
  font-size: 26rpx;
  color: $sg-t2;
}

/* 分段控件 */
.seg {
  flex: 1;
  display: flex;
  background: #EFF0F4;
  border-radius: $sg-radius-inner;
  padding: 6rpx;
}
.seg-item {
  flex: 1;
  text-align: center;
  padding: 16rpx 0;
  border-radius: 16rpx;
  font-size: 28rpx;
  color: $sg-t2;
}
.seg-item.on {
  background: #fff;
  color: $sg-t1;
  font-weight: 600;
  box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.08);
}

/* 筛选 chip */
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
  margin-bottom: $sg-gap;
}
.schip {
  padding: 12rpx 26rpx;
  border-radius: $sg-radius-pill;
  border: 2rpx solid $sg-line;
  background: #fff;
  font-size: 24rpx;
  color: $sg-t2;
}
.schip.on {
  background: $sg-blue;
  border-color: $sg-blue;
  color: #fff;
  font-weight: 600;
}

/* 下拉选择值 */
.picker-val {
  color: $sg-blue;
  font-size: 28rpx;
}

.btn-primary {
  background: $sg-primary;
  color: #FFFFFF;
  border-radius: $sg-radius-inner;
  font-size: 30rpx;
  font-weight: 600;
  padding: 24rpx 0;
  text-align: center;
}

.btn-blue {
  background: $sg-blue;
  color: #FFFFFF;
  border-radius: $sg-radius-inner;
  font-size: 30rpx;
  font-weight: 600;
  padding: 24rpx 0;
  text-align: center;
}

.btn-ghost {
  background: #FFFFFF;
  color: $sg-t1;
  border: 2rpx solid $sg-line;
  border-radius: $sg-radius-inner;
  font-size: 30rpx;
  padding: 24rpx 0;
  text-align: center;
}

.empty {
  text-align: center;
  color: $sg-t3;
  font-size: 26rpx;
  padding: 60rpx 0;
}
</style>
