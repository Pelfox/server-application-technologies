from pydantic import BaseModel, Field


class ResourceBase(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class ResourceCreate(ResourceBase):
    pass


class ResourceUpdate(ResourceBase):
    pass


class Resource(ResourceBase):
    id: int = Field(gt=0)
