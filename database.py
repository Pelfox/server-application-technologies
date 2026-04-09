import sqlite3
from pathlib import Path


DATABASE_PATH = Path(__file__).resolve().parent / "db.sqlite3"


def get_db_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection
