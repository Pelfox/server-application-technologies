from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr = Field()
    age: int | None = Field(default=None, gt=0)
    is_subscribed: bool | None = Field(default=None)
