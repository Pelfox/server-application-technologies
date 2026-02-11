from pydantic import BaseModel


class User(BaseModel):
    name: str
    age: int


class UserResponse(BaseModel):
    name: str
    age: int
    is_adult: bool
