from fastapi import FastAPI
from starlette.responses import FileResponse

app = FastAPI()


@app.get("/")
async def index():
    return FileResponse("./assets/index.html")


@app.post("/calculate")
async def calculate(num1: int, num2: int) -> dict:
    return {"result": num1 + num2}
