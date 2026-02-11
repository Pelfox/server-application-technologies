from fastapi import FastAPI
from starlette.responses import FileResponse

from models import User, UserResponse

app = FastAPI()


@app.get("/")
async def index():
    return FileResponse("./assets/index.html")


@app.post("/calculate")
async def calculate(num1: int, num2: int) -> dict:
    return {"result": num1 + num2}


@app.post("/user")
async def new_user(user: User) -> UserResponse:
    is_adult = user.age >= 18
    return UserResponse(
        name=user.name,
        age=user.age,
        is_adult=is_adult,
    )
