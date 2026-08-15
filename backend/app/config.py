from functools import lru_cache
from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_password: str = ""
    session_secret: str = ""

    database_url: str = (
        "sqlite+aiosqlite:///./stock_tracker.db"
    )

    smartapi_api_key: str = ""
    smartapi_client_code: str = ""
    smartapi_pin: str = ""
    smartapi_totp_secret: str = ""

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    @property
    def smartapi_ready(self) -> bool:
        return all(
            (
                self.smartapi_api_key,
                self.smartapi_client_code,
                self.smartapi_pin,
                self.smartapi_totp_secret,
            )
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()