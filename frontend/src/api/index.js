import { request, getSessionId } from './request'

export const api = {
  listGames: () => request({ url: '/api/games' }),
  getGame: (code) => request({ url: `/api/games/${code}` }),

  generatePicks: (payload) => request({ url: '/api/picks/generate', method: 'POST', data: payload }),

  simulateDraw: (payload) => request({ url: '/api/draws/simulate', method: 'POST', data: payload }),

  runBacktest: (payload) => request({ url: '/api/backtests/run', method: 'POST', data: payload }),
  listBacktests: () => request({ url: `/api/backtests/reports?session_id=${getSessionId()}` }),

  hotCold: (gameCode, periods = 60) => request({ url: `/api/analysis/hot-cold?game_code=${gameCode}&periods=${periods}` }),

  analysisStats: (gameCode, periods = 60) => request({ url: `/api/analysis/stats?game_code=${gameCode}&periods=${periods}` }),

  dataStatus: () => request({ url: '/api/data/status' }),

  dataHistory: (gameCode, limit = 10) => request({ url: `/api/data/history?game_code=${gameCode}&limit=${limit}` }),

  fetchData: (payload = {}) => request({ url: '/api/data/fetch', method: 'POST', data: payload, timeout: 60000 }),

  agentChat: (message) => request({ url: '/api/agent/chat-sync', method: 'POST', data: { message, session_id: getSessionId() }, timeout: 60000 }),
}
