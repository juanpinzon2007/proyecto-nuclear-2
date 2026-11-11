from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SPS API"
    postgres_host: str = "localhost"
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = "sps"
    postgres_user: str = "sps"
    postgres_password: SecretStr | None = None
    identity_jwt_secret: SecretStr | None = None
    identity_jwt_issuer: str = "sps-api"
    identity_jwt_audience: str = "sps"
    identity_jwt_minutes: int = Field(default=15, ge=1, le=60)
    identity_institutional_domains: tuple[str, ...] = ()
    # Convención histórica verificada del despliegue; nunca inferir UTC/local.
    participation_timestamp_zone: str | None = None
    scheduling_mail_enabled: bool = False
    scheduling_mail_host: str | None = None
    scheduling_mail_port: int | None = Field(default=None, ge=1, le=65535)
    scheduling_mail_tls: str | None = None
    scheduling_mail_from: str | None = None
    scheduling_mail_username: str | None = None
    scheduling_mail_password: SecretStr | None = None
    scheduling_mail_encryption_key: SecretStr | None = None
    scheduling_mail_public_url: str | None = None

    @field_validator('scheduling_mail_port', mode='before')
    @classmethod
    def puerto_correo_opcional(cls, value):
        return None if value == '' else value

    @property
    def database_url(self) -> URL:
        if self.postgres_password is None or not self.postgres_password.get_secret_value():
            raise ValueError("Configure POSTGRES_PASSWORD antes de usar PostgreSQL.")
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
