from fastapi import FastAPI
from starlette.responses import FileResponse

app = FastAPI()


@app.get("/")
async def index():
    return FileResponse("./assets/index.html")
