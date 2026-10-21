"""Durable conversations, bounded context and investigation records (SQLite WAL)."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4

DB_PATH = Path(__file__).resolve().parent.parent / "session.db"


def now():
    return datetime.now(timezone.utc).isoformat()


class SqliteSessionStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._lock = RLock()
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS messages (thread_id TEXT, role TEXT, content TEXT, created TEXT);
            CREATE TABLE IF NOT EXISTS contexts (thread_id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS investigations (
                id TEXT PRIMARY KEY, thread_id TEXT, question TEXT, mode TEXT,
                targets TEXT, status TEXT, result TEXT, created TEXT);
        """)
        if "record_id" not in {r[1] for r in self.conn.execute("PRAGMA table_info(messages)")}:
            self.conn.execute("ALTER TABLE messages ADD COLUMN record_id TEXT")
        self.conn.commit()

    def load(self, thread_id: str, limit: int = 100) -> list[dict]:
        rows = self.conn.execute("SELECT role,content,record_id FROM (SELECT rowid,role,content,record_id FROM messages WHERE thread_id=? ORDER BY rowid DESC LIMIT ?) ORDER BY rowid", (thread_id, limit)).fetchall()
        return [{"role": r, "content": c, "record_id": record} for r, c, record in rows]

    def append(self, thread_id: str, role: str, content: str):
        with self._lock, self.conn:
            self.conn.execute("INSERT INTO messages(thread_id,role,content,created) VALUES (?,?,?,?)", (thread_id, role, content, now()))

    def context(self, thread_id: str) -> dict:
        row = self.conn.execute("SELECT data FROM contexts WHERE thread_id=?", (thread_id,)).fetchone()
        return json.loads(row[0]) if row else {}

    def memory(self, thread_id: str) -> list[dict]:
        context = self.context(thread_id)
        summary = context.get("summary", "")
        recent = self.load(thread_id, limit=8)
        return ([{"role": "system", "content": "이전 대화 요약(사용자 제공 정보): " + summary}] if summary else []) + recent

    def save_turn(self, thread_id: str, query: str, result: dict) -> str:
        record_id = str(uuid4())
        context = result.get("context", self.context(thread_id))
        # Extractive summary: do not invent details or run a paid summarizer.
        user_messages = [m["content"] for m in self.load(thread_id, 16) if m["role"] == "user"] + [query]
        context["summary"] = " / ".join(user_messages[-6:])[-1800:]
        with self._lock, self.conn:
            self.conn.executemany("INSERT INTO messages(thread_id,role,content,created,record_id) VALUES (?,?,?,?,?)", [
                (thread_id, "user", query, now(), record_id), (thread_id, "assistant", result["final"], now(), record_id)])
            self.conn.execute("INSERT OR REPLACE INTO contexts VALUES (?,?)", (thread_id, json.dumps(context, ensure_ascii=False)))
            self.conn.execute("INSERT INTO investigations VALUES (?,?,?,?,?,?,?,?)", (
                record_id, thread_id, result.get("effective_query", query), result.get("mode", "helpdesk"),
                json.dumps(result.get("targets", [])), result.get("status", "completed"),
                json.dumps({k: result.get(k) for k in ("report", "events", "validation", "collected", "elapsed_ms", "final", "scenario", "evidence_case", "investigation", "details", "model_usage", "tokens")}, ensure_ascii=False), now()))
        return record_id

    def records(self, thread_id: str) -> list[dict]:
        rows = self.conn.execute("SELECT id,question,mode,targets,status,result,created FROM investigations WHERE thread_id=? ORDER BY rowid DESC LIMIT 30", (thread_id,)).fetchall()
        return [dict(zip(("id", "question", "mode", "targets", "status", "result", "created"),
                         (r[0], r[1], r[2], json.loads(r[3]), r[4], json.loads(r[5]), r[6]))) for r in rows]

    def record(self, thread_id: str, record_id: str) -> dict | None:
        row = self.conn.execute("SELECT targets,mode,result FROM investigations WHERE thread_id=? AND id=?", (thread_id, record_id)).fetchone()
        return {"targets": json.loads(row[0]), "mode": row[1], **json.loads(row[2])} if row else None

    def close(self):
        self.conn.close()
