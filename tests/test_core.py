"""时光选彩核心逻辑单元测试。

覆盖：7 彩种号码生成规则、全部奖级判定、数字型玩法、策略选号、自选校验、批量统计。
运行：python -m pytest tests/ -v
"""
from __future__ import annotations

import time

import pytest

from shiguang.config import GAMES
from shiguang.engine import Ticket, generate_tickets, quick_pick, validate_ticket
from shiguang.draw import draw
from shiguang.prize import check
from shiguang.stats import simulate


def make_ticket(code: str, **zones) -> Ticket:
    return Ticket(code, zones={k: tuple(v) for k, v in zones.items()})


def make_draw(code: str, special=None, digits: str = "", **zones) -> "DrawResult":
    from shiguang.draw import DrawResult

    return DrawResult(code, zones={k: tuple(v) for k, v in zones.items()}, special=special, digits=digits)


# ---------------------------------------------------------------- 生成规则

@pytest.mark.parametrize(
    "code,zone_names,picks,pools",
    [
        ("ssq", ("red", "blue"), (6, 1), (33, 16)),
        ("kl8", ("main",), (10,), (80,)),
        ("qlc", ("base",), (7,), (30,)),
        ("dlt", ("front", "back"), (5, 2), (35, 12)),
    ],
)
def test_lotto_quick_pick_rules(code, zone_names, picks, pools):
    game = GAMES[code]
    for _ in range(50):
        t = quick_pick(game)
        for z, pick, pool in zip(game.zones, picks, pools):
            nums = t.zones[z.name]
            assert len(nums) == pick
            assert all(1 <= n <= pool for n in nums)
            assert len(set(nums)) == pick            # 无重复
            assert nums == tuple(sorted(nums))        # 升序


@pytest.mark.parametrize("code,digits", [("fc3d", 3), ("pl3", 3), ("pl5", 5)])
def test_digit_quick_pick_rules(code, digits):
    game = GAMES[code]
    for _ in range(50):
        t = quick_pick(game)
        assert t.digits.isdigit()
        assert len(t.digits) == digits               # 保留前导零
        assert 0 <= int(t.digits) < 10**digits


def test_qlc_draw_special():
    game = GAMES["qlc"]
    for _ in range(30):
        d = draw(game)
        assert d.special is not None and 1 <= d.special <= 30
        assert d.special not in set(d.zones["base"])  # 特别号不与基本号重复


def test_kl8_draw_20_numbers():
    game = GAMES["kl8"]
    d = draw(game)
    assert len(d.zones["main"]) == 20


def test_generate_many_1000_fast():
    game = GAMES["ssq"]
    start = time.perf_counter()
    tickets = generate_tickets(game, count=1000)
    cost = time.perf_counter() - start
    assert len(tickets) == 1000
    assert cost < 2.0, f"1000 注生成耗时 {cost:.2f}s，超出 2s 验收线"


# ---------------------------------------------------------------- 双色球奖级

SSQ_TICKET = make_ticket("ssq", red=(1, 2, 3, 4, 5, 6), blue=(7,))


def _ssq_check(rh: int, bh: int) -> tuple[str, int]:
    game = GAMES["ssq"]
    # 开奖红球：包含用户前 rh 个号码，其余从 7..33 补齐
    rest = list(range(7, 34))
    win_red = tuple(sorted(list(range(1, rh + 1)) + rest[: 6 - rh]))
    win_blue = (7,) if bh else (8,)
    r = check(game, SSQ_TICKET, make_draw("ssq", red=win_red, blue=win_blue))
    assert r.hits == {"red": rh, "blue": bh}
    return (r.level.name if r.level else "未中奖", r.money)


def test_ssq_all_levels():
    assert _ssq_check(6, 1) == ("一等奖", 5_000_000)
    assert _ssq_check(6, 0) == ("二等奖", 200_000)
    assert _ssq_check(5, 1) == ("三等奖", 3000)
    assert _ssq_check(5, 0) == ("四等奖", 200)
    assert _ssq_check(4, 1) == ("四等奖", 200)
    assert _ssq_check(4, 0) == ("五等奖", 10)
    assert _ssq_check(3, 1) == ("五等奖", 10)
    assert _ssq_check(2, 1) == ("六等奖", 5)
    assert _ssq_check(1, 1) == ("六等奖", 5)
    assert _ssq_check(0, 1) == ("六等奖", 5)
    assert _ssq_check(0, 0) == ("未中奖", 0)


# ---------------------------------------------------------------- 大乐透奖级

DLT_TICKET = make_ticket("dlt", front=(1, 2, 3, 4, 5), back=(6, 7))


def _dlt_check(fh: int, bh: int) -> tuple[str, int]:
    game = GAMES["dlt"]
    win_front = (1, 2, 3, 4, 5) if fh == 5 else ((1, 2, 3, 4, 20) if fh == 4 else ((1, 2, 3, 20, 21) if fh == 3 else ((1, 2, 20, 21, 22) if fh == 2 else ((1, 20, 21, 22, 23) if fh == 1 else (20, 21, 22, 23, 24)))))
    win_back = (6, 7) if bh == 2 else ((6, 8) if bh == 1 else (8, 9))
    r = check(game, DLT_TICKET, make_draw("dlt", front=win_front, back=win_back))
    return (r.level.name if r.level else "未中奖", r.money)


def test_dlt_all_levels():
    assert _dlt_check(5, 2) == ("一等奖", 10_000_000)
    assert _dlt_check(5, 1) == ("二等奖", 500_000)
    assert _dlt_check(5, 0) == ("三等奖", 5000)
    assert _dlt_check(4, 2) == ("三等奖", 5000)
    assert _dlt_check(4, 1) == ("四等奖", 300)
    assert _dlt_check(4, 0) == ("五等奖", 150)
    assert _dlt_check(3, 2) == ("五等奖", 150)
    assert _dlt_check(3, 1) == ("六等奖", 15)
    assert _dlt_check(2, 2) == ("六等奖", 15)
    assert _dlt_check(3, 0) == ("七等奖", 5)
    assert _dlt_check(2, 1) == ("七等奖", 5)
    assert _dlt_check(1, 2) == ("七等奖", 5)
    assert _dlt_check(0, 2) == ("七等奖", 5)
    assert _dlt_check(0, 0) == ("未中奖", 0)


def test_dlt_pool_high():
    game = GAMES["dlt"]
    # 三等 (5前+0后)：5000 -> 6666
    r = check(game, DLT_TICKET, make_draw("dlt", front=(1, 2, 3, 4, 5), back=(8, 9)), pool_high=True)
    assert r.level is not None and r.level.name == "三等奖"
    assert r.money == 6666
    # 七等 (3前+0后)：5 -> 7
    r2 = check(game, DLT_TICKET, make_draw("dlt", front=(1, 2, 3, 20, 21), back=(8, 9)), pool_high=True)
    assert r2.level is not None and r2.level.name == "七等奖"
    assert r2.money == 7
    # 未启用联动时按基础金额
    r3 = check(game, DLT_TICKET, make_draw("dlt", front=(1, 2, 3, 20, 21), back=(8, 9)), pool_high=False)
    assert r3.money == 5


# ---------------------------------------------------------------- 快乐8

KL8_TICKET = make_ticket("kl8", main=(1, 2, 3, 4, 5, 6, 7, 8, 9, 10))


def _kl8_check(hit: int) -> tuple[str, int]:
    game = GAMES["kl8"]
    win = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20)
    # 前 hit 个与用户重合，其余取不重合号码
    win_set = list(range(1, hit + 1)) + list(range(21, 41 - hit + 1))[: 20 - hit]
    assert len(win_set) == 20 and len(set(win_set)) == 20
    r = check(game, KL8_TICKET, make_draw("kl8", main=tuple(win_set)))
    return (r.level.name if r.level else "未中奖", r.money)


def test_kl8_levels():
    assert _kl8_check(10) == ("选十中十", 5_000_000)
    assert _kl8_check(9) == ("选十中九", 8000)
    assert _kl8_check(8) == ("选十中八", 720)
    assert _kl8_check(7) == ("选十中七", 80)
    assert _kl8_check(6) == ("选十中六", 5)
    assert _kl8_check(5) == ("选十中五", 3)
    assert _kl8_check(0) == ("选十中零", 2)
    assert _kl8_check(4) == ("未中奖", 0)


# ---------------------------------------------------------------- 七乐彩

QLC_TICKET = make_ticket("qlc", base=(1, 2, 3, 4, 5, 6, 7))


def _qlc_check(bh: int, sh: bool) -> tuple[str, int]:
    game = GAMES["qlc"]
    win = (1, 2, 3, 4, 5, 6, 7) if bh == 7 else (
        (1, 2, 3, 4, 5, 6, 20) if bh == 6 else (
            (1, 2, 3, 4, 5, 20, 21) if bh == 5 else ((1, 2, 3, 4, 20, 21, 22) if bh == 4 else (1, 2, 3, 20, 21, 22, 23))
        )
    )
    special = 7 if sh else 30
    r = check(game, QLC_TICKET, make_draw("qlc", base=win, special=special))
    return (r.level.name if r.level else "未中奖", r.money)


def test_qlc_levels():
    assert _qlc_check(7, False) == ("一等奖", 1_000_000)
    assert _qlc_check(6, True) == ("二等奖", 50_000)
    assert _qlc_check(6, False) == ("三等奖", 10_000)
    assert _qlc_check(5, True) == ("四等奖", 200)
    assert _qlc_check(5, False) == ("五等奖", 50)
    assert _qlc_check(4, True) == ("六等奖", 10)
    assert _qlc_check(4, False) == ("七等奖", 5)
    assert _qlc_check(3, False) == ("未中奖", 0)


# ---------------------------------------------------------------- 数字型

def test_fc3d_plays():
    game = GAMES["fc3d"]
    t = Ticket("fc3d", digits="112")
    # 直选：按位一致
    r = check(game, t, make_draw("fc3d", digits="112"), play="直选")
    assert r.won and r.money == 1040
    # 直选：按位不一致不中
    r = check(game, t, make_draw("fc3d", digits="121"), play="直选")
    assert not r.won
    # 组选3：号码相同、开奖号含对子
    r = check(game, t, make_draw("fc3d", digits="121"), play="组选3")
    assert r.won and r.money == 346
    # 组选3：开奖号三位各异不中
    r = check(game, Ticket("fc3d", digits="123"), make_draw("fc3d", digits="132"), play="组选3")
    assert not r.won
    # 组选6：号码相同、开奖号三位各异
    r = check(game, Ticket("fc3d", digits="123"), make_draw("fc3d", digits="321"), play="组选6")
    assert r.won and r.money == 173


def test_pl3_plays():
    game = GAMES["pl3"]
    r = check(game, Ticket("pl3", digits="808"), make_draw("pl3", digits="880"), play="组选3")
    assert r.won and r.money == 346
    r = check(game, Ticket("pl3", digits="123"), make_draw("pl3", digits="123"), play="直选")
    assert r.won and r.money == 1040


def test_pl5():
    game = GAMES["pl5"]
    r = check(game, Ticket("pl5", digits="12345"), make_draw("pl5", digits="12345"))
    assert r.won and r.money == 100_000
    r = check(game, Ticket("pl5", digits="12345"), make_draw("pl5", digits="12346"))
    assert not r.won


# ---------------------------------------------------------------- 自选校验

def test_validate_ssq():
    game = GAMES["ssq"]
    ok, msg = validate_ticket(game, {"red": "01, 05, 12, 18, 22, 30", "blue": "07"})
    assert ok and msg == ""
    ok, msg = validate_ticket(game, {"red": "1,2,3,4,5,6,7", "blue": "1"})
    assert not ok and "6" in msg
    ok, msg = validate_ticket(game, {"red": "1,2,3,4,5,6", "blue": "1"})
    assert ok
    ok, msg = validate_ticket(game, {"red": "1,2,3,4,5,34", "blue": "1"})
    assert not ok and "超出" in msg
    ok, msg = validate_ticket(game, {"red": "1,2,3,4,5,5", "blue": "1"})
    assert not ok and "重复" in msg


def test_validate_digits():
    game = GAMES["fc3d"]
    ok, _ = validate_ticket(game, digits_text="007")
    assert ok
    ok, msg = validate_ticket(game, digits_text="12")
    assert not ok
    ok, msg = validate_ticket(GAMES["pl5"], digits_text="12345")
    assert ok


# ---------------------------------------------------------------- 策略选号

def test_strategy_zone_split():
    game = GAMES["ssq"]
    strategy = {"zone_split": {"red": [2, 2, 2]}, "consecutive": None}
    for _ in range(20):
        t = generate_tickets(game, count=1, strategy=strategy)[0]
        red = t.zones["red"]
        assert sum(1 for n in red if n <= 11) == 2
        assert sum(1 for n in red if 12 <= n <= 22) == 2
        assert sum(1 for n in red if n >= 23) == 2


def test_strategy_odd_even():
    game = GAMES["ssq"]
    strategy = {"odd_even": {"red": 3}, "consecutive": None}
    for _ in range(20):
        t = generate_tickets(game, count=1, strategy=strategy)[0]
        red = t.zones["red"]
        assert sum(1 for n in red if n % 2 == 1) == 3
        assert sum(1 for n in red if n % 2 == 0) == 3


def test_strategy_sum_range():
    game = GAMES["ssq"]
    strategy = {"sum_range": {"zone": "red", "min": 90, "max": 120}, "consecutive": None}
    for _ in range(20):
        t = generate_tickets(game, count=1, strategy=strategy)[0]
        assert 90 <= sum(t.zones["red"]) <= 120


def test_strategy_no_consecutive():
    game = GAMES["dlt"]
    strategy = {"consecutive": "forbid"}
    for _ in range(20):
        t = generate_tickets(game, count=1, strategy=strategy)[0]
        for nums in t.zones.values():
            assert all(b - a != 1 for a, b in zip(nums, nums[1:]))


def test_strategy_hot_cold():
    game = GAMES["ssq"]
    strategy = {"hot_cold": {"weights": {1: 3.0, 2: 0.2}, "mode": "hot"}, "consecutive": None}
    t = generate_tickets(game, count=1, strategy=strategy)[0]
    assert len(t.zones["red"]) == 6


def test_strategy_fallback_on_impossible():
    """和值区间过窄导致约束不可满足时，应回退为机选而不是死循环。"""
    game = GAMES["ssq"]
    strategy = {"sum_range": {"zone": "red", "min": 100, "max": 100}, "consecutive": "forbid"}
    t = generate_tickets(game, count=1, strategy=strategy)[0]
    assert len(t.zones["red"]) == 6


# ---------------------------------------------------------------- 批量统计

def test_simulate_basic():
    game = GAMES["ssq"]
    report = simulate(game, count=200)
    assert report.count == 200
    assert report.cost == 400
    assert report.win >= 0
    assert report.profit == report.win - report.cost
    assert report.roi == round(report.win / report.cost, 6)
    assert len(report.tickets) == 200
    total_notes = sum(report.level_counts.values())
    assert total_notes == report.hit_count


def test_simulate_digit():
    game = GAMES["pl5"]
    report = simulate(game, count=500)
    assert report.cost == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
