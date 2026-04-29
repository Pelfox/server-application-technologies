from fastapi import status


class ForbiddenNoteTitleError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "forbidden_note_title"
    message = "Note title contains a forbidden word"


class NoteNotFoundError(Exception):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "note_not_found"
    message = "Requested note was not found"
