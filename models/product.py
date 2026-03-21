from pydantic import BaseModel, Field


class Product(BaseModel):
    product_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    price: float = Field(gt=0)
