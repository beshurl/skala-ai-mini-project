"""Multilingual dense RAG, persisted in SQLite. No silent lexical fallback."""
import hashlib
import json
import sqlite3
from pathlib import Path
from threading import RLock

import numpy as np
from langsmith import traceable


class RunbookIndex:
    def __init__(self, data_dir: Path, db_path: Path, model_name: str, backend="fastembed"):
        self.data_dir, self.model_name, self.backend = data_dir, model_name, backend
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("CREATE TABLE IF NOT EXISTS vectors (id TEXT PRIMARY KEY, fingerprint TEXT, body TEXT, vector TEXT)")
        self.model = None
        self.lock = RLock()
        self.documents = []

    def _embed(self, texts):
        if self.backend != "fastembed":
            raise ValueError("RAG_BACKEND는 fastembed만 지원합니다. 모델 준비 실패를 검색 성공으로 대체하지 않습니다.")
        if self.model is None:
            from fastembed import TextEmbedding
            self.model = TextEmbedding(model_name=self.model_name, threads=2,
                                       cache_dir=str(self.data_dir / ".embedding_cache"))
        return [np.asarray(v, dtype=np.float32) for v in self.model.embed(texts)]

    def prepare(self):
        with self.lock:
            paths = sorted((self.data_dir / "runbooks").glob("*.md"))
            docs = [(p.stem, p.read_text(encoding="utf-8")) for p in paths]
            prepared = []
            for doc_id, body in docs:
                fingerprint = hashlib.sha256((self.model_name + body).encode()).hexdigest()
                row = self.conn.execute("SELECT vector FROM vectors WHERE id=? AND fingerprint=?", (doc_id, fingerprint)).fetchone()
                vector = np.asarray(json.loads(row[0]), dtype=np.float32) if row else self._embed([body])[0]
                if row is None:
                    self.conn.execute("INSERT OR REPLACE INTO vectors VALUES (?,?,?,?)", (doc_id, fingerprint, body, json.dumps(vector.tolist())))
                prepared.append({"id": doc_id, "body": body, "vector": vector})
            self.conn.commit()
            self.documents = prepared
            if not self.documents:
                raise ValueError("검색할 Runbook 문서가 없습니다.")

    @traceable(name="rag.semantic_search", run_type="retriever")
    def search(self, query: str, top_k=3) -> list[dict]:
        with self.lock:
            if not self.documents:
                self.prepare()
            q = self._embed([query[:6000]])[0]
            scores = []
            for doc in self.documents:
                score = float(np.dot(q, doc["vector"]) / max(np.linalg.norm(q) * np.linalg.norm(doc["vector"]), 1e-12))
                scores.append((score, doc))
            return [{"id": "R:" + d["id"], "title": d["body"].splitlines()[0].lstrip("# "),
                     "uri": "runbook://incident-response/" + d["id"], "score": round(s, 4),
                     "text": d["body"], "model": self.model_name}
                    for s, d in sorted(scores, key=lambda x: x[0], reverse=True)[:top_k] if s >= 0.18]

    def close(self):
        self.conn.close()
