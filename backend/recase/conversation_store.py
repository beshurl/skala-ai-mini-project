"""Case conversation turns stored in existing immutable jobs; no schema migration."""
import json
import time

from recase import lifecycle
from recase.ledger import digest
from recase.store import Conflict, NotFound

CONTRACT = "case-conversation-v1"
HISTORY_TURNS = 3
PAGE_SIZE = 20


def request_job_id(owner, case_id, request_id):
    return "JOB-" + digest([CONTRACT, owner, case_id, request_id])[:16]


def replay_turn(store, owner, case_id, version, request_id, question, after_turn_id):
    store.snapshot(owner, case_id)  # Authorization precedes request lookup.
    try:
        job = store.job(owner, request_job_id(owner, case_id, request_id), private=True)
    except NotFound:
        return None
    expected = digest([version, question, after_turn_id])
    metadata = job["snapshot"].get("conversation", {})
    if (job["case_id"] != case_id or metadata.get("contract") != CONTRACT
            or metadata.get("request_id") != request_id or metadata.get("fingerprint") != expected):
        raise Conflict("CHAT_REQUEST_CONFLICT")
    return store.job(owner, job["id"])


def create_turn(store, owner, case_id, version, request_id, question, after_turn_id, model):
    with store.db() as db:
        db.execute("BEGIN IMMEDIATE")
        prior = replay_turn(store, owner, case_id, version, request_id, question, after_turn_id)
        if prior:
            return prior, False
        snapshot = store.snapshot(owner, case_id, version)
        if lifecycle.state(db, owner, case_id)["data_class"] != "synthetic_fixture":
            raise Conflict("CASE_PROVENANCE_REVIEW_REQUIRED")
        lifecycle.require_open(db, owner, case_id)
        latest = db.execute("SELECT id FROM jobs WHERE owner=? AND case_id=? AND json_extract(snapshot,'$.conversation.contract')=? ORDER BY created DESC,rowid DESC LIMIT 1", (owner, case_id, CONTRACT)).fetchone()
        if after_turn_id != (latest["id"] if latest else None):
            raise Conflict("CHAT_HISTORY_CHANGED")
        if db.execute("SELECT 1 FROM jobs WHERE owner=? AND case_id=? AND status IN ('QUEUED','RUNNING')", (owner, case_id)).fetchone():
            raise Conflict("JOB_ALREADY_ACTIVE")
        rows = db.execute("SELECT id,version,snapshot,result FROM jobs WHERE owner=? AND case_id=? AND status='COMPLETED' AND json_extract(snapshot,'$.conversation.contract')=? ORDER BY created DESC,rowid DESC LIMIT ?", (owner, case_id, CONTRACT, HISTORY_TURNS)).fetchall()
        history = []
        for row in reversed(rows):
            answer = json.loads(row["result"])["conversation"]
            history.append({"turn_id": row["id"], "evidence_version": row["version"],
                            "question": json.loads(row["snapshot"])["conversation"]["question"],
                            "paragraphs": [p["text"] for p in answer["paragraphs"]],
                            "missing_information": answer["missing_information"]})
        snapshot["conversation"] = {"contract": CONTRACT, "request_id": request_id, "question": question,
                                    "after_turn_id": after_turn_id, "fingerprint": digest([version, question, after_turn_id]),
                                    "history": history, "history_limit": HISTORY_TURNS}
        job_id, now = request_job_id(owner, case_id, request_id), time.time()
        db.execute("INSERT INTO jobs(id,case_id,owner,version,status,snapshot,model,created,updated) VALUES(?,?,?,?,?,?,?,?,?)", (job_id, case_id, owner, version, "QUEUED", json.dumps(snapshot, ensure_ascii=False), json.dumps(model), now, now))
        db.execute("INSERT INTO events(job_id,type,payload,created) VALUES(?,?,?,?)", (job_id, "queued", "{}", now))
        db.execute("INSERT INTO audit(actor,action,resource,created) VALUES(?,?,?,?)", (owner, "conversation_requested", job_id, now))
    return store.job(owner, job_id), True


def list_turns(store, owner, case_id, before=None):
    snapshot = store.snapshot(owner, case_id)
    with store.db() as db:
        boundary, args = "", [owner, case_id, CONTRACT]
        if before:
            cursor = db.execute("SELECT created,rowid FROM jobs WHERE id=? AND owner=? AND case_id=? AND json_extract(snapshot,'$.conversation.contract')=?", (before, owner, case_id, CONTRACT)).fetchone()
            if not cursor:
                raise NotFound()
            boundary = " AND (created<? OR (created=? AND rowid<?))"
            args += [cursor["created"], cursor["created"], cursor["rowid"]]
        rows = db.execute("SELECT id FROM jobs WHERE owner=? AND case_id=? AND json_extract(snapshot,'$.conversation.contract')=?" + boundary + " ORDER BY created DESC,rowid DESC LIMIT ?", (*args, PAGE_SIZE + 1)).fetchall()
        selected = rows[:PAGE_SIZE]
        latest = db.execute("SELECT id FROM jobs WHERE owner=? AND case_id=? AND json_extract(snapshot,'$.conversation.contract')=? ORDER BY created DESC,rowid DESC LIMIT 1", (owner, case_id, CONTRACT)).fetchone()
    return {"case_id": case_id, "evidence_version": snapshot["evidence_version"],
            "turns": [store.job(owner, row["id"]) for row in reversed(selected)],
            "latest_turn_id": latest["id"] if latest else None,
            "next_before": selected[-1]["id"] if len(rows) > PAGE_SIZE else None,
            "history_limit": HISTORY_TURNS}
