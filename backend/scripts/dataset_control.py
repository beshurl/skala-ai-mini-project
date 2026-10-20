"""Offline intake/review CLI. Never auto-attests human review or history coverage."""
import argparse
import getpass
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.paths import PROJECT_ROOT
from recase.dataset_control import (PURPOSES, audit, exposure_entries, file_identity,
                                    latest_reviews, signature, subject_hash)
from recase.ledger import append_record, digest, read_ledger, utc_now


def load_rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def audit_files(candidates, history, reviews):
    entries = exposure_entries(history)
    history_rows = read_ledger(history)
    coverage = [e["payload"] for e in history_rows if e["payload"].get("kind") == "history_coverage"]
    complete = bool(coverage and coverage[-1].get("exposures_sha256") == digest(entries)
                    and coverage[-1].get("actor_kind") == "human_attestation")
    result = audit(load_rows(candidates), entries, latest_reviews(reviews) if Path(reviews).exists() else {}, complete)
    result["inputs"] = {"candidates": file_identity(candidates), "history": file_identity(history),
                        "reviews": file_identity(reviews) if Path(reviews).exists() else None}
    return result


def require_human():
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise PermissionError("Human review requires a local interactive terminal; no --yes/stdin automation")


def record_review(row, ledger):
    require_human()
    print(json.dumps(row, ensure_ascii=False, indent=2))
    print("검수 범위: 인명/주소/간접 식별자/문서 권리/라벨과 인용의 의미. 수정은 원본을 덮어쓰지 말고 새 후보로 작성하세요.")
    if input("이 자료를 직접 읽고 비식별화와 권리 근거를 검수했다면 '직접 검수 완료' 입력: ") != "직접 검수 완료":
        raise PermissionError("Review not attested")
    permissions = {}
    for use in sorted(PURPOSES):
        permissions[use] = input(f"{use} 목적을 별도로 승인합니까? (yes/기본 no): ") == "yes"
        if permissions[use] and row.get("permissions", {}).get(use) is not True:
            raise PermissionError("Source permission missing; obtain rights and create a new revision first")
    labels = input("정답 라벨/이유/근거를 직접 확인했습니까? (yes/기본 no): ") == "yes"
    note = input("검수 근거와 제한(필수): ").strip()
    if not note or not row.get("rights_basis", "").strip():
        raise PermissionError("Rights/review rationale required")
    return append_record(ledger, {"action": "approve", "subject_sha256": subject_hash(row),
                                 "reviewer": getpass.getuser(), "reviewer_uid": os.getuid(),
                                 "reviewed_at": utc_now(), "actor_kind": "human_attestation",
                                 "privacy_checked": True, "labels_checked": labels,
                                 "permissions": permissions, "note": note})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    history = sub.add_parser("register-legacy")
    history.add_argument("--source", default=str(PROJECT_ROOT / "data/processed"))
    history.add_argument("--history", required=True)
    check = sub.add_parser("audit")
    for key in ("candidates", "history", "reviews", "out"):
        check.add_argument("--" + key, required=True)
    review = sub.add_parser("review")
    review.add_argument("--candidates", required=True)
    review.add_argument("--sample-id", required=True)
    review.add_argument("--reviews", required=True)
    revoke = sub.add_parser("revoke")
    revoke.add_argument("--subject-sha256", required=True)
    revoke.add_argument("--reviews", required=True)
    coverage = sub.add_parser("attest-history")
    coverage.add_argument("--history", required=True)
    args = parser.parse_args()
    if args.action == "register-legacy":
        # Idempotent by source bytes + occurrence index, never silently relabel a
        # historical evaluation as blind. The old files remain unchanged.
        from scripts.data_audit import skeleton
        existing = exposure_entries(args.history) if Path(args.history).exists() else []
        keys = {e["occurrence"] for e in existing}
        count = 0
        for split, purpose in (("train", "training"), ("val", "validation"), ("test", "development_evaluation")):
            source = Path(args.source) / (split + ".jsonl")
            identity = file_identity(source)
            for number, row in enumerate(load_rows(source)):
                occurrence = digest([identity["sha256"], number, purpose])
                if occurrence in keys:
                    continue
                row["template_family"] = "legacy-" + digest(skeleton(row["prompt"]))
                append_record(args.history, {"kind": "exposure", "purpose": purpose,
                                             "occurrence": occurrence, "source": identity,
                                             "signature": signature(row), "evidence": "existing local dataset/run history"})
                keys.add(occurrence)
                count += 1
        print(json.dumps({"registered": count, "human_reviewed": False, "history_complete": False}))
    elif args.action == "audit":
        report = audit_files(args.candidates, args.history, args.reviews)
        write_new(args.out, report)
        print(json.dumps({"status": report["status"], "counts": report["issue_counts"], "out": args.out}))
        return 0 if report["status"] == "PASS" else 2
    elif args.action == "review":
        rows = [r for r in load_rows(args.candidates) if r.get("sample_id", r.get("doc_id")) == args.sample_id]
        if len(rows) != 1:
            raise ValueError("Exactly one matching sample required")
        record_review(rows[0], args.reviews)
    elif args.action == "revoke":
        require_human()
        if input("승인 철회 사유(필수): ").strip() == "":
            raise ValueError("Revocation rationale required")
        append_record(args.reviews, {"action": "revoke", "subject_sha256": args.subject_sha256,
                                    "reviewer": getpass.getuser(), "reviewed_at": utc_now()})
    else:
        require_human()
        print("기존 학습/검증/개발 평가/프롬프트·정답 열람/외부 모델 전송 이력까지 등록되어야 합니다.")
        note = input("확인한 이력의 범위와 누락 여부(필수): ").strip()
        if not note or input("전체 범위를 확인했다면 '이력 범위 확인' 입력: ") != "이력 범위 확인":
            raise PermissionError("History coverage not attested")
        append_record(args.history, {"kind": "history_coverage", "actor_kind": "human_attestation",
                                    "reviewer": getpass.getuser(), "reviewed_at": utc_now(), "scope": note,
                                    "exposures_sha256": digest(exposure_entries(args.history))})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
