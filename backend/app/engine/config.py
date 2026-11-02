"""彩种规则配置：号码池、抽取个数、奖级表、浮动奖默认值。

规则口径依据 PRD 附录 A 所列官方来源（2026 年现行规则）：
- 双色球 / 福彩3D / 快乐8 / 七乐彩：中国福彩网
- 超级大乐透（2026-02 新规 7 奖级）/ 排列3 / 排列5：中国体彩网

新增彩种只需在此追加一个 GameConfig 并注册到 GAMES。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Zone:
    """一个独立号码池分组，如双色球的红球 / 蓝球、大乐透的前区 / 后区。"""

    name: str          # 分组标识，如 "red" / "blue" / "front" / "back" / "base" / "main"
    pool_size: int     # 号码池大小（号码为 1..pool_size）
    pick: int          # 该组应抽取的个数
    label: str = ""    # 展示名称，如 "红球"


@dataclass(frozen=True)
class PrizeLevel:
    """一个奖级。

    amount 为固定奖金；amount 为 None 表示浮动奖，模拟时取 float_default。
    amount_high 用于大乐透"奖池 ≥ 8 亿"联动机制下的固定奖上浮值。
    """

    name: str                 # 奖级名，如 "一等奖"
    condition: str            # 中奖条件描述，如 "6红+1蓝"
    amount: Optional[int] = None
    float_default: Optional[int] = None   # 浮动奖模拟默认奖金（元/注）
    amount_high: Optional[int] = None     # 奖池联动时固定奖金上浮值

    @property
    def is_float(self) -> bool:
        return self.amount is None

    def money(self, pool_high: bool = False) -> int:
        """返回本奖级单注奖金；浮动奖返回模拟默认值。"""
        if self.amount is not None:
            if pool_high and self.amount_high is not None:
                return self.amount_high
            return self.amount
        return self.float_default or 0


@dataclass(frozen=True)
class GameConfig:
    """单个彩种的完整规则配置。"""

    code: str                          # 唯一标识，如 "ssq"
    name: str                          # 展示名，如 "双色球"
    game_type: str                     # lotto=乐透/双区, keno=基诺, digit3=三位数字, digit5=五位数字
    price: int = 2                     # 每注金额（元）
    zones: tuple[Zone, ...] = ()       # 号码池分组（乐透/基诺）
    digits: int = 0                    # 数字型位数（digit3=3, digit5=5）
    special: bool = False              # 是否额外开出 1 个特别号（七乐彩）
    pool_high: bool = False            # 是否支持"奖池 ≥ 8 亿"联动上调（大乐透）
    play_names: tuple[str, ...] = ()   # 数字型可选投注玩法（直选/组选3/组选6）
    draw_days: tuple[int, ...] = ()    # 开奖日，0=周一 … 6=周日；空表示每日开奖
    prize_levels: tuple[PrizeLevel, ...] = ()

    @property
    def is_digit(self) -> bool:
        return self.game_type in ("digit3", "digit5")

    def zone(self, name: str) -> Zone:
        for z in self.zones:
            if z.name == name:
                return z
        raise KeyError(f"彩种 {self.code} 没有号码池分组 {name}")


# ---------------------------------------------------------------- 双色球
SSQ = GameConfig(
    code="ssq",
    name="双色球",
    game_type="lotto",
    price=2,
    zones=(Zone("red", 33, 6, "红球"), Zone("blue", 16, 1, "蓝球")),
    draw_days=(1, 3, 6),
    prize_levels=(
        PrizeLevel("一等奖", "6红+1蓝", float_default=5_000_000),
        PrizeLevel("二等奖", "6红+0蓝", float_default=200_000),
        PrizeLevel("三等奖", "5红+1蓝", 3000),
        PrizeLevel("四等奖", "5红+0蓝 或 4红+1蓝", 200),
        PrizeLevel("五等奖", "4红+0蓝 或 3红+1蓝", 10),
        PrizeLevel("六等奖", "蓝球命中(红≤2)", 5),
    ),
)

# ---------------------------------------------------------------- 福彩3D
FC3D = GameConfig(
    code="fc3d",
    name="福彩3D",
    game_type="digit3",
    price=2,
    digits=3,
    play_names=("直选", "组选3", "组选6"),
    prize_levels=(
        PrizeLevel("单选", "按位完全一致", 1040),
        PrizeLevel("组选3", "号码相同、顺序不限(开奖号含对子)", 346),
        PrizeLevel("组选6", "号码相同、顺序不限(开奖号三位各异)", 173),
    ),
)

# ---------------------------------------------------------------- 快乐8（默认选十玩法）
KL8 = GameConfig(
    code="kl8",
    name="快乐8",
    game_type="keno",
    price=2,
    zones=(Zone("main", 80, 10, "选十号码"),),
    prize_levels=(
        PrizeLevel("选十中十", "命中10个", float_default=5_000_000),
        PrizeLevel("选十中九", "命中9个", 8000),
        PrizeLevel("选十中八", "命中8个", 720),
        PrizeLevel("选十中七", "命中7个", 80),
        PrizeLevel("选十中六", "命中6个", 5),
        PrizeLevel("选十中五", "命中5个", 3),
        PrizeLevel("选十中零", "一个未中", 2),
    ),
)

# ---------------------------------------------------------------- 七乐彩
QLC = GameConfig(
    code="qlc",
    name="七乐彩",
    game_type="lotto",
    price=2,
    zones=(Zone("base", 30, 7, "基本号"),),
    special=True,
    draw_days=(0, 2, 4),
    prize_levels=(
        PrizeLevel("一等奖", "7个基本号全中", float_default=1_000_000),
        PrizeLevel("二等奖", "6基本号+特别号", float_default=50_000),
        PrizeLevel("三等奖", "6个基本号", float_default=10_000),
        PrizeLevel("四等奖", "5基本号+特别号", 200),
        PrizeLevel("五等奖", "5个基本号", 50),
        PrizeLevel("六等奖", "4基本号+特别号", 10),
        PrizeLevel("七等奖", "4个基本号", 5),
    ),
)

# ---------------------------------------------------------------- 超级大乐透（2026-02 新规）
DLT = GameConfig(
    code="dlt",
    name="超级大乐透",
    game_type="lotto",
    price=2,
    zones=(Zone("front", 35, 5, "前区"), Zone("back", 12, 2, "后区")),
    pool_high=True,
    draw_days=(0, 2, 5),
    prize_levels=(
        PrizeLevel("一等奖", "5前+2后", float_default=10_000_000),
        PrizeLevel("二等奖", "5前+1后", float_default=500_000),
        PrizeLevel("三等奖", "5前+0后 或 4前+2后", 5000, amount_high=6666),
        PrizeLevel("四等奖", "4前+1后", 300, amount_high=380),
        PrizeLevel("五等奖", "4前+0后 或 3前+2后", 150, amount_high=200),
        PrizeLevel("六等奖", "3前+1后 或 2前+2后", 15, amount_high=18),
        PrizeLevel("七等奖", "3前+0后 或 2前+1后 或 1前+2后 或 0前+2后", 5, amount_high=7),
    ),
)

# ---------------------------------------------------------------- 排列3
PL3 = GameConfig(
    code="pl3",
    name="排列3",
    game_type="digit3",
    price=2,
    digits=3,
    play_names=("直选", "组选3", "组选6"),
    prize_levels=(
        PrizeLevel("直选", "按位完全一致", 1040),
        PrizeLevel("组选3", "号码相同、顺序不限(开奖号含对子)", 346),
        PrizeLevel("组选6", "号码相同、顺序不限(开奖号三位各异)", 173),
    ),
)

# ---------------------------------------------------------------- 排列5
PL5 = GameConfig(
    code="pl5",
    name="排列5",
    game_type="digit5",
    price=2,
    digits=5,
    prize_levels=(
        PrizeLevel("一等奖", "五位数按位完全一致", 100_000),
    ),
)

# 彩种注册表（界面下拉顺序）
GAMES: dict[str, GameConfig] = {g.code: g for g in (SSQ, FC3D, KL8, QLC, DLT, PL3, PL5)}

# 数字型彩种代码集合，用于判别
DIGIT_CODES: frozenset[str] = frozenset({"fc3d", "pl3", "pl5"})
