from re import IGNORECASE, search

from pydantic import BaseModel, Field, field_validator


class Feedback(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    message: str = Field(min_length=10, max_length=500)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        pattern = r"\b(кринж\w*|рофл\w*|вайб\w*)\b"
        if search(pattern, value, IGNORECASE):
            raise ValueError("Использование недопустимых слов")
        return value


class FeedbackResponse(BaseModel):
    message: str
