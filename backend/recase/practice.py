"""Explicit account-owned synthetic practice. No labels or reviewer notes are loaded."""
import hashlib
import json
import time
from functools import lru_cache

from recase.paths import PROJECT_ROOT

BUNDLE = PROJECT_ROOT / "data/practice/v1/cases.json"


@lru_cache(maxsize=1)
def bundle():
    raw = BUNDLE.read_bytes()
    data = json.loads(raw)
    if data.get("schema") != "recase_user_practice_v1" or data.get("source") != "AI_AUTHORED_SYNTHETIC" or data.get("training_eligible") is not False:
        raise ValueError("Unrecognized practice bundle")
    if any(key in raw.decode() for key in ('"proposed_relation"', '"expected_label"', '"next_check"')):
        raise ValueError("Review references must not enter the service bundle")
    cases = data["cases"]
    if len({c["id"] for c in cases}) != len(cases):
        raise ValueError("Duplicate practice case")
    for case in cases:
        evidence = case["evidence"]
        keys = {e["key"] for e in evidence}
        if len(keys) != len(evidence) or case["case_status"] != "UNRESOLVED":
            raise ValueError("Invalid practice evidence")
        if [s["version"] for s in case["stages"]] != [1, 2, 3]:
            raise ValueError("Practice stages must be ordered")
        for stage in case["stages"]:
            if set(stage["release_keys"]) != {e["key"] for e in evidence if e["release_at"] == stage["version"]}:
                raise ValueError("Evidence release order differs from the stage")
        if not all(e["release_at"] in (1, 2, 3) and e["text"].strip() and e["origin"]["type"] == "synthetic_authored" for e in evidence):
            raise ValueError("Only authored synthetic evidence is supported")
        if case["automatic_demo"] and (len(case["claims"]) != 1 or len(evidence) != 4 or [e["release_at"] for e in evidence] != [1, 1, 2, 3]):
            raise ValueError("Practice demo exceeds the current service capability")
    return data, hashlib.sha256(raw).hexdigest()


def seed_practice(store, owner, general=False):
    """Append three supported demos once; never reset evidence or analysis history."""
    data, revision = bundle()
    selected = data["cases"] if general else [c for c in data["cases"] if c["automatic_demo"]]
    if not general and [c["id"] for c in selected] != ["P01", "P02", "P03"]:
        raise ValueError("Unexpected automatic practice scope")

    def identifier(prefix, key):
        return prefix + "-" + hashlib.sha256((owner + revision + ("general" if general else "") + key).encode()).hexdigest()[:20]

    created, identifiers = 0, []
    with store.db() as db:
        db.execute("BEGIN IMMEDIATE")
        for case in selected:
            case_id = identifier("CASE", case["id"])
            identifiers.append(case_id)
            exists = db.execute("SELECT owner FROM cases WHERE id=?", (case_id,)).fetchone()
            if exists:
                if exists["owner"] != owner:
                    raise ValueError("Practice owner mismatch")
                continue
            now = time.time()
            db.execute("INSERT INTO cases(id,owner,title,summary,version) VALUES(?,?,?,?,1)",
                       (case_id, owner, ("다중 증거 검토 · " if general else "") + case["title"], case["summary"]))
            db.execute("INSERT INTO case_lifecycle VALUES(?,?,NULL,0,'synthetic_fixture',1)", (case_id, now))
            db.execute("INSERT INTO case_lifecycle_events VALUES(?,1,'create',?,?,?)", (case_id, owner, "explicit synthetic practice", now))
            for order, e in enumerate(case["evidence"]):
                attrs = {**e["attributes"], "source_type": "synthetic_authored", "source_document": e["origin"]["document_id"]}
                db.execute("INSERT INTO evidence(id,case_id,title,text,kind,attributes,released_version,release_order) VALUES(?,?,?,?,?,?,?,?)",
                           (identifier("E", e["key"]), case_id, e["title"], e["text"], e["kind"], json.dumps(attrs, ensure_ascii=False), 1 if e["release_at"] == 1 else None, order))
            for claim in case["claims"]:
                db.execute("INSERT INTO claims(id,case_id,text,attributes) VALUES(?,?,?,?)",
                           (identifier("C", claim["key"]), case_id, claim["text"], json.dumps({**claim["attributes"], **({"analysis_mode":"general"} if general else {})}, ensure_ascii=False)))
            created += 1
    store.audit(owner, "practice_opened", revision)
    return {"created": created, "total": len(identifiers), "case_ids": identifiers, "source": "synthetic_authored", "human_reviewed": False}
