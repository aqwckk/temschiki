from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_prefix="APP_",
        extra="ignore",
    )

    database_url: str = "sqlite:///" + (BACKEND_DIR / "data.db").as_posix()
    emulators_dir: Path = ROOT_DIR / "emulators"

    # dry - только лог, live - реальные запросы к стенду
    ujin_mode: Literal["dry", "live"] = "dry"
    ujin_base_url: str = "https://api-uae-test.ujin.tech"
    ujin_credentials_file: Path = BACKEND_DIR / "доступы.json"
    ujin_flush_interval: float = 3.0


settings = Settings()
