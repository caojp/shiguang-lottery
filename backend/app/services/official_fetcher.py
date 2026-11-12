"""官方开奖数据抓取：中国福彩网 + 中国体彩网。

数据源（均为官方站点，字段与期号保持官网原样，便于实体店/官网逐期核对）：
- 福彩（中国福彩网 JSON 接口 findDrawNotice）
  ssq 双色球 / 3d 福彩3D / kl8 快乐8 / qlc 七乐彩
- 体彩（中国体彩网 webapi getHistoryPageListV1）
  85 超级大乐透 / 35 排列3 / 350133 排列5

期号格式：福彩为 7 位（如 2026129），体彩为 5 位（如 26129）——与官网一致。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import httpx

CWL_NAME = {"ssq": "ssq", "fc3d": "3d", "kl8": "kl8", "qlc": "qlc"}
SPORTTERY_GNO = {"dlt": "85", "pl3": "35", "pl5": "350133"}

CWL_URL = (
    "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice"
    "?name={name}&issueCount=&issueStart=&issueEnd=&dayStart=&dayEnd="
    "&pageNo={page_no}&pageSize={page_size}&week=&systemType=PC"
)
SPORTTERY_URL = (
    "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
    "?gameNo={gno}&provinceId=0&pageSize={page_size}&isVerify=1&pageNo={page_no}"
)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


class FetchError(RuntimeError):
    """官方接口不可达或返回结构异常。"""


@dataclass
class DrawRecord:
    """一期官方开奖记录（numbers 结构与 draw_history.numbers_json 一致）。"""

    issue: str
    draw_date: date
    numbers: dict[str, Any]
    source: str = field(default="official")


def _get_json(url: str, referer: str, retries: int = 3) -> dict:
    headers = {"User-Agent": UA, "Referer": referer}
    last_err: Exception | None = None
    for i in range(retries):
        try:
            resp = httpx.get(url, headers=headers, timeout=20, follow_redirects=True)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data
            last_err = FetchError("返回非 JSON 对象")
        except Exception as e:  # noqa: BLE001 - 网络类异常统一重试
            last_err = e
        time.sleep(1.5 * (i + 1))
    raise FetchError(f"请求失败：{url}（{type(last_err).__name__}: {last_err}）")


def _parse_date(raw: str) -> date:
    """'2026-11-10(二)' / '2026-11-11' -> date。"""
    txt = (raw or "").strip()[:10]
    y, m, d = txt.split("-")
    return date(int(y), int(m), int(d))


def _tokens(raw: str) -> list[str]:
    """'03,09,16' / '02 12 14' / '5+4+4' -> ['03','09','16']。"""
    return [t.strip() for t in str(raw).replace("+", " ").replace(",", " ").split() if t.strip()]


def _digits_from(tokens: list[str], expect: int) -> str | None:
    """数字型开奖号按位拼接（保留前导 0），位数不符返回 None。"""
    if len(tokens) != expect:
        return None
    return "".join(t[-1] for t in tokens)


# ---------------------------------------------------------------- 福彩


def _parse_cwl(game_code: str, item: dict) -> DrawRecord | None:
    issue = str(item.get("code", "")).strip()
    if not issue:
        return None
    red = _tokens(item.get("red", ""))
    blue = _tokens(item.get("blue", ""))

    if game_code == "fc3d":
        digits = _digits_from(red, 3)
        if digits is None:
            return None
        numbers = {"zones": {}, "special": None, "digits": digits}
    elif game_code == "kl8":
        if len(red) != 20:
            return None
        numbers = {"zones": {"main": sorted(int(x) for x in red)}, "special": None, "digits": ""}
    elif game_code == "qlc":
        if len(red) != 7 or len(blue) != 1:
            return None
        numbers = {
            "zones": {"base": sorted(int(x) for x in red)},
            "special": int(blue[0]),
            "digits": "",
        }
    elif game_code == "ssq":
        if len(red) != 6 or len(blue) != 1:
            return None
        numbers = {
            "zones": {"red": sorted(int(x) for x in red), "blue": [int(blue[0])]},
            "special": None,
            "digits": "",
        }
    else:
        return None

    return DrawRecord(issue=issue, draw_date=_parse_date(item.get("date", "")), numbers=numbers)


def fetch_cwl(game_code: str, pages: int = 1, page_size: int = 30) -> list[DrawRecord]:
    """抓取福彩某彩种最近 pages*page_size 期（按官网倒序）。"""
    name = CWL_NAME[game_code]
    out: list[DrawRecord] = []
    for page_no in range(1, pages + 1):
        data = _get_json(
            CWL_URL.format(name=name, page_no=page_no, page_size=page_size),
            referer="https://www.cwl.gov.cn/",
        )
        items = data.get("result") or []
        if not items:
            break
        for item in items:
            rec = _parse_cwl(game_code, item)
            if rec:
                out.append(rec)
        if len(items) < page_size:
            break
        time.sleep(0.6)
    return out


# ---------------------------------------------------------------- 体彩


def _parse_sporttery(game_code: str, item: dict) -> DrawRecord | None:
    issue = str(item.get("lotteryDrawNum", "")).strip()
    if not issue:
        return None
    toks = _tokens(item.get("lotteryDrawResult", ""))

    if game_code == "dlt":
        if len(toks) != 7:
            return None
        vals = [int(t) for t in toks]
        numbers = {
            "zones": {"front": sorted(vals[:5]), "back": sorted(vals[5:7])},
            "special": None,
            "digits": "",
        }
    elif game_code in ("pl3", "pl5"):
        expect = 3 if game_code == "pl3" else 5
        digits = _digits_from(toks, expect)
        if digits is None:
            return None
        numbers = {"zones": {}, "special": None, "digits": digits}
    else:
        return None

    return DrawRecord(
        issue=issue, draw_date=_parse_date(item.get("lotteryDrawTime", "")), numbers=numbers
    )


def fetch_sporttery(game_code: str, pages: int = 1, page_size: int = 30) -> list[DrawRecord]:
    """抓取体彩某彩种最近 pages*page_size 期（按官网倒序）。"""
    gno = SPORTTERY_GNO[game_code]
    out: list[DrawRecord] = []
    for page_no in range(1, pages + 1):
        data = _get_json(
            SPORTTERY_URL.format(gno=gno, page_size=page_size, page_no=page_no),
            referer="https://www.lottery.gov.cn/",
        )
        value = data.get("value") or {}
        items = value.get("list") or []
        if not items:
            break
        for item in items:
            rec = _parse_sporttery(game_code, item)
            if rec:
                out.append(rec)
        if len(items) < page_size:
            break
        time.sleep(0.6)
    return out


def fetch_game(game_code: str, pages: int = 1, page_size: int = 30) -> list[DrawRecord]:
    """按彩种路由到对应官方接口。"""
    if game_code in CWL_NAME:
        return fetch_cwl(game_code, pages, page_size)
    if game_code in SPORTTERY_GNO:
        return fetch_sporttery(game_code, pages, page_size)
    raise FetchError(f"彩种 {game_code} 暂无官方数据源")
