import re

from pydantic import BaseModel, Field, field_validator


ACCEPT_LANGUAGE_PATTERN = re.compile(r"/([^-;]*)(?:-([^;]*))?(?:;q=([0-9]\.[0-9]))?/")


class CommonHeaders(BaseModel):
    user_agent: str = Field(min_length=1)
    accept_language: str = Field(min_length=1)

    @field_validator("accept_language")
    @classmethod
    def validate_accept_language(cls, value: str) -> str:
        if not ACCEPT_LANGUAGE_PATTERN.fullmatch(value):
            raise ValueError("Accept-Language header has an invalid format")
        return value
