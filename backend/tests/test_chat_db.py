import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from db.graph import conversations


def test_create_chat_initializes_schema(monkeypatch):
    db_path = Path(__file__).resolve().parent / "tmp_chat_regression.db"
    if db_path.exists():
        db_path.unlink()

    monkeypatch.setattr(conversations, "DB_PATH", db_path)

    chat = conversations.create_chat("user-123", "Test chat")

    assert chat["user_id"] == "user-123"
    assert chat["title"] == "Test chat"

    with sqlite3.connect(db_path) as conn:
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chats'"
        ).fetchone()
        assert table is not None

    db_path.unlink(missing_ok=True)
