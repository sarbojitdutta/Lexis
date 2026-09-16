import sqlite3
import uuid
import json
from datetime import datetime
from pathlib import Path


DB_PATH = Path(__file__).parent / "graph.db"


def init_conversation_tables(conn=None):
    close_conn = conn is None
    conn = conn or sqlite3.connect(DB_PATH)

    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT,
                created_at DATETIME NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN('user','assistant')),
                content TEXT NOT NULL,
                citations TEXT,
                created_at DATETIME NOT NULL,

                FOREIGN KEY (chat_id)
                    REFERENCES chats(id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_chats_user_id
            ON chats(user_id);

            CREATE INDEX IF NOT EXISTS idx_messages_chat_id
            ON messages(chat_id);

            CREATE INDEX IF NOT EXISTS idx_messages_created_at
            ON messages(created_at);
         """)
        conn.commit()
    finally:
        if close_conn:
            conn.close()


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_conversation_tables(conn=conn)
    return conn


def create_chat(user_id: str, title: str | None = None):
    chat_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    conn = get_connection()

    try:
        conn.execute(
            """
                INSERT INTO chats (id, user_id, title, created_at)
                VALUES (?, ?, ?, ?)
            """,
            (chat_id, user_id, title, created_at)
        )
        conn.commit()

        return {
            "id": chat_id,
            "user_id": user_id,
            "title": title,
            "created_at": created_at
        }
    finally:
        conn.close()


def save_messages(chat_id: str, role: str, content: str, citations: list | None = None):
    message_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    citations_json = json.dumps(citations) if citations else None

    conn = get_connection()

    try:
        conn.execute(
            """
            INSERT INTO messages (
                id, chat_id, role, content, citations, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                chat_id,
                role,
                content,
                citations_json,
                created_at
            )
        )
        conn.commit()

        return {
            "id": message_id,
            "chat_id": chat_id,
            "role": role,
            "content": content,
            "citations": citations,
            "created_at": created_at
        }
    finally:
        conn.close()


# Singular alias used by the query endpoint.
def save_message(chat_id: str, role: str, content: str, citations: list | None = None):
    return save_messages(chat_id, role, content, citations)


def chat_history(chat_id: str, limit: int = 20):
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT id, chat_id, role, content, citations, created_at
            FROM messages
            WHERE chat_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (chat_id, limit)
        ).fetchall()

        rows = list(reversed(rows))

        return [
            {
                "id": row["id"],
                "chat_id": row["chat_id"],
                "role": row["role"],
                "content": row["content"],
                "citations": json.loads(row["citations"]) if row["citations"] else None,
                "created_at": row["created_at"]
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_users_chat(user_id: str):
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT id, user_id, title, created_at
            FROM chats
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_chat(chat_id: str, user_id: str):
    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT id, user_id, title, created_at
            FROM chats
            WHERE id = ? AND user_id = ?
            """,
            (chat_id, user_id)
        ).fetchone()

        return dict(row) if row else None
    finally:
        conn.close()


def delete_chat(chat_id: str, user_id: str):
    conn = get_connection()

    try:
        cur = conn.execute(
            """
            DELETE FROM chats
            WHERE id = ? AND user_id = ?
            """,
            (chat_id, user_id)
        )

        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
