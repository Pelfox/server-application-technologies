import pytest
from faker import Faker
from fastapi import status
from httpx import AsyncClient


def build_note_payload(faker: Faker, title: str | None = None) -> dict:
    return {
        "title": title or faker.sentence(nb_words=3).rstrip("."),
        "content": faker.paragraph(nb_sentences=2),
        "is_published": faker.boolean(),
    }


async def create_note(
    async_client: AsyncClient,
    faker: Faker,
    title: str | None = None,
) -> dict:
    response = await async_client.post(
        "/notes",
        json=build_note_payload(faker, title=title),
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


@pytest.mark.asyncio
class TestAsyncCreateNote:
    async def test_create_note_with_faker_payload(
        self,
        async_client: AsyncClient,
        faker: Faker,
    ) -> None:
        payload = build_note_payload(faker)
        response = await async_client.post("/notes", json=payload)

        data = response.json()
        assert response.status_code == status.HTTP_201_CREATED
        assert data["title"] == payload["title"]
        assert data["content"] == payload["content"]
        assert data["is_published"] == payload["is_published"]
        assert "id" in data
        assert "created_at" in data

    async def test_create_note_rejects_boundary_values(
        self,
        async_client: AsyncClient,
    ) -> None:
        response = await async_client.post(
            "/notes",
            json={
                "title": "ab",
                "content": "too short",
                "is_published": "yes",
            },
        )

        data = response.json()
        fields = {error["field"] for error in data["errors"]}

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert data["error_code"] == "validation_error"
        assert fields == {"title", "content", "is_published"}

    async def test_create_note_rejects_custom_business_rule(
        self,
        async_client: AsyncClient,
        faker: Faker,
    ) -> None:
        payload = build_note_payload(faker, title="forbidden async note")
        response = await async_client.post("/notes", json=payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {
            "error_code": "forbidden_note_title",
            "message": "Note title contains a forbidden word",
        }


@pytest.mark.asyncio
class TestAsyncReadNotes:
    async def test_list_notes_returns_only_current_test_data(
        self,
        async_client: AsyncClient,
        faker: Faker,
    ) -> None:
        first_note = await create_note(async_client, faker, title="Async first note")
        second_note = await create_note(async_client, faker, title="Async second note")
        response = await async_client.get("/notes")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == [first_note, second_note]

    async def test_get_note_returns_created_note(
        self,
        async_client: AsyncClient,
        faker: Faker,
    ) -> None:
        note = await create_note(async_client, faker)
        response = await async_client.get(f"/notes/{note['id']}")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == note

    async def test_get_note_returns_not_found(
        self,
        async_client: AsyncClient,
    ) -> None:
        response = await async_client.get("/notes/999999")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {
            "error_code": "note_not_found",
            "message": "Requested note was not found",
        }


@pytest.mark.asyncio
class TestAsyncDeleteNote:
    async def test_delete_note_removes_created_note(
        self,
        async_client: AsyncClient,
        faker: Faker,
    ) -> None:
        note = await create_note(async_client, faker)
        delete_response = await async_client.delete(f"/notes/{note['id']}")
        get_response = await async_client.get(f"/notes/{note['id']}")

        assert delete_response.status_code == status.HTTP_200_OK
        assert delete_response.json() == {"message": "Note deleted successfully"}
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_note_returns_not_found(
        self,
        async_client: AsyncClient,
    ) -> None:
        response = await async_client.delete("/notes/999999")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {
            "error_code": "note_not_found",
            "message": "Requested note was not found",
        }
