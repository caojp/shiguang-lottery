"""时光选彩 · 模拟彩票选号与开奖分析工具（Streamlit 入口）。

运行方式：
    pip install -r requirements.txt
    streamlit run app.py

本工具为纯模拟用途，不涉及任何真实投注。
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

import pandas as pd
import streamlit as st

from shiguang.config import GAMES, GameConfig
from shiguang.engine import Ticket, generate_tickets, quick_pick, validate_ticket
from shiguang.draw import draw
from shiguang.prize import check
from shiguang.stats import simulate
from shiguang import history

BASE_DIR = Path(__file__).resolve().parent
DEMO_DIR = BASE_DIR / "data" / "demo_history"

st.set_page_config(page_title="时光选彩 · 模拟彩票", page_icon="🎯", layout="wide")


# ---------------------------------------------------------------- 演示历史数据

def ensure_demo_files() -> None:
    """为乐透型 / 基诺型彩种生成内置演示历史数据（CSV）。"""
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    for game in GAMES.values():
        if game.is_digit:
            continue
        fp = DEMO_DIR / f"{game.code}.csv"
        if not fp.exists():
            fp.write_text("\n".join(history.demo_csv_for(game)), encoding="utf-8")


def load_demo(game: GameConfig) -> list:
    ensure_demo_files()
    fp = DEMO_DIR / f"{game.code}.csv"
    return history.load_draws_csv(fp, game)


# ---------------------------------------------------------------- 策略构建

def _split_counts(pick: int, parts: int = 3) -> list[int]:
    base, rem = divmod(pick, parts)
    return [base + 1] * rem + [base] * (parts - rem)


def hot_cold_weights(game: GameConfig, mode: str, top_n: int) -> dict[int, float] | None:
    """由内置演示历史计算冷热号权重（热号优先 / 冷号优先）。"""
    draws = load_demo(game)
    if not draws:
        return None
    hc = history.hot_cold(draws, game, top_n=top_n)
    weights: dict[int, float] = {}
    for z in game.zones:
        hot = set(hc.get(z.name, {}).get("hot", []))
        cold = set(hc.get(z.name, {}).get("cold", []))
        for n in range(1, z.pool_size + 1):
            if mode == "hot":
                weights[n] = 2.5 if n in hot else (0.4 if n in cold else 1.0)
            else:
                weights[n] = 2.5 if n in cold else (0.4 if n in hot else 1.0)
    return weights


def build_strategy(game: GameConfig, ui: dict) -> dict:
    """根据界面策略选项构造策略字典（仅乐透 / 基诺适用）。"""
    strategy: dict = {}

    if ui.get("use_hot_cold"):
        mode = ui.get("hot_cold_mode", "hot")
        weights = hot_cold_weights(game, mode=mode, top_n=int(ui.get("hot_cold_top", 8)))
        if weights:
            strategy["hot_cold"] = {"mode": mode, "weights": weights}

    if ui.get("use_zone_split"):
        strategy["zone_split"] = {z.name: _split_counts(z.pick, 3) for z in game.zones}

    if ui.get("use_odd_even"):
        odd = int(ui.get("odd_count", game.zones[0].pick // 2))
        strategy["odd_even"] = {game.zones[0].name: odd}

    if ui.get("use_sum_range"):
        strategy["sum_range"] = {
            "zone": game.zones[0].name,
            "min": int(ui.get("sum_min", 0)),
            "max": int(ui.get("sum_max", game.zones[0].pool_size * game.zones[0].pick)),
        }

    strategy["consecutive"] = ui.get("consecutive")
    return strategy


# ---------------------------------------------------------------- 渲染辅助

def render_ticket_row(label: str, ticket: Ticket, game: GameConfig) -> None:
    cols = st.columns([1, 4])
    cols[0].markdown(f"**{label}**")
    cols[1].code(ticket.display(game), language=None)


def result_summary(r: PrizeResult) -> str:
    if not r.won or r.level is None:
        return "未中奖 😅"
    return f"中得 **{r.level.name}**（{r.level.condition}）· 奖金 **{r.money:,.0f} 元**"


def draw_level_table(game: GameConfig, pool_high: bool = False) -> pd.DataFrame:
    rows = []
    for lv in game.prize_levels:
        if lv.amount is not None:
            money = f"{lv.money(pool_high):,} 元"
            if lv.amount_high is not None:
                money = f"{lv.amount:,} / ≥8亿 {lv.amount_high:,} 元"
            kind = "固定"
        else:
            money = f"浮动（模拟 {lv.money(pool_high):,} 元/注）"
            kind = "浮动"
        rows.append({"奖级": lv.name, "中奖条件": lv.condition, "奖金": money, "类型": kind})
    return pd.DataFrame(rows)


def tickets_to_csv(game: GameConfig, tickets: list[Ticket]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    if game.is_digit:
        writer.writerow(["注号", "号码"])
        for i, t in enumerate(tickets, 1):
            writer.writerow([i, t.digits])
    else:
        header = ["注号"] + [z.label for z in game.zones]
        writer.writerow(header)
        for i, t in enumerate(tickets, 1):
            row = [i]
            for z in game.zones:
                row.append(" ".join(f"{n:02d}" for n in t.zones.get(z.name, ())))
            writer.writerow(row)
    return buf.getvalue().encode("utf-8-sig")


# ---------------------------------------------------------------- 主界面

st.markdown(
    "<h1 style='margin-bottom:0'>🎯 时光选彩</h1>"
    "<p style='color:#666;margin-top:0'>模拟彩票选号 · 开奖分析工具（双色球 / 福彩3D / 快乐8 / 七乐彩 / 大乐透 / 排列3 / 排列5）</p>",
    unsafe_allow_html=True,
)
st.warning("**免责声明**：本工具为学习 / 娱乐模拟用途，不涉及任何真实投注。彩票号码完全随机，任何选号策略都不改变中奖概率，请理性看待。")

# 侧边栏：彩种选择
game_options = {f"{g.name}（{g.code}）": g for g in GAMES.values()}
game_options["竞彩足球（暂不支持）"] = None
selected = st.sidebar.selectbox("选择彩种", list(game_options.keys()))
game: GameConfig | None = game_options[selected]

if game is None:
    st.info("竞彩足球 / 篮球依赖真实比赛赛果，无法用随机开奖模拟，本期暂不支持。请选择其他彩种。")
    st.stop()

if game.pool_high:
    pool_high = st.sidebar.checkbox("开启『奖池 ≥ 8 亿』固定奖上调（大乐透新规）", value=False)
else:
    pool_high = False

with st.sidebar.expander(f"📖 {game.name} 规则与奖级", expanded=False):
    st.dataframe(draw_level_table(game, pool_high), width="stretch", hide_index=True)

tab_play, tab_batch, tab_hot, tab_rules = st.tabs(["🎱 选号与开奖", "📊 批量模拟统计", "🔥 冷热号分析", "📖 全部彩种规则"])


# ================================================================ Tab1 选号与开奖
with tab_play:
    st.subheader(f"{game.name} · 选号")
    method = st.radio("选号方式", ["随机机选", "策略选号", "自选录入"], horizontal=True)

    ui: dict = {}
    tickets: list[Ticket] = []
    strategy: dict = {}
    manual: dict | None = None

    if method == "随机机选":
        count = st.number_input("机选注数", min_value=1, max_value=1000, value=1, step=1)
        if st.button("🎲 生成号码", type="primary"):
            tickets = quick_pick(game) if count == 1 else generate_tickets(game, count=int(count))

    elif method == "策略选号":
        if game.is_digit:
            st.warning("数字型玩法（3D / 排列3 / 排列5）为整体号码，不支持组合策略，请使用机选或自选。")
            count = st.number_input("机选注数", min_value=1, max_value=1000, value=1, step=1)
            if st.button("🎲 生成号码", type="primary"):
                tickets = quick_pick(game) if count == 1 else generate_tickets(game, count=int(count))
        else:
            st.caption("⚠️ 策略只改变号码分布形态，**不改变中奖概率**（每种号码组合概率恒等）。")
            with st.expander("🎛️ 策略选项", expanded=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    ui["use_hot_cold"] = st.checkbox("冷热号加权", value=False)
                    if ui["use_hot_cold"]:
                        ui["hot_cold_mode"] = st.selectbox("倾向", ["热号优先", "冷号优先"])
                        ui["hot_cold_top"] = st.slider("参与加权号码数", 3, 15, 8)
                    ui["use_zone_split"] = st.checkbox("区间均衡（均分3段）", value=False)
                with c2:
                    ui["use_odd_even"] = st.checkbox("奇偶约束", value=False)
                    if ui["use_odd_even"]:
                        ui["odd_count"] = st.slider("奇数个数", 0, game.zones[0].pick, game.zones[0].pick // 2)
                    ui["use_sum_range"] = st.checkbox("和值约束", value=False)
                    if ui["use_sum_range"]:
                        pool = game.zones[0].pool_size
                        ui["sum_min"] = st.number_input("和值下限", 1, pool * game.zones[0].pick, value=pool // 4)
                        ui["sum_max"] = st.number_input("和值上限", 1, pool * game.zones[0].pick, value=pool)
                with c3:
                    ui["consecutive"] = st.selectbox("连号控制", ["不限制", "禁止连号"])
                strategy = build_strategy(game, ui)
            count = st.number_input("策略选号注数", min_value=1, max_value=1000, value=1, step=1)
            if st.button("🎲 按策略生成", type="primary"):
                tickets = generate_tickets(game, count=int(count), strategy=strategy)

    else:  # 自选录入
        st.caption("手动输入号码：乐透型各区逗号 / 空格分隔；数字型直接输入 n 位数字。")
        zone_inputs: dict[str, str] = {}
        if game.is_digit:
            digits_text = st.text_input(
                "号码",
                placeholder="如 007 / 12345" + ("（3位）" if game.digits == 3 else "（5位）"),
            )
        else:
            cols = st.columns(len(game.zones))
            for z, col in zip(game.zones, cols):
                zone_inputs[z.name] = col.text_input(
                    f"{z.label}（1-{z.pool_size} 选 {z.pick}）",
                    placeholder="如 01,05,12",
                )
        if st.button("✅ 确认自选号码", type="primary"):
            ok, msg = validate_ticket(game, zone_inputs, digits_text)
            if not ok:
                st.error(msg)
            else:
                if game.is_digit:
                    tickets = [Ticket(game.code, digits=digits_text.strip())]
                else:
                    zones = {}
                    for z in game.zones:
                        from shiguang.engine import parse_numbers
                        zones[z.name] = tuple(sorted(parse_numbers(zone_inputs[z.name], z.pool_size)))
                    tickets = [Ticket(game.code, zones=zones)]

    if tickets:
        st.markdown("#### 我的号码")
        for i, t in enumerate(tickets, 1):
            render_ticket_row(f"第 {i} 注", t, game)

        if st.button("🎰 模拟开奖并判定", type="primary"):
            st.markdown("#### 开奖结果")
            draw_result = draw(game)
            st.success(f"**{game.name}开奖号码**：{draw_result.display(game)}")

            st.markdown("#### 对奖结果")
            for i, t in enumerate(tickets, 1):
                r = check(game, t, draw_result, pool_high=pool_high)
                cols = st.columns([3, 3, 3, 2])
                cols[0].write(f"第 {i} 注")
                cols[1].code(t.display(game), language=None)
                cols[2].write(result_summary(r))
                if r.won and r.level is not None:
                    cols[3].metric("奖金(元)", f"{r.money:,}")
                else:
                    cols[3].write("—")

            st.download_button(
                "⬇️ 导出选号记录 CSV",
                data=tickets_to_csv(game, tickets),
                file_name=f"{game.code}_tickets.csv",
                mime="text/csv",
            )


# ================================================================ Tab2 批量模拟
with tab_batch:
    st.subheader("📊 批量模拟与统计")
    st.caption("自动生成 N 注 → 模拟开奖 → 逐注对奖 → 汇总统计。用于直观展示『长期随机购彩』的期望结果。")
    b1, b2, b3 = st.columns(3)
    with b1:
        batch_count = st.number_input("投注注数", min_value=1, max_value=50000, value=1000, step=100)
    with b2:
        use_strategy = st.checkbox("批量使用策略选号", value=False)
        if use_strategy and not game.is_digit:
            bm = st.selectbox("倾向", ["热号优先", "冷号优先"])
            strategy = build_strategy(game, {"use_hot_cold": True, "hot_cold_mode": bm, "hot_cold_top": 8, "consecutive": "不限制"})
        else:
            strategy = {}
    with b3:
        if game.is_digit and game.play_names:
            play = st.selectbox("投注玩法", list(game.play_names))
        else:
            play = None

    if st.button("🚀 运行批量模拟", type="primary"):
        with st.spinner(f"正在模拟 {int(batch_count):,} 注……"):
            report = simulate(game, count=int(batch_count), strategy=strategy or None, pool_high=pool_high, play=play)

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("总投入（元）", f"{report.cost:,}")
        m2.metric("总奖金（元）", f"{report.win:,}")
        m3.metric("盈亏（元）", f"{report.profit:+,}")
        m4.metric("回报率", f"{report.roi*100:.2f}%")
        m5.metric("中奖注数", f"{report.hit_count}/{report.count}")

        st.info(f"本期开奖号码：**{report.draw_display}**")

        if report.level_counts:
            dist = pd.DataFrame(
                [{"奖级": k, "中奖注数": v, "奖金合计(元)": report.win_money_by_level[k]} for k, v in report.level_counts.items()]
            )
            st.markdown("#### 奖级分布")
            st.dataframe(dist, width="stretch", hide_index=True)
        else:
            st.warning("本次模拟无任何中奖——这正是长期随机购彩的真实写照（多数情况下血本无归）。")

        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(["指标", "数值"])
        writer.writerow(["彩种", game.name])
        writer.writerow(["注数", report.count])
        writer.writerow(["总投入(元)", report.cost])
        writer.writerow(["总奖金(元)", report.win])
        writer.writerow(["盈亏(元)", report.profit])
        writer.writerow(["回报率", report.roi])
        writer.writerow(["开奖号码", report.draw_display])
        writer.writerow([])
        writer.writerow(["奖级", "中奖注数", "奖金合计(元)"])
        for k in report.level_counts:
            writer.writerow([k, report.level_counts[k], report.win_money_by_level[k]])
        st.download_button(
            "⬇️ 导出统计结果 CSV",
            data=csv_buf.getvalue().encode("utf-8-sig"),
            file_name=f"{game.code}_batch_report.csv",
            mime="text/csv",
        )


# ================================================================ Tab3 冷热号
with tab_hot:
    st.subheader("🔥 冷热号分析（基于历史开奖数据）")
    src = st.radio("数据来源", ["内置演示数据", "上传 CSV"], horizontal=True)

    draws = None
    if src == "内置演示数据":
        if game.is_digit:
            st.warning("数字型玩法为整体号码，不参与冷热号分析。请选择乐透型彩种。")
        else:
            draws = load_demo(game)
            st.caption(f"已加载内置演示数据：{len(draws)} 期")
    else:
        uploaded = st.file_uploader("上传历史开奖 CSV（首列期号，其后按彩种规则排列号码）", type=["csv"])
        if uploaded is not None:
            tmp = Path(BASE_DIR / f"_upload_{game.code}.csv")
            tmp.write_bytes(uploaded.getvalue())
            draws = history.load_draws_csv(tmp, game)
            tmp.unlink(missing_ok=True)
            if draws:
                st.caption(f"解析成功：{len(draws)} 期")
            else:
                st.error("CSV 解析失败，请确认列格式（如双色球：期号,红1..红6,蓝）")

    if draws:
        top_n = st.slider("展示数量 N", 3, 15, 8)
        hc = history.hot_cold(draws, game, top_n=top_n)
        freq = history.frequencies(draws, game)
        miss = history.missing_periods(draws, game)
        for z in game.zones:
            c1, c2 = st.columns(2)
            hot = hc[z.name]["hot"]
            cold = hc[z.name]["cold"]
            with c1:
                st.markdown(f"**{z.label} · 热号**（出现最多）")
                st.dataframe(
                    pd.DataFrame([{"号码": n, "出现次数": freq[z.name][n], "当前遗漏": miss[z.name][n]} for n in hot]),
                    width="stretch", hide_index=True,
                )
            with c2:
                st.markdown(f"**{z.label} · 冷号**（最少出现 / 遗漏最长）")
                st.dataframe(
                    pd.DataFrame([{"号码": n, "出现次数": freq[z.name][n], "当前遗漏": miss[z.name][n]} for n in cold]),
                    width="stretch", hide_index=True,
                )
        if game.special and "special" in hc:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**特别号 · 热号**")
                st.write(" ".join(f"{n:02d}" for n in hc["special"]["hot"]))
            with c2:
                st.markdown(f"**特别号 · 冷号**")
                st.write(" ".join(f"{n:02d}" for n in hc["special"]["cold"]))
        st.caption("注：历史数据仅供娱乐观察，**不能预测未来开奖**——每期开奖相互独立。")


# ================================================================ Tab4 全部规则
with tab_rules:
    st.subheader("📖 全部彩种规则与奖级（2026 年现行官方口径）")
    for g in GAMES.values():
        with st.expander(f"{g.name}", expanded=False):
            if g.is_digit:
                st.write(f"**玩法**：{' / '.join(g.play_names)}（每注 {g.price} 元）")
            else:
                zone_desc = "；".join(f"{z.label} 1-{z.pool_size} 选 {z.pick}" for z in g.zones)
                if g.special:
                    zone_desc += "；另摇出 1 个特别号"
                if g.pool_high:
                    zone_desc += "；奖池 ≥ 8 亿时三至七等奖自动上调"
                st.write(f"**选号规则**：{zone_desc}（每注 {g.price} 元）")
            st.dataframe(draw_level_table(g, pool_high=False), width="stretch", hide_index=True)


st.caption("时光选彩 · 纯模拟工具 · 不构成任何购彩建议")
