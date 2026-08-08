from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_password: str = "admin123"
    session_secret: str = "s5wyBQtJtQmnFuiybD2HY_ZOiXsFEYG9pTHJ6Qd1BBGq0sOwQ_lYVundxNrDo6xYf"
    # SQLite makes the demo usable with one command on a laptop. Docker Compose
    # overrides this with PostgreSQL for the production-like local stack.
    database_url: str = "sqlite+aiosqlite:///./stock_tracker.db"
    smartapi_api_key: str = "ptqyUyjU"
    smartapi_client_code: str = "K56059679"
    smartapi_pin: str = "7337"
    smartapi_totp_secret: str = "XCOJ7QUNRVXCOSN5275SOYL7BM"
    telegram_bot_token: str = "8556772251:AAGIJusLfKvDGqz-tljK8yNWcYn9K_Lfg2Y"
    telegram_chat_id: str = "@Kama_stock_predictor_bot"

    @property
    def smartapi_ready(self) -> bool:
        return all((self.smartapi_api_key, self.smartapi_client_code, self.smartapi_pin, self.smartapi_totp_secret))


@lru_cache
def get_settings() -> Settings:
    return Settings()
