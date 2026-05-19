from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    fmp_api_key: str = ""
    alpha_vantage_api_key: str = ""
    alphavantage_api_key: str = ""
    finnhub_api_key: str = ""
    news_api_key: str = ""
    polygon_api_key: str = ""
    massive_api_key: str = ""
    marketaux_api_key: str = ""
    tiingo_api_key: str = ""
    twelvedata_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-5.2"
    tipranks_enabled: bool = False
    tipranks_cookie: str = ""
    tipranks_user_agent: str = "StonksResearch/1.0"
    database_url: str = "sqlite:///./data/stonks.db"
    under_dollar_refresh_seconds: int = 300
    sec_user_agent: str = "Stonks research app contact@example.com"
    app_contact_email: str = "contact@example.com"
    app_timezone: str = "America/Tijuana"
    cache_ttl_seconds: int = 900
    cache_dir: Path = Path("data/cache")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.alpha_vantage_api_key and settings.alphavantage_api_key:
        settings.alpha_vantage_api_key = settings.alphavantage_api_key
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    return settings
