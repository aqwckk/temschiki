from pathlib import Path

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


settings = Settings()
