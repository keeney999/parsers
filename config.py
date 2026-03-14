from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List

class Settings(BaseSettings):
    # Общие настройки
    APP_NAME: str = "PythonParsers"
    DEBUG: bool = False
    OUTPUT_DIR: str = "results"

    # Telegram (для tg_parser)
    TG_API_ID: Optional[int] = None
    TG_API_HASH: Optional[str] = None
    TG_PHONE: Optional[str] = None

    # Прокси
    PROXY_URL: Optional[str] = None
    PROXY_LIST: List[str] = []
    PROXY_FILE: Optional[str] = None

    # Яндекс API
    YANDEX_API_KEY: Optional[str] = None

    # Настройки задержек и таймаутов
    MIN_DELAY: float = 2.0
    MAX_DELAY: float = 5.0
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()