from typing import Annotated

from fastapi import Depends, FastAPI, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.exceptions import ForbiddenNoteTitleError, NoteNotFoundError
from app.models import Note
from app.schemas import (
    ErrorResponse,
    MessageResponse,
    NoteCreate,
    NoteRead,
    ValidationErrorItem,
    ValidationErrorResponse,
)

app = FastAPI()


def build_error_response(exc: ForbiddenNoteTitleError | NoteNotFoundError) -> JSONResponse:
    error = ErrorResponse(error_code=exc.error_code, message=exc.message)
    return JSONResponse(status_code=exc.status_code, content=error.model_dump())


@app.exception_handler(ForbiddenNoteTitleError)
def forbidden_note_title_error_handler(
    _: Request,
    exc: ForbiddenNoteTitleError,
) -> JSONResponse:
    return build_error_response(exc)


@app.exception_handler(NoteNotFoundError)
def note_not_found_error_handler(
    _: Request,
    exc: NoteNotFoundError,
) -> JSONResponse:
    return build_error_response(exc)


@app.exception_handler(RequestValidationError)
def request_validation_error_handler(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = [
        ValidationErrorItem(
            field=".".join(str(part) for part in error["loc"] if part != "body")
            or "request",
            message=error["msg"],
            error_type=error["type"],
        )
        for error in exc.errors()
    ]
    payload = ValidationErrorResponse(
        error_code="validation_error",
        message="Request validation failed",
        errors=errors,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=payload.model_dump(),
    )


@app.post(
    "/notes",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ValidationErrorResponse},
    },
)
def create_note(
    note: NoteCreate,
    session: Annotated[Session, Depends(get_session)],
) -> Note:
    if "forbidden" in note.title.lower():
        raise ForbiddenNoteTitleError()

    db_note = Note(**note.model_dump())
    session.add(db_note)
    session.commit()
    session.refresh(db_note)
    return db_note


@app.get("/notes", response_model=list[NoteRead])
def list_notes(
    session: Annotated[Session, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Note]:
    statement = select(Note).order_by(Note.id).limit(limit).offset(offset)
    return list(session.scalars(statement))


@app.get(
    "/notes/{note_id}",
    response_model=NoteRead,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
def get_note(
    note_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> Note:
    note = session.get(Note, note_id)
    if note is None:
        raise NoteNotFoundError()
    return note


@app.delete(
    "/notes/{note_id}",
    response_model=MessageResponse,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
def delete_note(
    note_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> MessageResponse:
    note = session.get(Note, note_id)
    if note is None:
        raise NoteNotFoundError()

    session.delete(note)
    session.commit()
    return MessageResponse(message="Note deleted successfully")
