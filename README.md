# Технологии разработки серверных приложений

В данной ветке содержится реализация заданий для выполнения контрольной работы №3.

## Установка проекта

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python init_db.py
```

## Переменные окружения

Для `DEV`-режима задайте:

```bash
export MODE=DEV
export DOCS_USER=valid_user
export DOCS_PASSWORD=valid_password
```

Для `PROD`-режима достаточно:

```bash
export MODE=PROD
```

Для JWT можно дополнительно переопределить:

```bash
export JWT_SECRET_KEY=change-me-please-use-at-least-32-chars
export JWT_ALGORITHM=HS256
export ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Запуск проекта

```bash
uvicorn main:app --reload
```

Приложение будет доступно по адресу `http://127.0.0.1:8000`.

В `DEV` документация по `/docs` и `/openapi.json` защищена Basic Auth.
В `PROD` маршруты `/docs`, `/openapi.json` и `/redoc` скрыты и возвращают `404`.

## Todo CRUD

- `POST /todos` создаёт `Todo` и возвращает его с `completed=false`.
- `GET /todos/{todo_id}` возвращает один `Todo` или `404`.
- `PUT /todos/{todo_id}` обновляет `title`, `description`, `completed`.
- `DELETE /todos/{todo_id}` удаляет `Todo` и возвращает сообщение об успехе.
