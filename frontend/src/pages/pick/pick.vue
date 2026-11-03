<template>
  <view class="page">
    <!-- 自定义导航 -->
    <view class="nav">
      <view class="nav-title">
        <view class="nav-ball">彩</view>
        <text>时光选彩</text>
      </view>
      <text class="nav-sub">模拟彩票 · 不涉及真实投注</text>
    </view>

    <view class="banner">模拟用途，不涉及真实投注，任何策略都不改变中奖概率</view>

    <!-- 彩种切换 -->
    <view class="games-row">
      <scroll-view scroll-x class="games">
        <view
          v-for="g in games"
          :key="g.code"
          class="chip"
          :class="{ on: g.code === curCode }"
          @click="switchGame(g.code)"
        >{{ g.name }}</view>
        <view class="chip planned" @click="goJingcai">竞彩足球</view>
      </scroll-view>
      <tip-dot text="覆盖 7 种主流福彩/体彩玩法；竞彩足球目前为玩法预览，尚未接入赛事数据。各玩法的奖级与奖金以福彩/体彩官方最新公布为准" />
    </view>

    <view class="card">
      <view class="rowline">
        <text class="l">彩种 · 单价</text>
        <text class="r">{{ curGame ? `${curGame.name} · ${price} 元/注` : '—' }}</text>
      </view>
      <view class="rowline">
        <text class="l">开奖日</text>
        <text class="r">{{ drawDaysText }}</text>
      </view>
      <view class="rowline">
        <view class="l-row">
          <text class="l">模拟期号</text>
          <tip-dot text="按开奖日历从年初推算期号，未包含休市等官方调整，仅作模拟展示" />
        </view>
        <text class="r">第 {{ issueText }} 期</text>
      </view>
      <view v-if="countdownText" class="draw-strip">
        <text class="draw-strip-text">{{ countdownText }}</text>
        <text class="draw-strip-note">模拟推算</text>
      </view>

      <!-- 模式分段 -->
      <view class="mode-row">
        <view class="seg">
          <view v-for="m in modes" :key="m.key" class="seg-item" :class="{ on: mode === m.key }" @click="switchMode(m.key)">{{ m.label }}</view>
        </view>
        <tip-dot text="机选：完全随机生成；策略：按分布形态约束生成；推演：按历史开奖频率与遗漏生成；自选：手动点选或录入号码。所有方式都不改变中奖概率" />
      </view>

      <!-- 数字型玩法 -->
      <block v-if="playNames.length">
        <view class="strat-title">
          <text>玩法</text>
          <tip-dot :text="playTip" />
        </view>
        <view class="chips play-chips">
          <view v-for="p in playNames" :key="p" class="schip" :class="{ on: play === p }" @click="switchPlay(p)">{{ p }}</view>
        </view>
      </block>

      <!-- 注数与模拟投注金额 -->
      <view class="amount-bar">
        <text class="amount-l">共 {{ displayCount }} 注</text>
        <text class="amount-r">模拟投注 ¥{{ displayCost }} 元</text>
      </view>

      <!-- 机选 -->
      <block v-if="mode === 'random'">
        <view class="stepper">
          <text class="lbl">注数</text>
          <view class="num">
            <view class="num-btn" @click="stepCount(-1)">−</view>
            <text class="num-val">{{ count }}</text>
            <view class="num-btn" @click="stepCount(1)">+</view>
          </view>
        </view>
        <view class="quick-row">
          <view v-for="c in quickCounts" :key="c" class="quick-chip" :class="{ on: count === c }" @click="count = c">{{ c }} 注</view>
        </view>
        <view class="btn-primary" @click="gen('random')">生成号码</view>
      </block>

      <!-- 策略 -->
      <block v-if="mode === 'strategy'">
        <view class="warnline">策略只改变号码分布形态，不改变中奖概率</view>
        <view class="strat-title">
          <text>策略组合</text>
          <tip-dot text="冷热号：偏好近期高频号码；区间均衡：各号码区间数量均匀；奇偶约束：限制奇偶比；和值约束：控制号码和值区间；连号控制：限制相邻连号数量" />
        </view>
        <view class="chips">
          <view
            v-for="(s, i) in stratChips"
            :key="s.name"
            class="schip"
            :class="{ on: s.on }"
            @click="s.on = !s.on"
          >{{ s.name }}</view>
        </view>
        <view class="stepper">
          <text class="lbl">注数</text>
          <view class="num">
            <view class="num-btn" @click="stepCount(-1)">−</view>
            <text class="num-val">{{ count }}</text>
            <view class="num-btn" @click="stepCount(1)">+</view>
          </view>
        </view>
        <view class="btn-primary" @click="gen('strategy')">按策略生成</view>
      </block>

      <!-- 历史推演 -->
      <block v-if="mode === 'history'">
        <view class="warnline">依据历史开奖的频率与遗漏推演号码，不改变中奖概率</view>
        <view class="strat-title">
          <text>参考范围</text>
          <tip-dot text="取最近 N 期开奖统计：近期高频号适当加权，长期未出号适当补权，仅在分布上做倾向" />
        </view>
        <view class="quick-row">
          <view
            v-for="p in historyOptions"
            :key="p"
            class="quick-chip"
            :class="{ on: historyPeriods === p }"
            @click="historyPeriods = p"
          >近 {{ p }} 期</view>
        </view>
        <view class="stepper">
          <text class="lbl">注数</text>
          <view class="num">
            <view class="num-btn" @click="stepCount(-1)">−</view>
            <text class="num-val">{{ count }}</text>
            <view class="num-btn" @click="stepCount(1)">+</view>
          </view>
        </view>
        <view class="btn-primary" @click="gen('history')">按历史推演生成</view>
      </block>

      <!-- 自选 -->
      <block v-if="mode === 'manual'">
        <!-- 乐透型：复式开关 -->
        <view v-if="isLotto" class="rowline">
          <view class="l-row">
            <text class="l">复式投注</text>
            <tip-dot text="每区多选号码，按组合展开为多注单式票；展开注数上限 100 注，超出请减少选号" />
          </view>
          <switch :checked="compound" color="#E03C31" @change="onCompoundChange" />
        </view>

        <block v-if="curGame && !curGame.digits">
          <view v-for="z in curGame.zones" :key="z.name" class="zone-block">
            <view class="zone-title">
              <text>{{ zoneTitle(z) }}</text>
              <tip-dot :text="compound ? `${z.label}：从 1-${z.pool_size} 中至少选 ${z.pick} 个号码，系统按组合展开` : `${z.label}：从 1-${z.pool_size} 中选 ${z.pick} 个号码`" />
            </view>
            <view class="pickgrid">
              <view
                v-for="n in z.pool_size"
                :key="n"
                class="pcell"
                :class="[{ on: inManual(z.name, n) }, zoneColor(z.name)]"
                :disabled="!compound && manualCount(z.name) >= z.pick && !inManual(z.name, n)"
                @click="toggleManual(z.name, n)"
              >{{ n }}</view>
            </view>
          </view>
        </block>
        <block v-if="curGame && curGame.digits">
          <view class="zone-title">开奖号码（{{ curGame.digits }} 位数字）</view>
          <input class="digit-input" v-model="digitsInput" :maxlength="curGame.digits" type="number" :placeholder="`如 ${curGame.digits === 3 ? '007' : '12345'}`" />
          <text v-if="playHint" class="digit-hint">{{ playHint }}</text>
        </block>
        <view class="btn-primary" style="margin-top:20rpx" @click="submitManual">确认号码</view>
      </block>

      <!-- 大乐透奖池联动 -->
      <view v-if="curGame && curGame.pool_high" class="rowline pool-row">
        <view class="l-row">
          <text class="l">奖池 ≥ 8 亿联动</text>
          <tip-dot text="模拟固定奖上浮（三至七等奖），浮动奖仍按默认值计算" />
        </view>
        <switch :checked="poolHigh" color="#E03C31" @change="onPoolHighChange" />
      </view>
    </view>

    <!-- 我的号码 -->
    <view v-if="tickets.length" class="card">
      <view class="card-title">
        <text>我的号码</text>
        <view class="ticket-sum">
          <text v-if="isLogged && !saving" class="save-btn" @click="saveOnlyPick">保存</text>
          <text v-if="isLogged && saving" class="save-btn dim">保存中…</text>
          <text>{{ tickets.length }} 注</text>
          <text class="sum-sep">·</text>
          <text>¥{{ ticketsCost }}</text>
        </view>
      </view>
      <view v-if="basis && basis.hot && basis.hot.length" class="basis-line">
        <text>近 {{ basis.periods }} 期 · {{ basis.label }}热号 {{ hotText }}</text>
        <text v-if="basis.overdue && basis.overdue.length" class="basis-sub">遗漏 {{ overdueText }}</text>
      </view>
      <view v-for="(t, i) in visibleTickets" :key="i" class="ticket-row">
        <text class="ticket-idx">第 {{ i + 1 }} 注</text>
        <view class="balls">
          <template v-for="(z, zi) in curGame.zones" :key="zi">
            <ball v-for="n in t.zones[z.name]" :key="n" :num="n" :color="zoneColor(z.name)" size="sm" />
            <view v-if="zi < curGame.zones.length - 1" class="plus">+</view>
          </template>
          <template v-if="curGame.digits">
            <ball
              v-for="(ch, ci) in (t.digits || '')"
              :key="`d-${ci}`"
              :num="ch"
              :color="zoneColor(curGame.zones[0] ? curGame.zones[0].name : 'main')"
              size="sm"
              :pad="false"
            />
          </template>
        </view>
      </view>
      <text v-if="tickets.length > 20" class="more-note">共 {{ tickets.length }} 注，仅展示前 20 注</text>
    </view>

    <!-- 开奖 / 对奖 -->
    <view v-if="tickets.length" class="btn-primary draw-btn" :class="{ disabled: drawing }" @click="doDraw">
      {{ drawing ? '开奖中…' : '模拟开奖并判定' }}
    </view>

    <view v-if="draw" class="card">
      <view class="card-title"><text>开奖号码</text></view>
      <view class="drawbox">
        <text class="drawlab">{{ curGame.name }} · 本期模拟开奖{{ play ? ` · ${play}` : '' }}</text>
        <view class="balls">
          <template v-for="(z, zi) in curGame.zones" :key="zi">
            <ball v-for="n in draw.zones[z.name]" :key="n" :num="n" :color="zoneColor(z.name)" size="sm" />
            <view v-if="zi < curGame.zones.length - 1" class="plus">+</view>
          </template>
          <ball v-if="draw.special" :num="draw.special" color="gold" size="sm" />
          <template v-if="curGame.digits">
            <ball
              v-for="(ch, ci) in (draw.digits || '')"
              :key="`draw-d-${ci}`"
              :num="ch"
              :color="zoneColor(curGame.zones[0] ? curGame.zones[0].name : 'main')"
              size="sm"
              :pad="false"
            />
          </template>
        </view>
      </view>
    </view>

    <view v-if="results.length" class="card">
      <view class="card-title"><text>对奖结果</text></view>
      <view class="draw-sum">
        <view class="ds-item">
          <text class="ds-lab">投入</text>
          <text class="ds-val">¥{{ summary.cost }}</text>
        </view>
        <view class="ds-item">
          <text class="ds-lab">中奖</text>
          <text class="ds-val win">¥{{ summary.win.toLocaleString() }}</text>
        </view>
        <view class="ds-item">
          <text class="ds-lab">净盈亏</text>
          <text class="ds-val" :class="summary.profit >= 0 ? 'win' : 'lose'">{{ summary.profit >= 0 ? '+' : '' }}{{ summary.profit.toLocaleString() }}</text>
        </view>
      </view>
      <view v-for="r in visibleResults" :key="r.index" class="res-item">
        <view class="res-head">
          <text class="res-idx">第 {{ r.index + 1 }} 注</text>
          <view class="res-badge" :class="r.won ? 'gold' : 'lose'">
            <text>{{ r.won ? r.level : '未中奖' }}</text>
            <tip-dot v-if="r.won" :text="`命中条件：${levelCondition(r.level)}`" />
          </view>
          <text class="res-amt" :class="r.won ? 'win' : 'lose'">{{ r.won ? '¥' + r.money.toLocaleString() : '—' }}</text>
        </view>
        <view class="res-balls">
          <template v-for="(z, zi) in curGame.zones" :key="zi">
            <ball v-for="n in ticketOf(r).zones[z.name]" :key="`${zi}-${n}`" :num="n" :color="zoneColor(z.name)" size="sm" :hit="isHit(r, z.name, n)" />
            <view v-if="zi < curGame.zones.length - 1" class="plus">+</view>
          </template>
          <template v-if="curGame.digits">
            <ball
              v-for="(ch, ci) in ticketOf(r).digits"
              :key="`d-${ci}`"
              :num="ch"
              :color="zoneColor(curGame.zones[0] ? curGame.zones[0].name : 'main')"
              size="sm"
              :pad="false"
              :hit="r.digit_hits && r.digit_hits[ci]"
            />
          </template>
        </view>
        <text class="res-hits">{{ hitsText(r) }}</text>
      </view>
      <text v-if="results.length > 20" class="more-note">共 {{ results.length }} 注，仅展示前 20 注</text>
    </view>

    <ai-fab />
  </view>
</template>

<script>
import Ball from '@/components/ball.vue'
import TipDot from '@/components/tip-dot.vue'
import AiFab from '@/components/ai-fab.vue'
import { api } from '@/api/index'
import { getSessionId, getToken } from '@/api/request'
import { FALLBACK_GAMES, getCurrentGameCode, setCurrentGameCode, loadGames, gameIndexByCode } from '@/store/game'

export default {
  name: 'Pick',
  components: { Ball, TipDot, AiFab },
  data() {
    return {
      games: FALLBACK_GAMES,
      curCode: getCurrentGameCode(),
      curGame: null,
      mode: 'random',
      count: 1,
      tickets: [],
      ticketsCost: 0,
      draw: null,
      results: [],
      summary: { cost: 0, win: 0, profit: 0 },
      drawing: false,
      saving: false,
      isLogged: !!getToken(),
      play: '',
      compound: false,
      poolHigh: false,
      digitsInput: '',
      manualSel: {},
      quickCounts: [1, 5, 10, 20],
      historyOptions: [30, 60, 100],
      historyPeriods: 60,
      basis: null,
      stratChips: [
        { name: '冷热号', on: false },
        { name: '区间均衡', on: true },
        { name: '奇偶约束', on: false },
        { name: '和值约束', on: false },
        { name: '连号控制', on: false },
      ],
      modesAll: [
        { key: 'random', label: '机选' },
        { key: 'strategy', label: '策略' },
        { key: 'history', label: '推演' },
        { key: 'manual', label: '自选' },
      ],
    }
  },
  computed: {
    modes() {
      // 数字型彩种没有号码分布策略，隐藏策略模式
      if (this.curGame && this.curGame.digits) {
        return this.modesAll.filter((m) => m.key !== 'strategy')
      }
      return this.modesAll
    },
    price() {
      return this.curGame ? this.curGame.price : 2
    },
    playNames() {
      return (this.curGame && this.curGame.play_names) || []
    },
    isLotto() {
      return this.curGame && this.curGame.game_type === 'lotto'
    },
    displayCount() {
      if (!this.curGame) return 0
      if (this.mode === 'manual') return this.isLotto && this.compound ? this.comboCount : 1
      return this.count
    },
    displayCost() {
      return this.displayCount * this.price
    },
    comboCount() {
      const g = this.curGame
      if (!g || g.digits) return 1
      let total = 1
      for (const z of g.zones) {
        const n = this.manualCount(z.name)
        if (n < z.pick) return 0
        total *= this.comb(n, z.pick)
      }
      return total
    },
    drawDaysText() {
      const days = (this.curGame && this.curGame.draw_days) || []
      if (!days.length) return '每日开奖'
      const names = ['一', '二', '三', '四', '五', '六', '日']
      return '每周' + days.map((d) => names[d]).join('、') + ' 开奖'
    },
    // 下一期开奖日期（本地推算；draw_days 索引 0=周一…6=周日，每日开奖为空数组）
    nextDraw() {
      const days = (this.curGame && this.curGame.draw_days) || []
      const now = new Date()
      const toIdx = (d) => (d.getDay() + 6) % 7
      for (let i = 0; i < 8; i++) {
        const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() + i)
        if (days.length && !days.includes(toIdx(d))) continue
        // 开奖日当晚 21:00 后算作下一期
        if (i === 0 && now.getHours() >= 21) continue
        return d
      }
      return null
    },
    // 模拟期号：年份 + 年内第 N 个开奖日（三位序号，与官方格式一致的推算口径）
    issueText() {
      const d = this.nextDraw
      if (!d || !this.curGame) return '——'
      const days = this.curGame.draw_days || []
      const toIdx = (date) => (date.getDay() + 6) % 7
      let n = 0
      const cur = new Date(d.getFullYear(), 0, 1)
      while (cur <= d) {
        if (!days.length || days.includes(toIdx(cur))) n++
        cur.setDate(cur.getDate() + 1)
      }
      return `${d.getFullYear()}${String(n).padStart(3, '0')}`
    },
    countdownText() {
      const d = this.nextDraw
      if (!d) return ''
      const now = new Date()
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
      const diff = Math.round((d - today) / 86400000)
      const week = ['日', '一', '二', '三', '四', '五', '六'][d.getDay()]
      const dateStr = `${d.getMonth() + 1}月${d.getDate()}日 周${week}`
      if (diff === 0) return `今晚开奖 · ${dateStr}`
      if (diff === 1) return `明天开奖 · ${dateStr}`
      return `${diff} 天后开奖 · ${dateStr}`
    },
    playHint() {
      if (this.play === '组选3') return '组选3：三位中含一组对子，如 112（顺序不限）'
      if (this.play === '组选6') return '组选6：三位各不相同，如 123（顺序不限）'
      if (this.play === '直选') return '直选：与开奖号码按位完全一致'
      return ''
    },
    playTip() {
      return '直选按位一致；组选3 需含一组对子；组选6 需三位各不相同。玩法只影响对奖与奖金，不改变单注命中概率'
    },
    visibleTickets() {
      return this.tickets.slice(0, 20)
    },
    visibleResults() {
      return this.results.slice(0, 20)
    },
    hotText() {
      if (!this.basis || !this.basis.hot) return ''
      return this.basis.hot.map((n) => String(n).padStart(2, '0')).join(' ')
    },
    overdueText() {
      if (!this.basis || !this.basis.overdue) return ''
      return this.basis.overdue.map((n) => String(n).padStart(2, '0')).join(' ')
    },
  },
  onLoad() {
    this.loadGameList()
  },
  onShow() {
    const code = getCurrentGameCode()
    if (code !== this.curCode) this.switchGame(code)
    this.isLogged = !!getToken()
  },
  methods: {
    async loadGameList() {
      this.games = await loadGames()
      if (gameIndexByCode(this.games, this.curCode) === 0 && this.games[0]) {
        this.curCode = this.games[0].code
      }
      this.applyGame()
    },
    switchGame(code) {
      this.curCode = code
      setCurrentGameCode(code)
      this.resetResult()
      this.manualSel = {}
      this.digitsInput = ''
      this.compound = false
      this.applyGame()
    },
    goJingcai() {
      uni.navigateTo({ url: '/pages/jingcai/jingcai' })
    },
    applyGame() {
      const g = this.games.find((x) => x.code === this.curCode)
      this.curGame = g
        ? { ...g, digits: g.digits || 0, zones: g.zones || [] }
        : null
      this.play = this.playNames.length ? this.playNames[0] : ''
      this.poolHigh = !!(this.curGame && this.curGame.pool_high)
      if (this.curGame && this.curGame.digits && this.mode === 'strategy') this.mode = 'random'
    },
    switchMode(m) {
      this.mode = m
      this.resetResult()
    },
    switchPlay(p) {
      this.play = p
      this.resetResult()
    },
    resetResult() {
      this.tickets = []
      this.ticketsCost = 0
      this.basis = null
      this.draw = null
      this.results = []
      this.summary = { cost: 0, win: 0, profit: 0 }
    },
    onCompoundChange(e) {
      this.compound = e.detail.value
      this.resetResult()
    },
    onPoolHighChange(e) {
      this.poolHigh = e.detail.value
      this.resetResult()
    },
    stepCount(delta) {
      this.count = Math.min(100, Math.max(1, this.count + delta))
    },
    zoneColor(name) {
      if (!this.curGame) return 'red'
      const z = this.curGame.zones.find((x) => x.name === name)
      if (this.curCode === 'ssq') return z && z.name === 'blue' ? 'blue' : 'red'
      if (this.curCode === 'dlt') return z && z.name === 'front' ? 'orange' : 'blue'
      if (this.curCode === 'qlc') return 'blue'
      if (this.curCode === 'kl8') return 'red'
      if (this.curCode === 'pl5') return 'blue'
      if (this.curCode === 'pl3') return 'orange'
      return 'red'
    },
    zoneTitle(z) {
      const count = this.manualCount(z.name)
      const need = this.compound ? `≥${z.pick}` : `${z.pick}`
      return `${z.label}（1-${z.pool_size} 选 ${need}，已选 ${count}）`
    },
    manualCount(zoneName) {
      return (this.manualSel[zoneName] || []).length
    },
    inManual(zoneName, n) {
      return (this.manualSel[zoneName] || []).includes(n)
    },
    toggleManual(zoneName, n) {
      const arr = this.manualSel[zoneName] || []
      const idx = arr.indexOf(n)
      if (idx >= 0) {
        arr.splice(idx, 1)
      } else {
        const z = this.curGame.zones.find((x) => x.name === zoneName)
        if (!this.compound && arr.length >= z.pick) return
        arr.push(n)
      }
      this.$set(this.manualSel, zoneName, [...arr].sort((a, b) => a - b))
    },
    comb(n, k) {
      if (k > n) return 0
      let r = 1
      for (let i = 1; i <= k; i++) r = (r * (n - k + i)) / i
      return Math.round(r)
    },
    async gen(mode) {
      try {
        let strategy = {}
        if (mode === 'strategy') strategy = await this.buildStrategy()
        const res = await api.generatePicks({
          game_code: this.curCode,
          mode,
          count: this.count,
          strategy,
          play: this.curGame.digits ? this.play : '',
          history_periods: mode === 'history' ? this.historyPeriods : 60,
        })
        this.applyPickResult(res)
      } catch (err) {
        uni.showToast({ title: err.message, icon: 'none' })
      }
    },
    applyPickResult(res) {
      this.tickets = res.tickets
      this.ticketsCost = res.cost != null ? res.cost : res.tickets.length * this.price
      this.basis = res.basis || null
      this.draw = null
      this.results = []
      this.summary = { cost: 0, win: 0, profit: 0 }
    },
    async buildStrategy() {
      const on = this.stratChips.filter((s) => s.on).map((s) => s.name)
      const strategy = {}
      const g = this.curGame
      const splitCounts = (pick) => {
        const base = Math.floor(pick / 3)
        const rem = pick % 3
        return [base + (rem > 0 ? 1 : 0), base + (rem > 1 ? 1 : 0), base]
      }
      if (on.includes('区间均衡')) {
        strategy.zone_split = {}
        g.zones.forEach((z) => (strategy.zone_split[z.name] = splitCounts(z.pick)))
      }
      if (on.includes('奇偶约束')) {
        strategy.odd_even = {}
        g.zones.forEach((z) => (strategy.odd_even[z.name] = Math.floor(z.pick / 2)))
      }
      if (on.includes('和值约束') && g.zones.length) {
        const z = g.zones[0]
        const minSum = (z.pick * (z.pick + 1)) / 2
        const maxSum = (z.pick * (2 * z.pool_size - z.pick + 1)) / 2
        strategy.sum_range = {
          zone: z.name,
          min: Math.floor(minSum + (maxSum - minSum) * 0.2),
          max: Math.ceil(maxSum - (maxSum - minSum) * 0.2),
        }
      }
      if (on.includes('连号控制')) strategy.consecutive = 'forbid'
      if (on.includes('冷热号')) {
        try {
          const hc = await api.hotCold(this.curCode, 60)
          const z0 = hc.zones && hc.zones[Object.keys(hc.zones)[0]]
          if (z0) {
            strategy.hot_cold = { weights: {} }
            z0.frequency.forEach(([n, c]) => {
              strategy.hot_cold.weights[n] = 1 + c / 10
            })
          }
        } catch (e) {
          uni.showToast({ title: '冷热号数据缺失，已忽略该策略', icon: 'none' })
        }
      }
      return strategy
    },
    async submitManual() {
      const g = this.curGame
      if (g.digits) {
        if (!g.digits || this.digitsInput.length !== g.digits) {
          uni.showToast({ title: `请输入 ${g.digits} 位数字`, icon: 'none' })
          return
        }
        const uniq = new Set(this.digitsInput).size
        if (this.play === '组选3' && uniq !== 2) {
          uni.showToast({ title: '组选3 需含一组对子，如 112', icon: 'none' })
          return
        }
        if (this.play === '组选6' && uniq !== 3) {
          uni.showToast({ title: '组选6 需三位各不相同，如 123', icon: 'none' })
          return
        }
      } else if (this.compound) {
        if (this.comboCount === 0) {
          uni.showToast({ title: `每区至少选够 ${g.zones[0].pick} 个号码`, icon: 'none' })
          return
        }
        if (this.comboCount > 100) {
          uni.showToast({ title: `复式展开 ${this.comboCount} 注，超过 100 注上限`, icon: 'none' })
          return
        }
      }
      try {
        let res
        if (g.digits) {
          res = await api.generatePicks({
            game_code: this.curCode,
            mode: 'manual',
            digits: this.digitsInput,
            play: this.play,
          })
        } else {
          const zoneInputs = {}
          g.zones.forEach((z) => {
            zoneInputs[z.name] = (this.manualSel[z.name] || []).join(' ')
          })
          res = await api.generatePicks({
            game_code: this.curCode,
            mode: 'manual',
            zone_inputs: zoneInputs,
            compound: this.compound,
          })
        }
        this.applyPickResult(res)
      } catch (err) {
        uni.showToast({ title: err.message, icon: 'none' })
      }
    },
    async doDraw() {
      if (this.drawing) return
      this.drawing = true
      try {
        const res = await api.simulateDraw({
          game_code: this.curCode,
          session_id: getSessionId(),
          tickets: this.tickets,
          play: this.curGame.digits ? this.play : null,
          pool_high: this.poolHigh,
        })
        this.draw = res.draw
        this.results = res.results
        this.summary = { cost: res.cost, win: res.win, profit: res.profit }
        this.saveRecord(res)
        if (this.isLogged) this.savePickServer(res)
      } catch (err) {
        uni.showToast({ title: err.message, icon: 'none' })
      } finally {
        this.drawing = false
      }
    },
    saveRecord(res) {
      const list = uni.getStorageSync('sg_records') || []
      const shown = this.tickets.slice(0, 3).map((t) => t.display || t.digits || '')
      const nums = shown.join(' / ') + (this.tickets.length > 3 ? ` 等 ${this.tickets.length} 注` : '')
      list.unshift({
        game: this.curGame.name,
        code: this.curCode,
        nums,
        result: res.win > 0 ? `中奖 ${res.win.toLocaleString()} 元` : '未中奖',
        // 供「我的」页汇总：注数 / 投入 / 中奖金额
        count: this.tickets.length,
        cost: res.cost,
        win: res.win,
        time: new Date().toLocaleString(),
      })
      uni.setStorageSync('sg_records', list.slice(0, 20))
    },
    /** 登录用户把当前选号保存到云端（drawRes 为空表示仅保存选号，未开奖） */
    async savePickServer(drawRes) {
      try {
        await api.savePick({
          game_code: this.curCode,
          mode: this.mode,
          play: this.curGame && this.curGame.digits ? this.play : '',
          count: this.tickets.length,
          cost: drawRes ? drawRes.cost : this.ticketsCost,
          tickets: this.tickets,
          draw: drawRes ? drawRes.draw : null,
          win: drawRes ? drawRes.win : 0,
        })
        uni.showToast({ title: '已保存到我的记录', icon: 'success' })
      } catch (err) {
        this.isLogged = !!getToken()
        uni.showToast({ title: err.message, icon: 'none' })
      }
    },
    /** 「我的号码」卡片上的保存按钮：仅保存当前选号 */
    saveOnlyPick() {
      if (this.saving) return
      this.saving = true
      this.savePickServer(null).finally(() => {
        this.saving = false
      })
    },
    ticketOf(r) {
      return this.tickets[r.index] || { zones: {}, digits: '' }
    },
    isHit(r, zoneName, n) {
      return (r.hit_numbers && r.hit_numbers[zoneName] ? r.hit_numbers[zoneName] : []).includes(n)
    },
    hitsText(r) {
      if (this.curGame.digits) {
        const hit = (r.digit_hits || []).filter(Boolean).length
        return `逐位命中 ${hit}/${this.curGame.digits} 位`
      }
      return this.curGame.zones
        .map((z) => `${z.label} ${r.hits && r.hits[z.name] != null ? r.hits[z.name] : 0}/${z.pick}`)
        .join(' · ')
    },
    levelCondition(levelName) {
      const g = this.curGame
      if (!g) return ''
      const lv = (g.prize_levels || []).find((l) => l.name === levelName)
      return lv ? lv.condition : ''
    },
  },
}
</script>

<style scoped lang="scss">
@import '@/uni.scss';

.nav {
  display: flex;
  flex-direction: column;
  padding: 24rpx 0 8rpx;
}
.nav-title {
  display: flex;
  align-items: center;
  gap: 16rpx;
  font-size: 38rpx;
  font-weight: 600;
}
.nav-ball {
  width: 44rpx;
  height: 44rpx;
  border-radius: 50%;
  background: $sg-primary;
  color: #fff;
  font-size: 24rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}
.nav-sub {
  font-size: 24rpx;
  color: $sg-t3;
  margin-top: 4rpx;
}
.games-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 24rpx;
}
.games {
  flex: 1;
  white-space: nowrap;
}
.chip {
  display: inline-flex;
  padding: 14rpx 30rpx;
  border-radius: 999rpx;
  background: #fff;
  border: 2rpx solid $sg-line;
  font-size: 26rpx;
  color: $sg-t2;
  margin-right: 14rpx;
}
.chip.on {
  background: $sg-primary;
  border-color: $sg-primary;
  color: #fff;
  font-weight: 600;
}
.chip.planned {
  border-style: dashed;
  color: $sg-t3;
  background: transparent;
}
.mode-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin: 24rpx 0 8rpx;
}
.play-chips {
  margin-bottom: 8rpx;
}
.amount-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #F7F8FB;
  border-radius: $sg-radius-inner;
  padding: 16rpx 24rpx;
  margin: 20rpx 0;
}
.amount-l {
  font-size: 26rpx;
  color: $sg-t2;
}
.amount-r {
  font-size: 28rpx;
  font-weight: 700;
  color: $sg-primary;
}
.stepper {
  display: flex;
  align-items: center;
  margin-bottom: 20rpx;
}
.lbl {
  font-size: 28rpx;
  color: $sg-t2;
}
.num {
  display: flex;
  align-items: center;
  gap: 20rpx;
  margin-left: auto;
}
.num-btn {
  width: 60rpx;
  height: 60rpx;
  border-radius: 16rpx;
  border: 2rpx solid $sg-line;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32rpx;
}
.num-val {
  font-size: 32rpx;
  min-width: 48rpx;
  text-align: center;
  font-weight: 600;
}
.quick-row {
  display: flex;
  gap: 14rpx;
  margin-bottom: 24rpx;
}
.quick-chip {
  flex: 1;
  text-align: center;
  padding: 12rpx 0;
  border-radius: $sg-radius-inner;
  border: 2rpx solid $sg-line;
  background: #fff;
  font-size: 24rpx;
  color: $sg-t2;
}
.quick-chip.on {
  border-color: $sg-primary;
  background: #FFF1F0;
  color: $sg-primary;
  font-weight: 600;
}
.warnline {
  font-size: 22rpx;
  color: #AD6800;
  background: #FFF7E6;
  padding: 12rpx 20rpx;
  border-radius: 16rpx;
  margin-bottom: 24rpx;
}
/* 下期开奖倒计时条 */
.draw-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #FDECEA;
  border-radius: 16rpx;
  padding: 14rpx 20rpx;
  margin: 4rpx 0 24rpx;
}
.draw-strip-text {
  font-size: 24rpx;
  color: #E03C31;
  font-weight: 600;
}
.draw-strip-note {
  font-size: 20rpx;
  color: #E03C31;
  opacity: 0.7;
}
.strat-title {
  display: flex;
  align-items: center;
  gap: 10rpx;
  font-size: 26rpx;
  color: $sg-t2;
  margin-bottom: 16rpx;
}
.l-row {
  display: flex;
  align-items: center;
  gap: 10rpx;
}
.zone-block {
  margin-bottom: 12rpx;
}
.zone-title {
  display: flex;
  align-items: center;
  gap: 10rpx;
  font-size: 26rpx;
  font-weight: 600;
  color: $sg-t2;
  margin: 16rpx 0;
}
.pickgrid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 12rpx;
}
.pcell {
  height: 76rpx;
  border-radius: 50%;
  border: 2rpx solid $sg-line;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26rpx;
  color: $sg-t2;
}
.pcell.on.red {
  background: $sg-primary;
  color: #fff;
  border-color: $sg-primary;
}
.pcell.on.blue {
  background: $sg-blue;
  color: #fff;
  border-color: $sg-blue;
}
.pcell.on.orange {
  background: $sg-orange;
  color: #fff;
  border-color: $sg-orange;
}
.pcell[disabled] {
  opacity: 0.35;
}
.digit-input {
  border: 2rpx solid $sg-line;
  border-radius: 20rpx;
  padding: 20rpx 28rpx;
  font-size: 32rpx;
  background: #fff;
}
.digit-hint {
  display: block;
  font-size: 22rpx;
  color: $sg-t3;
  margin-top: 12rpx;
}
.pool-row {
  margin-top: 8rpx;
}
.save-btn {
  font-size: 24rpx;
  color: $sg-primary;
  font-weight: 600;
  margin-right: 12rpx;
}
.save-btn.dim {
  color: $sg-t3;
}
.ticket-sum {
  display: flex;
  align-items: center;
  gap: 8rpx;
  font-size: 24rpx;
  font-weight: 600;
  color: $sg-primary;
}
.sum-sep {
  color: $sg-t3;
}
.basis-line {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
  margin: 8rpx 0 16rpx;
  padding: 12rpx 16rpx;
  background: #F7F8FB;
  border-radius: 12rpx;
  font-size: 22rpx;
  color: $sg-t2;
}
.basis-sub {
  color: $sg-t3;
}
.ticket-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 12rpx 0;
  border-bottom: 2rpx dashed $sg-line;
}
.ticket-row:last-child {
  border-bottom: none;
}
.ticket-idx {
  font-size: 22rpx;
  color: $sg-t3;
  width: 76rpx;
  flex: none;
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
.more-note {
  display: block;
  font-size: 22rpx;
  color: $sg-t3;
  text-align: center;
  margin-top: 16rpx;
}
.draw-btn {
  margin-bottom: 24rpx;
}
.draw-btn.disabled {
  opacity: 0.6;
}
.drawbox {
  background: linear-gradient(135deg, #2F3542, #1F2430);
  border-radius: 28rpx;
  padding: 32rpx;
  text-align: center;
}
.drawlab {
  font-size: 22rpx;
  color: #A8B0BF;
  display: block;
  margin-bottom: 20rpx;
}
.drawbox .balls {
  justify-content: center;
}
.draw-sum {
  display: flex;
  background: #F7F8FB;
  border-radius: $sg-radius-inner;
  padding: 20rpx 0;
  margin-bottom: 8rpx;
}
.ds-item {
  flex: 1;
  text-align: center;
}
.ds-lab {
  display: block;
  font-size: 22rpx;
  color: $sg-t3;
}
.ds-val {
  display: block;
  font-size: 30rpx;
  font-weight: 700;
  margin-top: 4rpx;
}
.ds-val.win {
  color: $sg-gold;
}
.ds-val.lose {
  color: $sg-t3;
}
.res-item {
  padding: 20rpx 0;
  border-bottom: 2rpx solid $sg-line;
}
.res-item:last-child {
  border-bottom: none;
}
.res-head {
  display: flex;
  align-items: center;
  gap: 12rpx;
}
.res-idx {
  font-size: 22rpx;
  color: $sg-t3;
}
.res-badge {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  font-size: 24rpx;
  padding: 6rpx 18rpx;
  border-radius: 999rpx;
}
.res-badge.gold {
  background: #FFF7E6;
  color: #AD6800;
  font-weight: 600;
}
.res-badge.lose {
  background: #F1F2F5;
  color: $sg-t3;
}
.res-amt {
  margin-left: auto;
  font-size: 28rpx;
  font-weight: 700;
}
.res-amt.win {
  color: $sg-gold;
}
.res-amt.lose {
  color: $sg-t3;
}
.res-balls {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  align-items: center;
  margin-top: 14rpx;
}
.res-hits {
  display: block;
  font-size: 22rpx;
  color: $sg-t3;
  margin-top: 8rpx;
}
</style>
