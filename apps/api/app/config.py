from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str = Field(min_length=32)
    app_origin: str = "http://localhost:5173"
    chain_id: int = Field(default=10143, gt=0)
    challenge_ttl_seconds: int = Field(default=300, ge=30, le=600)
    token_ttl_seconds: int = Field(default=1800, ge=60, le=3600)
    nonce_cooldown_seconds: int = Field(default=5, ge=1)

    @field_validator("jwt_secret")
    @classmethod
    def reject_example_secret(cls, value: str) -> str:
        if value.startswith("replace-"):
            raise ValueError("Generate a random JWT_SECRET before starting the API")
        return value

    @field_validator("database_url")
    @classmethod
    def require_postgres(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use postgresql+psycopg")
        return value

    @field_validator("app_origin")
    @classmethod
    def validate_origin(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (parsed.scheme not in ("http", "https") or not parsed.netloc
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment
                or parsed.username or parsed.password):
            raise ValueError("APP_ORIGIN must be an exact HTTP(S) origin")
        if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1"):
            raise ValueError("Use HTTPS outside localhost")
        return value.rstrip("/")
