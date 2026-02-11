from pydantic import BaseModel


class Feedback(BaseModel):
    name: str
    message: str


class FeedbackResponse(BaseModel):
    message: str
