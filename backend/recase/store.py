"""SQLite state, immutable job snapshots and server-side ownership checks."""
import json
import secrets
import sqlite3
import time
import uuid
from contextlib import closing, contextmanager
from pathlib import Path
from recase import lifecycle
from recase.ledger import digest

TERMINAL = {"COMPLETED", "PARTIAL", "FAILED", "CANCELLED", "STALE"}


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


def uid(prefix):
    return prefix + "-" + uuid.uuid4().hex[:16]


class Store:
    def __init__(self, path, read_only=False):
        self.path = Path(path).resolve()
        self.read_only = read_only
        if read_only:
            if not self.path.is_file():
                raise FileNotFoundError(self.path)
            return
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.is_symlink():
            raise ValueError("Database symlinks are not supported")
        if not self.path.exists():
            self.path.touch(mode=0o600, exist_ok=False)
        self.path.chmod(0o600)
        with self.db() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > lifecycle.SCHEMA_VERSION:
                raise ValueError("Database schema is newer than this application")
            if version == 1:
                raise ValueError("MIGRATION_REQUIRED: back up and migrate lifecycle metadata before using schema2 code")
            if version == 0 and db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone():
                raise ValueError("Unversioned nonempty database refused")
            if version == 2:
                db.execute("SELECT case_id,created,closed,hold,data_class,revision FROM case_lifecycle LIMIT 0")
                db.execute("SELECT case_id,revision,action,actor,reason,at FROM case_lifecycle_events LIMIT 0")
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT NOT NULL,csrf TEXT NOT NULL,expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS cases(id TEXT PRIMARY KEY,owner TEXT NOT NULL,title TEXT NOT NULL,summary TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1);
                CREATE TABLE IF NOT EXISTS evidence(id TEXT PRIMARY KEY,case_id TEXT NOT NULL,title TEXT NOT NULL,text TEXT NOT NULL,kind TEXT NOT NULL,attributes TEXT NOT NULL,released_version INTEGER,release_order INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS claims(id TEXT PRIMARY KEY,case_id TEXT NOT NULL,text TEXT NOT NULL,attributes TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,case_id TEXT NOT NULL,owner TEXT NOT NULL,version INTEGER NOT NULL,status TEXT NOT NULL,snapshot TEXT NOT NULL,result TEXT,error TEXT,model TEXT NOT NULL,created REAL NOT NULL,updated REAL NOT NULL,cancel_requested INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,job_id TEXT NOT NULL,type TEXT NOT NULL,payload TEXT NOT NULL,created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT NOT NULL,action TEXT NOT NULL,resource TEXT NOT NULL,created REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS jobs_owner_case ON jobs(owner,case_id,created);
            """)
            if version == 0:
                for statement in lifecycle.TABLES:
                    db.execute(statement)
                db.execute("PRAGMA user_version=2")

    @contextmanager
    def db(self):
        db = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True, timeout=10) if self.read_only else sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def audit(self, actor, action, resource):
        with self.db() as db:
            db.execute("INSERT INTO audit(actor,action,resource,created) VALUES(?,?,?,?)", (actor, action, resource, time.time()))

    def seed_demo(self, user, fresh=False):
        """Seed only on an explicit authenticated action; preserve account ownership."""
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            if not fresh and db.execute("SELECT 1 FROM cases WHERE owner=?", (user,)).fetchone():
                return
            for title, summary, place in [
                ("사라진 연구 노트", "연구 노트가 사라진 날의 방문 진술과 출입 기록을 대조합니다. 모든 인물과 기록은 합성 자료입니다.", "연구실"),
                ("보관실의 출입 기록", "신원 확인이 불완전한 기록을 검토하고 새 자료가 판단에 주는 영향을 확인합니다. 합성 시뮬레이션입니다.", "보관실")]:
                case = uid("CASE")
                db.execute("INSERT INTO cases VALUES(?,?,?,?,1)", (case, user, title, summary))
                created = time.time()
                db.execute("INSERT INTO case_lifecycle VALUES(?,?,NULL,0,'synthetic_fixture',1)", (case, created))
                db.execute("INSERT INTO case_lifecycle_events VALUES(?,1,'create',?,?,?)", (case, user, "new synthetic demo", created))
                items = [
                    ("방문에 관한 진술", f"인물 A는 2026년 10월 10일 {place}에 간 적이 없다고 진술했다.", "statement", {"subject": "A", "place": place, "date": "2026-10-10", "assertion": "never_visited"}, 1),
                    ("신원 미확인 출입 기록", f"같은 날 {place} 출입 장치에 출입 흔적이 남았다. 출입자의 신원은 확인되지 않았다.", "record", {"place": place, "date": "2026-10-10", "identity_verified": False}, 1),
                    ("본인 확인이 완료된 기록", f"본인 확인이 완료된 출입 기록에 인물 A가 2026년 10월 10일 {place}에 입장한 사실이 남아 있다. 시각은 21:00 Asia/Seoul이며 기기 오차는 ±1분이다.", "record", {"subject": "A", "place": place, "date": "2026-10-10", "identity_verified": True, "event": "entered"}, None),
                    ("주변 날씨 기록", "같은 날 인근 관측소에는 맑은 날씨로 기록되었다. 출입자의 신원이나 방문 사실을 확인하는 자료는 아니다.", "record", {"topic": "weather"}, None),
                ]
                for i, (name, text, kind, attrs, released) in enumerate(items):
                    db.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?)", (uid("E"), case, name, text, kind, json.dumps(attrs, ensure_ascii=False), released, i))
                db.execute("INSERT INTO claims VALUES(?,?,?,?)", (uid("C"), case, f"인물 A의 '{place}에 방문한 적 없다'는 진술과 기록의 관계", json.dumps({"subject": "A", "place": place, "date": "2026-10-10", "assertion": "never_visited"})))
        self.audit(user, "demo_created", user)

    def new_demo(self):
        """Internal synthetic-fixture helper retained for operational copy tests."""
        user, token, csrf = uid("demo"), secrets.token_urlsafe(32), secrets.token_urlsafe(24)
        self.seed_demo(user)
        with self.db() as db:
            db.execute("INSERT INTO sessions VALUES(?,?,?,?)", (token, user, csrf, time.time() + 86400))
        return {"user_id": user, "token": token, "csrf": csrf, "mode": "local_demo"}

    def session(self, token):
        with self.db() as db:
            row = db.execute("SELECT * FROM sessions WHERE token=? AND expires>?", (token, time.time())).fetchone()
        if not row:
            raise NotFound()
        return dict(row)

    def create_synthetic_case(self, owner, creation_id, title, summary, claims, evidence):
        """Explicit user-authored synthetic input; no original-file ingestion."""
        case_id, now = "CASE-" + digest([owner, creation_id])[:20], time.time()
        fingerprint = digest([title, summary, claims, evidence])
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT owner FROM cases WHERE id=?", (case_id,)).fetchone()
            if existing:
                stored = db.execute("SELECT attributes FROM claims WHERE case_id=?", (case_id,)).fetchall()
                if existing["owner"] != owner or not stored or any(json.loads(r[0]).get("creation_fingerprint") != fingerprint for r in stored):
                    raise Conflict("CREATION_REQUEST_CONFLICT")
                return self.snapshot(owner, case_id)
            db.execute("INSERT INTO cases VALUES(?,?,?,?,1)", (case_id, owner, title, summary))
            db.execute("INSERT INTO case_lifecycle VALUES(?,?,NULL,0,'synthetic_fixture',1)", (case_id, now))
            db.execute("INSERT INTO case_lifecycle_events VALUES(?,1,'create',?,?,?)", (case_id, owner, "explicit user-authored synthetic case", now))
            for text in claims:
                db.execute("INSERT INTO claims VALUES(?,?,?,?)", (uid("C"), case_id, text, json.dumps({"analysis_mode":"general","source_type":"user_authored_synthetic","creation_fingerprint":fingerprint})))
            for i, item in enumerate(evidence):
                db.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?)", (uid("E"), case_id, item["title"], item["text"], item["kind"],
                           json.dumps({"source_type":"user_authored_synthetic"}), 1 if item["initially_released"] else None, i))
        self.audit(owner, "synthetic_case_created", case_id)
        return self.snapshot(owner, case_id)

    def cases(self, owner):
        with self.db() as db:
            return [dict(r) for r in db.execute("SELECT id,title,summary,version FROM cases WHERE owner=? ORDER BY rowid DESC", (owner,))]

    def snapshot(self, owner, case_id, version=None):
        with self.db() as db:
            case = db.execute("SELECT * FROM cases WHERE id=? AND owner=?", (case_id, owner)).fetchone()
            if not case:
                raise NotFound()
            if version is not None and version != case["version"]:
                raise Conflict("EVIDENCE_VERSION_CHANGED")
            evidence = [dict(r) for r in db.execute("SELECT id,title,text,kind,attributes,released_version FROM evidence WHERE case_id=? AND released_version<=? ORDER BY release_order", (case_id, case["version"]))]
            claims = [dict(r) for r in db.execute("SELECT id,text,attributes FROM claims WHERE case_id=?", (case_id,))]
            pending = db.execute("SELECT count(*) FROM evidence WHERE case_id=? AND released_version IS NULL", (case_id,)).fetchone()[0]
        for item in evidence + claims:
            item["attributes"] = json.loads(item["attributes"])
        return {"case_id": case_id, "title": case["title"], "summary": case["summary"], "evidence_version": case["version"],
                "source": "synthetic_fixture", "claims": claims, "evidence": evidence, "pending_count": pending}

    def release_next(self, owner, case_id, expected_version):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            case = db.execute("SELECT version FROM cases WHERE id=? AND owner=?", (case_id, owner)).fetchone()
            if not case:
                raise NotFound()
            if case["version"] != expected_version:
                raise Conflict("EVIDENCE_VERSION_CHANGED")
            lifecycle.require_open(db, owner, case_id)
            row = db.execute("SELECT id FROM evidence WHERE case_id=? AND released_version IS NULL ORDER BY release_order LIMIT 1", (case_id,)).fetchone()
            if not row:
                raise Conflict("NO_PENDING_EVIDENCE")
            version = case["version"] + 1
            db.execute("UPDATE cases SET version=? WHERE id=?", (version, case_id))
            db.execute("UPDATE evidence SET released_version=? WHERE id=?", (version, row["id"]))
        self.audit(owner, "evidence_released", case_id)
        return self.snapshot(owner, case_id)

    def create_job(self, owner, case_id, version, model):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            snapshot = self.snapshot(owner, case_id, version)
            lifecycle.require_open(db, owner, case_id)
            if db.execute("SELECT 1 FROM jobs WHERE owner=? AND case_id=? AND status IN ('QUEUED','RUNNING')", (owner, case_id)).fetchone():
                raise Conflict("JOB_ALREADY_ACTIVE")
            job_id, now = uid("JOB"), time.time()
            db.execute("INSERT INTO jobs(id,case_id,owner,version,status,snapshot,model,created,updated) VALUES(?,?,?,?,?,?,?,?,?)", (job_id, case_id, owner, version, "QUEUED", json.dumps(snapshot, ensure_ascii=False), json.dumps(model), now, now))
            db.execute("INSERT INTO events(job_id,type,payload,created) VALUES(?,?,?,?)", (job_id, "queued", "{}", now))
        self.audit(owner, "analysis_requested", job_id)
        return self.job(owner, job_id)

    def job(self, owner, job_id, private=False):
        with self.db() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=? AND owner=?", (job_id, owner)).fetchone()
        if not row:
            raise NotFound()
        result = dict(row)
        for key in ("snapshot", "result", "model"):
            result[key] = json.loads(result[key]) if result[key] else None
        conversation = result["snapshot"].get("conversation", {})
        result["kind"] = "conversation" if conversation.get("contract") == "case-conversation-v1" else "analysis"
        if result["kind"] == "conversation":
            result["question"] = conversation["question"]
            result["request_id"] = conversation["request_id"]
        if not private:
            result.pop("snapshot")
            result.pop("owner")
        return result

    def jobs(self, owner, case_id):
        self.snapshot(owner, case_id)
        with self.db() as db:
            ids = [r[0] for r in db.execute("SELECT id FROM jobs WHERE owner=? AND case_id=? AND json_extract(snapshot,'$.conversation.contract') IS NULL ORDER BY created DESC LIMIT 100", (owner, case_id))]
        return [self.job(owner, i) for i in ids]

    def event(self, job_id, event_type, payload=None):
        with self.db() as db:
            db.execute("INSERT INTO events(job_id,type,payload,created) VALUES(?,?,?,?)", (job_id, event_type, json.dumps(payload or {}, ensure_ascii=False), time.time()))

    def events(self, owner, job_id, after=0):
        self.job(owner, job_id)
        with self.db() as db:
            rows = db.execute("SELECT * FROM events WHERE job_id=? AND id>? ORDER BY id", (job_id, after)).fetchall()
        return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows]

    def set_status(self, owner, job_id, status, result=None, error=None):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            job = self.job(owner, job_id, private=True)
            if job["status"] in TERMINAL:
                return job["status"]
            if job["cancel_requested"] and status in ("COMPLETED", "PARTIAL"):
                status, result, error = "CANCELLED", None, "CANCELLED"
            current = db.execute("SELECT version FROM cases WHERE id=? AND owner=?", (job["case_id"], owner)).fetchone()
            if status in ("COMPLETED", "PARTIAL") and current[0] != job["version"]:
                status, result, error = "STALE", None, "EVIDENCE_VERSION_CHANGED"
            db.execute("UPDATE jobs SET status=?,result=?,error=?,updated=? WHERE id=?", (status, json.dumps(result, ensure_ascii=False) if result else None, error, time.time(), job_id))
            db.execute("INSERT INTO events(job_id,type,payload,created) VALUES(?,?,?,?)", (job_id, status.lower(), json.dumps({"status": status, "error": error}), time.time()))
        return status

    def cancel(self, owner, job_id):
        self.job(owner, job_id)
        with self.db() as db:
            db.execute("UPDATE jobs SET cancel_requested=1 WHERE id=? AND status IN ('QUEUED','RUNNING')", (job_id,))
        self.audit(owner, "analysis_cancelled", job_id)

    def recover(self):
        with self.db() as db:
            rows = db.execute("SELECT id FROM jobs WHERE status IN ('QUEUED','RUNNING')").fetchall()
            db.execute("UPDATE jobs SET status='FAILED',error='SERVER_RESTARTED',updated=? WHERE status IN ('QUEUED','RUNNING')", (time.time(),))
            for row in rows:
                db.execute("INSERT INTO events(job_id,type,payload,created) VALUES(?,?,?,?)", (row[0], "failed", '{"error":"SERVER_RESTARTED"}', time.time()))
        return len(rows)

    def lifecycle(self, owner, case_id):
        with self.db() as db:
            return lifecycle.state(db, owner, case_id)

    def transition_case(self, owner, case_id, expected_version, expected_revision, action, reason):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            return lifecycle.transition(db, owner, case_id, expected_version, expected_revision, action, reason)

    def backup(self, target):
        target = Path(target)
        if target.exists():
            raise FileExistsError(target)
        target.touch(mode=0o600, exist_ok=False)
        with self.db() as db, closing(sqlite3.connect(target)) as destination, destination:
            db.backup(destination)
        return target
