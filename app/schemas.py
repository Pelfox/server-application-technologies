from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator


class ErrorResponse(BaseModel):
    error_code: str
    message: str


class MessageResponse(BaseModel):
    message: str


class ValidationErrorItem(BaseModel):
    field: str
    message: str
    error_type: str


class ValidationErrorResponse(BaseModel):
    error_code: str
    message: str
    errors: list[ValidationErrorItem]


class NoteCreate(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    content: str | None = Field(default=None, min_length=10, max_length=2000)
    is_published: StrictBool = False

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            msg = "Title must not be blank"
            raise ValueError(msg)
        return title

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str | None) -> str | None:
        if value is None:
            return value

        content = value.strip()
        if not content:
            msg = "Content must not be blank when provided"
            raise ValueError(msg)
        return content


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str | None
    created_at: datetime
    is_published: bool
