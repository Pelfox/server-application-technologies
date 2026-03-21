from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class UserProfile(BaseModel):
    username: str = Field(min_length=1)
    full_name: str = Field(min_length=1)
    email: str = Field(min_length=1)


class SessionData(BaseModel):
    profile: UserProfile
    last_activity: int = Field(ge=0)
