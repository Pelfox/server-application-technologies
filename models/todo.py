from pydantic import BaseModel, ConfigDict, Field


class TodoBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1)
    description: str = Field(min_length=1)


class TodoCreate(TodoBase):
    pass


class TodoUpdate(TodoBase):
    completed: bool


class Todo(TodoBase):
    id: int = Field(gt=0)
    completed: bool
