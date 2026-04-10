from functools import lru_cache
import os
from pathlib import Path

from dotenv import dotenv_values
from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parents[2]
_ENV_FILE = BACKEND_DIR / ".env"

# Load .env values and patch OS env vars.
# The project .env is the source of truth for local development.
# Production deployments should set env vars explicitly.
for key, value in dotenv_values(_ENV_FILE).items():
    os.environ[key] = value


def _read_secret_file(path_value: str) -> str:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = (BACKEND_DIR / path).resolve()
    return path.read_text(encoding="utf-8").strip()


def _resolve_secret(value: str, file_path: str) -> str:
    if file_path and file_path.strip():
        p = Path(file_path).expanduser()
        if p.is_file():
            return _read_secret_file(file_path)
    return value


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./landten.db"

    # JWT
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    SECRET_KEY_FILE: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Email
    MAIL_HOST: str = "smtp.gmail.com"
    MAIL_USERNAME: str = ""
    MAIL_USERNAME_FILE: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_PASSWORD_FILE: str = ""
    MAIL_PORT: int = 587
    MAIL_FROM: str = ""
    MAIL_FROM_FILE: str = ""

    # App
    APP_NAME: str = "LandTen"
    FRONTEND_URL: str = "http://localhost:3000"

    def model_post_init(self, __context) -> None:
        self.SECRET_KEY = _resolve_secret(self.SECRET_KEY, self.SECRET_KEY_FILE)
        self.MAIL_USERNAME = _resolve_secret(
            self.MAIL_USERNAME, self.MAIL_USERNAME_FILE
        )
        self.MAIL_PASSWORD = _resolve_secret(
            self.MAIL_PASSWORD, self.MAIL_PASSWORD_FILE
        )
        self.MAIL_FROM = _resolve_secret(self.MAIL_FROM, self.MAIL_FROM_FILE)

    class Config:
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
