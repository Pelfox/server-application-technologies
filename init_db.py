from database import get_db_connection


def create_users_table() -> None:
    connection = get_db_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password TEXT NOT NULL
            )
            """,
        )
        connection.commit()
    finally:
        connection.close()


def create_todos_table() -> None:
    connection = get_db_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1))
            )
            """,
        )
        connection.commit()
    finally:
        connection.close()


def initialize_database() -> None:
    create_users_table()
    create_todos_table()


if __name__ == "__main__":
    initialize_database()
