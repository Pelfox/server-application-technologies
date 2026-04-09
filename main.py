import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from itertools import count
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)
from jwt import ExpiredSignatureError, InvalidTokenError
from passlib.context import CryptContext
from pydantic import ValidationError

from database import get_db_connection
from models import (
    AccessTokenResponse,
    MessageResponse,
    Resource,
    ResourceCreate,
    ResourceUpdate,
    TokenPayload,
    Todo,
    TodoCreate,
    TodoUpdate,
    User,
    UserCreate,
    UserInDB,
)
from rate_limit import InMemoryRateLimiter, RateLimitRule, create_rate_limit_dependency
from settings import Settings, get_settings

basic_security = HTTPBasic(auto_error=False)
docs_security = HTTPBasic(auto_error=False)
bearer_security = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

BASIC_AUTH_HEADERS = {"WWW-Authenticate": "Basic"}
BEARER_AUTH_HEADERS = {"WWW-Authenticate": "Bearer"}
DEFAULT_USERS = (
    UserCreate(username="admin", password="admin123", role="admin"),
    UserCreate(username="user123", password="password123", role="user"),
    UserCreate(username="guest", password="guest123", role="guest"),
)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def build_user_in_db(user: UserCreate) -> UserInDB:
    return UserInDB(
        username=user.username,
        hashed_password=get_password_hash(user.password),
        role=user.role,
    )


def create_fake_users_db() -> dict[str, UserInDB]:
    return {
        user.username: build_user_in_db(user)
        for user in DEFAULT_USERS
    }


fake_users_db = create_fake_users_db()
DUMMY_PASSWORD_HASH = get_password_hash("dummy-password-for-timing-attack-mitigation")
fake_resources_db: dict[int, Resource] = {
    1: Resource(
        id=1,
        title="Starter Resource",
        content="This resource is available for read operations.",
    ),
}
resource_id_sequence = count(start=max(fake_resources_db) + 1)


def basic_auth_exception(
    detail: str = "Invalid authentication credentials",
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers=BASIC_AUTH_HEADERS,
    )


def bearer_auth_exception(detail: str = "Invalid or expired token") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers=BEARER_AUTH_HEADERS,
    )


def get_user_by_username(username: str) -> UserInDB | None:
    for user in fake_users_db.values():
        if secrets.compare_digest(user.username, username):
            return user
    return None


def authenticate_user_credentials(username: str, password: str) -> UserInDB | None:
    user = get_user_by_username(username)
    hashed_password = user.hashed_password if user is not None else DUMMY_PASSWORD_HASH
    is_valid_password = verify_password(password, hashed_password)

    if user is None or not is_valid_password:
        return None

    return user


def auth_user(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(basic_security)],
) -> UserInDB:
    if credentials is None:
        raise basic_auth_exception()

    user = authenticate_user_credentials(
        credentials.username,
        credentials.password,
    )
    if user is None:
        raise basic_auth_exception()

    return user


def create_docs_auth_dependency(settings: Settings):
    def authenticate_docs_access(
        credentials: Annotated[HTTPBasicCredentials | None, Depends(docs_security)],
    ) -> None:
        if credentials is None:
            raise basic_auth_exception()

        is_valid_username = secrets.compare_digest(
            credentials.username,
            settings.docs_user or "",
        )
        is_valid_password = secrets.compare_digest(
            credentials.password,
            settings.docs_password or "",
        )

        if not (is_valid_username and is_valid_password):
            raise basic_auth_exception()

    return authenticate_docs_access


def create_access_token(subject: str, settings: Settings) -> str:
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes,
    )
    payload = {
        "sub": subject,
        "exp": expires_at,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_jwt_auth_dependency(settings: Settings):
    def get_current_user(
        credentials: Annotated[
            HTTPAuthorizationCredentials | None,
            Depends(bearer_security),
        ],
    ) -> UserInDB:
        if credentials is None:
            raise bearer_auth_exception("Missing bearer token")

        if not secrets.compare_digest(credentials.scheme.lower(), "bearer"):
            raise bearer_auth_exception("Invalid authentication scheme")

        try:
            payload = jwt.decode(
                credentials.credentials,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            token_payload = TokenPayload.model_validate(payload)
        except ExpiredSignatureError as error:
            raise bearer_auth_exception("Token has expired") from error
        except (InvalidTokenError, ValidationError) as error:
            raise bearer_auth_exception() from error

        user = get_user_by_username(token_payload.sub)
        if user is None:
            raise bearer_auth_exception()

        return user

    return get_current_user


def create_role_dependency(get_current_user, *allowed_roles: str):
    def require_role(
        user: Annotated[UserInDB, Depends(get_current_user)],
    ) -> UserInDB:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )

        return user

    return require_role


def get_resource_or_404(resource_id: int) -> Resource:
    resource = fake_resources_db.get(resource_id)
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    return resource


def map_todo_row_to_model(row: sqlite3.Row) -> Todo:
    return Todo(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        completed=bool(row["completed"]),
    )


def get_todo_or_404(connection: sqlite3.Connection, todo_id: int) -> Todo:
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, title, description, completed FROM todos WHERE id = ?",
        (todo_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )
    return map_todo_row_to_model(row)


def register_api_routes(app: FastAPI, settings: Settings) -> None:
    get_current_user = create_jwt_auth_dependency(settings)
    require_admin = create_role_dependency(get_current_user, "admin")
    require_admin_or_user = create_role_dependency(get_current_user, "admin", "user")
    require_read_access = create_role_dependency(
        get_current_user,
        "admin",
        "user",
        "guest",
    )
    limiter = InMemoryRateLimiter()
    register_rate_limit = create_rate_limit_dependency(
        limiter=limiter,
        scope="register",
        rule=RateLimitRule(max_requests=1, window_seconds=60),
    )
    login_rate_limit = create_rate_limit_dependency(
        limiter=limiter,
        scope="login",
        rule=RateLimitRule(max_requests=5, window_seconds=60),
    )

    @app.post(
        "/register",
        response_model=MessageResponse,
        dependencies=[Depends(register_rate_limit)],
    )
    def register(user: UserCreate) -> MessageResponse:
        if get_user_by_username(user.username) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists",
            )

        connection = get_db_connection()
        user_in_db = build_user_in_db(user)

        try:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (user.username, user.password),
            )
            connection.commit()
        except sqlite3.Error as error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error",
            ) from error
        finally:
            connection.close()

        fake_users_db[user_in_db.username] = user_in_db
        return MessageResponse(message="User registered successfully!")

    @app.get("/login", response_model=MessageResponse)
    def basic_login(user: Annotated[UserInDB, Depends(auth_user)]) -> MessageResponse:
        return MessageResponse(message=f"Welcome, {user.username}!")

    @app.post(
        "/login",
        response_model=AccessTokenResponse,
        dependencies=[Depends(login_rate_limit)],
    )
    def jwt_login(credentials: User) -> AccessTokenResponse:
        user = get_user_by_username(credentials.username)
        if user is None:
            verify_password(credentials.password, DUMMY_PASSWORD_HASH)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if not verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization failed",
            )

        access_token = create_access_token(user.username, settings)
        return AccessTokenResponse(access_token=access_token)

    @app.get("/protected_resource", response_model=MessageResponse)
    def protected_resource(
        user: Annotated[UserInDB, Depends(require_admin_or_user)],
    ) -> MessageResponse:
        return MessageResponse(
            message=f"Access granted for role {user.role}",
        )

    @app.post("/resources", response_model=Resource, status_code=status.HTTP_201_CREATED)
    def create_resource(
        resource: ResourceCreate,
        _: Annotated[UserInDB, Depends(require_admin)],
    ) -> Resource:
        resource_id = next(resource_id_sequence)
        stored_resource = Resource(
            id=resource_id,
            title=resource.title,
            content=resource.content,
        )
        fake_resources_db[resource_id] = stored_resource
        return stored_resource

    @app.get("/resources/{resource_id}", response_model=Resource)
    def get_resource(
        resource_id: int,
        _: Annotated[UserInDB, Depends(require_read_access)],
    ) -> Resource:
        return get_resource_or_404(resource_id)

    @app.put("/resources/{resource_id}", response_model=Resource)
    def update_resource(
        resource_id: int,
        resource: ResourceUpdate,
        _: Annotated[UserInDB, Depends(require_admin_or_user)],
    ) -> Resource:
        existing_resource = get_resource_or_404(resource_id)
        updated_resource = existing_resource.model_copy(
            update={
                "title": resource.title,
                "content": resource.content,
            },
        )
        fake_resources_db[resource_id] = updated_resource
        return updated_resource


def register_todo_routes(app: FastAPI) -> None:
    @app.post("/todos", response_model=Todo, status_code=status.HTTP_201_CREATED)
    def create_todo(todo: TodoCreate) -> Todo:
        connection = get_db_connection()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO todos (title, description, completed)
                VALUES (?, ?, ?)
                """,
                (todo.title, todo.description, 0),
            )
            connection.commit()
            todo_id = cursor.lastrowid
            if todo_id is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create todo",
                )
            return Todo(
                id=todo_id,
                title=todo.title,
                description=todo.description,
                completed=False,
            )
        except sqlite3.Error as error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error",
            ) from error
        finally:
            connection.close()

    @app.get("/todos/{todo_id}", response_model=Todo)
    def get_todo(todo_id: int) -> Todo:
        connection = get_db_connection()
        try:
            return get_todo_or_404(connection, todo_id)
        finally:
            connection.close()

    @app.put("/todos/{todo_id}", response_model=Todo)
    def update_todo(todo_id: int, todo: TodoUpdate) -> Todo:
        connection = get_db_connection()
        try:
            get_todo_or_404(connection, todo_id)
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE todos
                SET title = ?, description = ?, completed = ?
                WHERE id = ?
                """,
                (todo.title, todo.description, int(todo.completed), todo_id),
            )
            connection.commit()
            return Todo(
                id=todo_id,
                title=todo.title,
                description=todo.description,
                completed=todo.completed,
            )
        except sqlite3.Error as error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error",
            ) from error
        finally:
            connection.close()

    @app.delete("/todos/{todo_id}", response_model=MessageResponse)
    def delete_todo(todo_id: int) -> MessageResponse:
        connection = get_db_connection()
        try:
            get_todo_or_404(connection, todo_id)
            cursor = connection.cursor()
            cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            connection.commit()
            return MessageResponse(message="Todo deleted successfully!")
        except sqlite3.Error as error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error",
            ) from error
        finally:
            connection.close()


def register_docs_routes(app: FastAPI, settings: Settings) -> None:
    if settings.mode != "DEV":
        return

    authenticate_docs_access = create_docs_auth_dependency(settings)

    @app.get("/openapi.json", include_in_schema=False)
    def openapi_json(
        _: Annotated[None, Depends(authenticate_docs_access)],
    ) -> JSONResponse:
        return JSONResponse(app.openapi())

    @app.get("/docs", include_in_schema=False)
    def swagger_ui(
        _: Annotated[None, Depends(authenticate_docs_access)],
    ) -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title=f"{app.title} - Swagger UI",
        )


def create_app(settings: Settings | None = None) -> FastAPI:
    current_settings = settings or get_settings()
    app = FastAPI(
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    register_api_routes(app, current_settings)
    register_todo_routes(app)
    register_docs_routes(app, current_settings)

    return app


app = create_app()
