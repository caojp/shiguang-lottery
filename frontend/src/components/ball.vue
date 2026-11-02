<template>
  <view class="ball" :class="[color, size, { hit: hit }]">{{ display }}</view>
</template>

<script>
export default {
  name: 'Ball',
  props: {
    num: { type: [Number, String], default: '' },
    color: { type: String, default: 'red' },   // red | blue | orange | gold | gray
    size: { type: String, default: 'md' },     // md | sm
    pad: { type: Boolean, default: true },
    hit: { type: Boolean, default: false },    // 对奖命中高亮
  },
  computed: {
    display() {
      if (this.num === '' || this.num === null) return ''
      return this.pad ? String(this.num).padStart(2, '0') : String(this.num)
    },
  },
}
</script>

<style scoped lang="scss">
@import '@/uni.scss';

.ball {
  border-radius: 50%;
  color: #fff;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.md {
  width: $ball-md;
  height: $ball-md;
  font-size: 28rpx;
}
.sm {
  width: $ball-sm;
  height: $ball-sm;
  font-size: 20rpx;
}
.red { background: $sg-primary; }
.blue { background: $sg-blue; }
.orange { background: $sg-orange; }
.gold { background: $sg-gold; }
.gray { background: #8F959E; }
/* 命中号码：金色描边高亮 */
.hit {
  box-shadow: 0 0 0 4rpx $sg-gold;
}
</style>
