"""规则引擎冒烟测试（无需数据库，验证复用的确定性引擎仍按官方口径工作）。"""
from __future__ import annotations

from app.engine.config import GAMES
from app.engine.draw import draw
from app.engine.engine import Ticket, generate_tickets, quick_pick, validate_ticket
from app.engine.prize import check


def test_all_games_quick_pick():
    for code, g in GAMES.items():
        t = quick_pick(g)
        assert t.game_code == code
        if g.is_digit:
            assert len(t.digits) == g.digits
        else:
            for z in g.zones:
                assert len(t.zones[z.name]) == z.pick
                assert all(1 <= n <= z.pool_size for n in t.zones[z.name])


def test_draw_shape():
    for code, g in GAMES.items():
        d = draw(g)
        if g.is_digit:
            assert len(d.digits) == g.digits
        else:
            for z in g.zones:
                want = 20 if g.game_type == "keno" else z.pick
                assert len(d.zones[z.name]) == want
        if g.special:
            assert d.special is not None and d.special not in d.zones["base"]


def test_ssq_levels():
    g = GAMES["ssq"]
    d = draw(g)
    cases = [
        (Ticket("ssq", zones={"red": (1, 2, 3, 4, 5, 6), "blue": (7,)}),
         {"red": (1, 2, 3, 4, 5, 6), "blue": (7,)}, "一等奖"),
        (Ticket("ssq", zones={"red": (1, 2, 3, 4, 5, 6), "blue": (8,)}),
         {"red": (1, 2, 3, 4, 5, 6), "blue": (7,)}, "二等奖"),
        (Ticket("ssq", zones={"red": (1, 2, 3, 4, 5, 9), "blue": (7,)}),
         {"red": (1, 2, 3, 4, 5, 6), "blue": (7,)}, "三等奖"),
    ]
    for ticket, zones, expect in cases:
        r = check(g, ticket, _dr(g, zones))
        assert r.won and r.level.name == expect


def test_dlt_pool_high():
    g = GAMES["dlt"]
    t = Ticket("dlt", zones={"front": (1, 2, 3, 4, 5), "back": (1, 2)})
    d = _dr(g, {"front": (1, 2, 3, 4, 5), "back": (1, 2)})
    assert check(g, t, d, pool_high=False).level.name == "一等奖"
    # 三等奖：5前+0后（前区全中、后区全不中）
    t3 = Ticket("dlt", zones={"front": (1, 2, 3, 4, 5), "back": (3, 4)})
    d3 = _dr(g, {"front": (1, 2, 3, 4, 5), "back": (1, 2)})
    assert check(g, t3, d3, pool_high=False).level.name == "三等奖"
    assert check(g, t3, d3, pool_high=False).money == 5000
    assert check(g, t3, d3, pool_high=True).money == 6666


def test_manual_validation():
    ok, _ = validate_ticket(GAMES["ssq"], {"red": "01 05 12 18 22 30", "blue": "07"})
    assert ok
    ok2, _ = validate_ticket(GAMES["fc3d"], digits_text="007")
    assert ok2
    ok3, _ = validate_ticket(GAMES["fc3d"], digits_text="12")
    assert not ok3


def _dr(game, zones: dict):
    from app.engine.draw import DrawResult
    return DrawResult(game.code, zones=zones)
