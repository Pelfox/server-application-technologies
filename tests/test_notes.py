from fastapi import status
from fastapi.testclient import TestClient


def create_note(client: TestClient, title: str = "Study FastAPI") -> dict:
    response = client.post(
        "/notes",
        json={
            "title": title,
            "content": "Write unit tests for the notes API",
            "is_published": False,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


class TestCreateNote:
    def test_create_note_returns_created_note(self, client: TestClient) -> None:
        data = create_note(client)

        assert data["id"] == 1
        assert data["title"] == "Study FastAPI"
        assert data["content"] == "Write unit tests for the notes API"
        assert data["is_published"] is False
        assert "created_at" in data

    def test_create_note_rejects_forbidden_title(self, client: TestClient) -> None:
        response = client.post(
            "/notes",
            json={
                "title": "Forbidden note",
                "content": "This content is long enough",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {
            "error_code": "forbidden_note_title",
            "message": "Note title contains a forbidden word",
        }

    def test_create_note_returns_validation_errors(self, client: TestClient) -> None:
        response = client.post(
            "/notes",
            json={
                "title": "No",
                "content": "short",
                "is_published": "true",
            },
        )

        data = response.json()
        error_fields = {error["field"] for error in data["errors"]}

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert data["error_code"] == "validation_error"
        assert data["message"] == "Request validation failed"
        assert error_fields == {"title", "content", "is_published"}


class TestReadNotes:
    def test_list_notes_returns_created_notes(self, client: TestClient) -> None:
        first_note = create_note(client, title="First note")
        second_note = create_note(client, title="Second note")
        response = client.get("/notes")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == [first_note, second_note]

    def test_list_notes_respects_limit(self, client: TestClient) -> None:
        create_note(client, title="First note")
        create_note(client, title="Second note")
        response = client.get("/notes", params={"limit": 1})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1

    def test_get_note_returns_note_by_id(self, client: TestClient) -> None:
        note = create_note(client)
        response = client.get(f"/notes/{note['id']}")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == note

    def test_get_note_returns_custom_not_found_error(self, client: TestClient) -> None:
        response = client.get("/notes/999")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {
            "error_code": "note_not_found",
            "message": "Requested note was not found",
        }


class TestDeleteNote:
    def test_delete_note_removes_existing_note(self, client: TestClient) -> None:
        note = create_note(client)
        delete_response = client.delete(f"/notes/{note['id']}")
        get_response = client.get(f"/notes/{note['id']}")

        assert delete_response.status_code == status.HTTP_200_OK
        assert delete_response.json() == {"message": "Note deleted successfully"}
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_note_returns_custom_not_found_error(
        self,
        client: TestClient,
    ) -> None:
        response = client.delete("/notes/999")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {
            "error_code": "note_not_found",
            "message": "Requested note was not found",
        }
