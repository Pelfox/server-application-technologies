from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(min_length=1)


class User(UserBase):
    password: str = Field(min_length=1)


class UserCreate(User):
    role: Literal["admin", "user", "guest"] = "user"


class UserInDB(UserBase):
    hashed_password: str = Field(min_length=1)
    role: Literal["admin", "user", "guest"]


class MessageResponse(BaseModel):
    message: str = Field(min_length=1)


class AccessTokenResponse(BaseModel):
    access_token: str = Field(min_length=1)
    token_type: Literal["bearer"] = "bearer"


class TokenPayload(BaseModel):
    sub: str = Field(min_length=1)
