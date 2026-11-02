import { api } from '@/api/index'

const GAME_CODE_KEY = 'sg_game_code'
const DEFAULT_GAME_CODE = 'ssq'

/* 后端未启动时的兜底彩种列表：与后端 config.py 保持一致的只读副本，
   保证选号页在离线预览时也能正确展示单价、号码池与开奖日历 */
const Z = (name, pool_size, pick, label) => ({ name, pool_size, pick, label })

export const FALLBACK_GAMES = [
  {
    code: 'ssq', name: '双色球', game_type: 'lotto', price: 2, digits: 0,
    play_names: [], draw_days: [1, 3, 6],
    zones: [Z('red', 33, 6, '红球'), Z('blue', 16, 1, '蓝球')],
  },
  {
    code: 'fc3d', name: '福彩3D', game_type: 'digit3', price: 2, digits: 3,
    play_names: ['直选', '组选3', '组选6'], draw_days: [], zones: [],
  },
  {
    code: 'kl8', name: '快乐8', game_type: 'keno', price: 2, digits: 0,
    play_names: [], draw_days: [], zones: [Z('main', 80, 10, '选十号码')],
  },
  {
    code: 'qlc', name: '七乐彩', game_type: 'lotto', price: 2, digits: 0,
    special: true, play_names: [], draw_days: [0, 2, 4],
    zones: [Z('base', 30, 7, '基本号')],
  },
  {
    code: 'dlt', name: '超级大乐透', game_type: 'lotto', price: 2, digits: 0,
    pool_high: true, play_names: [], draw_days: [0, 2, 5],
    zones: [Z('front', 35, 5, '前区'), Z('back', 12, 2, '后区')],
  },
  {
    code: 'pl3', name: '排列3', game_type: 'digit3', price: 2, digits: 3,
    play_names: ['直选', '组选3', '组选6'], draw_days: [], zones: [],
  },
  {
    code: 'pl5', name: '排列5', game_type: 'digit5', price: 2, digits: 5,
    play_names: [], draw_days: [], zones: [],
  },
]

/** 当前彩种在选号/分析/回测页之间共享 */
export function getCurrentGameCode() {
  return uni.getStorageSync(GAME_CODE_KEY) || DEFAULT_GAME_CODE
}

export function setCurrentGameCode(code) {
  if (code) uni.setStorageSync(GAME_CODE_KEY, code)
}

/** 拉取彩种列表，失败时回退到内置列表 */
export async function loadGames() {
  try {
    const games = await api.listGames()
    return games && games.length ? games : FALLBACK_GAMES
  } catch (err) {
    return FALLBACK_GAMES
  }
}

/** 按彩种代码取列表下标，找不到时回到 0 */
export function gameIndexByCode(games, code) {
  const idx = games.findIndex((g) => g.code === code)
  return idx >= 0 ? idx : 0
}
