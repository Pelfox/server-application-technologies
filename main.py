from fastapi import FastAPI
from starlette.responses import FileResponse

from models import Feedback, FeedbackResponse, User, UserResponse

app = FastAPI()
existing_user = User(age=18, name="Ваше Имя и Фамилия")
feedbacks: list[Feedback] = []


@app.get("/")
async def index():
    return FileResponse("./assets/index.html")


@app.post("/calculate")
async def calculate(num1: int, num2: int) -> dict:
    return {"result": num1 + num2}


@app.get("/users")
async def users() -> User:
    return existing_user


@app.post("/user")
async def new_user(user: User) -> UserResponse:
    is_adult = user.age >= 18
    return UserResponse(
        name=user.name,
        age=user.age,
        is_adult=is_adult,
    )


@app.post("/feedback")
async def feedback(feedback: Feedback) -> FeedbackResponse:
    feedbacks.append(feedback)
    return FeedbackResponse(
        message=f"Feedback received. Thank you, {feedback.name}."
    )
