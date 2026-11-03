"""应用配置。所有可调项均支持环境变量覆盖（.env / docker-compose 注入）。"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 运行时数据库连接（asyncpg 驱动）
    database_url: str = "postgresql+asyncpg://shiguang:shiguang@localhost:5432/shiguang_lottery"

    # 迁移用同步 URL（Alembic）；留空则自动由 database_url 推导
    database_url_sync: str = ""

    # 跨域白名单（H5 / uni-app 开发服务器）
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # 用户认证：JWT 签名密钥（生产环境必须用强随机值覆盖，≥32 字节）
    secret_key: str = "dev-secret-change-me-in-production-0123456789"
    token_expire_minutes: int = 10080   # 默认 7 天

    # Agent 编排层：OpenAI 兼容 Chat Completions 接口
    llm_api_base: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    agent_enabled: bool = True   # 未配置 key 时自动降级为内置关键词路由

    # 模拟参数
    default_pool_high: bool = True      # 大乐透默认启用"奖池≥8亿"联动
    backtest_max_periods: int = 300

    # 历史数据定时任务：每日开奖后自动入库，移动端无需手动操作
    auto_fetch_enabled: bool = True
    auto_fetch_hour: int = 21           # 北京时间，开奖后留出官方数据更新时间
    auto_fetch_minute: int = 35
    auto_seed_periods: int = 60         # 首次部署无数据时的引导期数

    @property
    def cors_list(self) -> list[str]:
        return [s.strip() for s in self.cors_origins.split(",") if s.strip()]

    @property
    def sync_url(self) -> str:
        if self.database_url_sync:
            return self.database_url_sync
        return self.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")


@lru_cache
def get_settings() -> Settings:
    return Settings()
