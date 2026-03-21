from json import JSONDecodeError
from datetime import datetime
from time import time
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from itsdangerous import BadSignature, Signer
from pydantic import ValidationError

from models.auth import LoginRequest, SessionData, UserProfile
from models.headers import CommonHeaders
from models.product import Product
from models.user import UserCreate


app = FastAPI()

# Тестовые пользовательские данные для демонстрации
VALID_USERNAME = "user123"
VALID_PASSWORD = "password123"
SESSION_COOKIE_NAME = "session_token"
SESSION_IDLE_TIMEOUT_SECONDS = 300
SESSION_RENEWAL_THRESHOLD_SECONDS = 180
SESSION_COOKIE_MAX_AGE = SESSION_IDLE_TIMEOUT_SECONDS
SECRET_KEY = "server-application-technologies-secret-key"

user_profile = UserProfile(
    username=VALID_USERNAME,
    full_name="Test User",
    email="user123@example.com",
)
active_sessions: dict[str, SessionData] = {}
cookie_signer = Signer(SECRET_KEY)

# Тестовые данные продуктов для демонстрации
sample_product_1 = Product(
    product_id=123,
    name="Smartphone",
    category="Electronics",
    price=599.99,
)
sample_product_2 = Product(
    product_id=456,
    name="Phone Case",
    category="Accessories",
    price=19.99,
)
sample_product_3 = Product(
    product_id=789,
    name="Iphone",
    category="Electronics",
    price=1299.99,
)
sample_product_4 = Product(
    product_id=101,
    name="Headphones",
    category="Accessories",
    price=99.99,
)
sample_product_5 = Product(
    product_id=202,
    name="Smartwatch",
    category="Electronics",
    price=299.99,
)

sample_products = [
    sample_product_1,
    sample_product_2,
    sample_product_3,
    sample_product_4,
    sample_product_5,
]


async def parse_login_request(request: Request) -> LoginRequest:
    content_type = request.headers.get("Content-Type", "")

    try:
        if "application/json" in content_type:
            data = await request.json()
        elif (
            "application/x-www-form-urlencoded" in content_type
            or "multipart/form-data" in content_type
        ):
            form_data = await request.form()
            data = dict(form_data)
        else:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported media type",
            )
        return LoginRequest.model_validate(data)
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from error
    except JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON",
        ) from error


def get_current_timestamp() -> int:
    return int(time())


def create_session_token(user_id: str, last_activity: int) -> str:
    session_payload = f"{user_id}.{last_activity}"
    return cookie_signer.sign(session_payload.encode()).decode()


def parse_session_token(session_token: str | None) -> tuple[str, int] | None:
    if session_token is None:
        return None

    try:
        session_payload = cookie_signer.unsign(session_token).decode()
        user_id, last_activity_raw = session_payload.rsplit(".", 1)
        UUID(user_id)
        last_activity = int(last_activity_raw)
    except (BadSignature, ValueError, TypeError):
        return None

    return user_id, last_activity


def set_session_cookie(response: Response, session_token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=False,
        max_age=SESSION_COOKIE_MAX_AGE,
        samesite="lax",
    )


def build_session_error_response(message: str) -> JSONResponse:
    response = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"message": message},
    )
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


def serialize_common_headers(headers: CommonHeaders) -> dict[str, str]:
    return {
        "User-Agent": headers.user_agent,
        "Accept-Language": headers.accept_language,
    }


@app.exception_handler(RequestValidationError)
async def custom_request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = exc.errors()
    if errors and all(error.get("loc", [None])[0] == "header" for error in errors):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": jsonable_encoder(errors)},
        )
    return await request_validation_exception_handler(request, exc)


@app.post("/create_user", response_model=UserCreate, response_model_exclude_none=True)
async def create_user(user: UserCreate) -> UserCreate:
    return user


@app.get("/product/{product_id}", response_model=Product)
async def get_product(product_id: int) -> Product:
    for product in sample_products:
        if product.product_id == product_id:
            return product
    raise HTTPException(status_code=404, detail="Product not found")


@app.get("/products/search", response_model=list[Product], response_model_exclude_none=True)
async def search_products(
    keyword: str = Query(..., min_length=1),
    category: str | None = None,
    limit: int = Query(default=10, gt=0),
) -> list[Product]:
    filtered_products = [
        product
        for product in sample_products
        if keyword.lower() in product.name.lower()
    ]

    if category is not None:
        filtered_products = [
            product
            for product in filtered_products
            if product.category.lower() == category.lower()
        ]

    return filtered_products[:limit]


@app.post("/login")
async def login(request: Request) -> JSONResponse:
    credentials = await parse_login_request(request)
    if credentials.username != VALID_USERNAME or credentials.password != VALID_PASSWORD:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Unauthorized"},
        )

    user_id = str(uuid4())
    last_activity = get_current_timestamp()
    session_token = create_session_token(user_id, last_activity)
    active_sessions[user_id] = SessionData(
        profile=user_profile,
        last_activity=last_activity,
    )

    response = JSONResponse(content={"message": "Login successful"})
    set_session_cookie(response, session_token)
    return response


@app.get("/profile", response_model=UserProfile)
@app.get("/user", response_model=UserProfile)
async def get_user(request: Request, response: Response) -> UserProfile | JSONResponse:
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token is None:
        return build_session_error_response("Session expired")

    parsed_session_token = parse_session_token(session_token)
    current_timestamp = get_current_timestamp()
    if parsed_session_token is None:
        return build_session_error_response("Invalid session")

    user_id, last_activity = parsed_session_token
    session_data = active_sessions.get(user_id)

    if session_data is None:
        return build_session_error_response("Session expired")

    if last_activity != session_data.last_activity or last_activity > current_timestamp:
        return build_session_error_response("Invalid session")

    elapsed_seconds = current_timestamp - last_activity
    if elapsed_seconds >= SESSION_IDLE_TIMEOUT_SECONDS:
        active_sessions.pop(user_id, None)
        return build_session_error_response("Session expired")

    if elapsed_seconds >= SESSION_RENEWAL_THRESHOLD_SECONDS:
        session_data.last_activity = current_timestamp
        set_session_cookie(
            response,
            create_session_token(user_id, current_timestamp),
        )

    return session_data.profile


@app.get("/headers")
async def get_headers(headers: Annotated[CommonHeaders, Header()]) -> dict[str, str]:
    return serialize_common_headers(headers)


@app.get("/info")
async def get_info(
    response: Response,
    headers: Annotated[CommonHeaders, Header()],
) -> dict[str, object]:
    response.headers["X-Server-Time"] = datetime.now().isoformat(timespec="seconds")
    return {
        "message": "Добро пожаловать! Ваши заголовки успешно обработаны.",
        "headers": serialize_common_headers(headers),
    }
