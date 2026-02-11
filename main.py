from fastapi import FastAPI
from starlette.responses import FileResponse

from models.user import User

app = FastAPI()
existing_user = User(id=1, name="Ваше Имя и Фамилия")


@app.get("/")
async def index():
    return FileResponse("./assets/index.html")


@app.post("/calculate")
async def calculate(num1: int, num2: int) -> dict:
    return {"result": num1 + num2}


@app.get("/users")
async def users() -> User:
    return existing_user
