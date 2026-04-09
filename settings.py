from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    mode: Literal["DEV", "PROD"] = Field(default="PROD", validation_alias="MODE")
    docs_user: str | None = Field(default=None, validation_alias="DOCS_USER")
    docs_password: str | None = Field(default=None, validation_alias="DOCS_PASSWORD")
    jwt_secret_key: str = Field(
        default="development-jwt-secret-key-please-change",
        validation_alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )

    @model_validator(mode="after")
    def validate_docs_credentials(self) -> "Settings":
        if self.mode == "DEV" and (not self.docs_user or not self.docs_password):
            raise ValueError(
                "DOCS_USER and DOCS_PASSWORD must be set when MODE=DEV",
            )
        if len(self.jwt_secret_key) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 characters")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
