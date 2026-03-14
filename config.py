from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from pydantic import Field


class Settings(BaseSettings):
    # Общие настройки
    APP_NAME: str = "PythonParsers"
    DEBUG: bool = False

    # Telegram (для tg_parser)
    TG_API_ID: Optional[int] = None
    TG_API_HASH: Optional[str] = None
    TG_PHONE: Optional[str] = None

    # Прокси (опционально)
    PROXY_URL: Optional[str] = None  # например http://user:pass@ip:port
    PROXY_LIST: List[str] = []  # можно список для ротации

    # Папка для сохранения результатов
    OUTPUT_DIR: str = "results"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()