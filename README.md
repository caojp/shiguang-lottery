# 时光选彩 · 模拟彩票选号与开奖分析工具

纯模拟用途，不涉及任何真实投注。

覆盖国内主流福彩与体彩玩法：**双色球、福彩3D、快乐8、七乐彩、超级大乐透、排列3、排列5**。

## 功能

- 🎱 号码生成：随机机选 / 策略选号（冷热号、区间均衡、奇偶、和值、连号）/ 自选校验
- 🎰 模拟开奖：按彩种官方规则摇号（含七乐彩特别号、快乐8 二十码）
- 🏆 中奖判定：官方现行奖级与奖金（2026 口径），大乐透奖池 ≥ 8 亿联动
- 📊 策略回测：基于历史开奖，策略 vs 随机基线对照（平均命中 / 相似度 / 显著性），窗口聚合
- 🔥 冷热号分析：历史频率统计、热号/冷号 Top、频率热力图
- 🤖 AI 分析助手：Agent 编排层（LLM function calling + SSE），未配置 key 时降级为内置关键词路由
- 📁 历史数据管理：幂等拉取入库（ON CONFLICT DO UPDATE）、期号缺口检测、CSV 导入导出

## 技术架构（用户已定）

```
uni-app 多端前端（H5 / 微信小程序）
        │ HTTPS / SSE
FastAPI 后端
├── Agent 编排层（LLM function calling）       app/agent/
├── 确定性规则引擎（纯 Python）                app/engine/（复用 shiguang 核心）
├── 数据访问层（SQLAlchemy 2.0 Core）          app/models.py
└── PostgreSQL（JSONB 存号码、窗口函数聚合、generate_series 补期号）
    ├── games             彩种静态配置
    ├── draw_history      UNIQUE(game_code, issue)
    ├── bets              模拟投注（session_id 匿名，单式/复式）
    └── backtest_reports  回测报告（baseline 对照、is_significant、detail JSONB）
```

## 目录结构

```
shiguang-lottery/
├── PRD.md              # 项目需求文档（规则口径、验收标准）
├── docker-compose.yml  # PostgreSQL 16（本地开发）
├── docs/               # UI 设计规范 + 高保真原型
├── shiguang/           # 核心逻辑包（Streamlit 版与后端共用规则源）
├── app.py              # Streamlit 版入口（过渡产物，仍可运行）
├── backend/
│   ├── app/            # FastAPI 应用
│   │   ├── engine/     # 确定性规则引擎（config/engine/draw/prize/stats）
│   │   ├── services/   # 回测 / 冷热号分析
│   │   ├── agent/      # Agent 编排层（functions + orchestrator）
│   │   └── routers/    # games/picks/draws/backtests/analysis/data/agent
│   ├── alembic/        # 数据库迁移
│   ├── scripts/fetch_history.py  # 幂等历史拉取
│   └── tests/          # 引擎冒烟测试 + DB 集成测试
└── frontend/           # uni-app（vue3 + vite）
    └── src/
        ├── pages/      # pick / backtest / analysis / data / mine
        ├── components/ # ball（号码球）/ tip-dot（?浮窗）/ ai-fab（AI悬浮球）
        └── api/        # 接口封装
```

## 快速开始（后端）

前置：Docker（PostgreSQL 16）、Python 3.11+。

```bash
# 1. 启动 PostgreSQL（Docker Hub 不可达时可先 docker pull docker.m.daocloud.io/library/postgres:16-alpine 并打 tag）
docker compose up -d

# 2. 安装依赖
cd backend
pip install -r requirements.txt

# 3. 迁移建表
alembic upgrade head

# 4. 生成演示历史数据（幂等，可重复执行）
python scripts/fetch_history.py --seed-demo --demo-periods 60
python scripts/fetch_history.py --check-gaps   # 检查期号缺口

# 5. 启动 API（默认 http://127.0.0.1:8000）
uvicorn app.main:app --reload --port 8000
```

验证：浏览器打开 `http://127.0.0.1:8000/docs` 查看 Swagger；`/api/health`、`/api/games`、`/api/data/status` 可直接验证。

## 快速开始（前端 uni-app）

```bash
cd frontend
npm install
npm run dev:h5            # H5 开发（已配置 /api 代理到 127.0.0.1:8000）
npm run dev:mp-weixin     # 微信小程序（用微信开发者工具导入 dist/dev/mp-weixin）
npm run build:h5
```

> 小程序真机调试需将 `src/api/request.js` 的 `BASE_URL` 改为正式 HTTPS 域名，并在 `manifest.json` 的 `mp-weixin.appid` 填入小程序 AppID。

## 配置（backend/.env，参考 .env.example）

| 变量 | 说明 | 默认 |
| --- | --- | --- |
| DATABASE_URL | 运行时连接（asyncpg） | postgresql+asyncpg://shiguang:shiguang@localhost:5432/shiguang_lottery |
| DATABASE_URL_SYNC | 迁移用同步 URL（留空自动推导） | — |
| CORS_ORIGINS | 前端来源白名单 | http://localhost:5173,http://127.0.0.1:5173 |
| LLM_API_KEY / LLM_API_BASE / LLM_MODEL | Agent 层 OpenAI 兼容接口 | 留空则降级内置关键词路由 |
| DEFAULT_POOL_HIGH | 大乐透奖池 ≥ 8 亿联动默认开启 | true |

## API 一览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | /api/games | 7 彩种完整规则 |
| POST | /api/picks/generate | 机选 / 策略 / 自选生成号码 |
| POST | /api/draws/simulate | 模拟开奖 + 逐注对奖（写入 bets） |
| POST | /api/backtests/run | 策略回测（历史命中 + 基线对照，写入 backtest_reports） |
| GET | /api/backtests/reports | 回测历史 |
| GET | /api/analysis/hot-cold | 冷热号统计 |
| GET | /api/data/status | 数据源状态 + 期号缺口（窗口函数 LAG） |
| POST | /api/agent/chat | Agent 对话（SSE 流式） |
| POST | /api/agent/chat-sync | Agent 对话（非流式，小程序端用） |

## 运行测试

```bash
# 引擎冒烟测试（无需数据库）
cd backend && python -m pytest tests/ -q

# DB 集成测试（需先启动 PG 并迁移）
$env:RUN_DB_TESTS=1; python -m pytest tests/test_integration.py -v
```

## 规则口径说明

奖级与奖金依据中国福彩网、中国体彩网现行规则（2026 年口径），详见 `PRD.md` 附录 A。
超级大乐透为 2026 年 2 月起执行的 7 奖级新规（奖池 ≥ 8 亿时三至七等奖自动上调：5000→6666 / 300→380 / 150→200 / 15→18 / 5→7）。

## 已知边界

- **真实官网数据拉取**：`fetch_history.py` 已实现幂等入库与期号检查；真实抓取为扩展点（官网接口会改版），默认用 `--seed-demo` 生成演示历史。
- **竞彩**：依赖真实赛果，本期未开放。
- **Agent 层**：未配置 LLM key 时用内置关键词路由（选号/冷热/规则/回测），配置后走 function calling。
- **前端图表**：为跨端（H5/小程序）零依赖，走势与热力图用 CSS 实现；如需高级图表可在 H5 端引入 ECharts。
