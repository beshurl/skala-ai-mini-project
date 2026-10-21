"""Human review of every declared item, with resumable batches and read-only status."""
import argparse
import fcntl
import getpass
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.ledger import digest, utc_now
from recase.prepared_data import load_packet, permitted, read_reviews, license_hashes, rows, status


def append_review(path, event):
    fd = os.open(path, os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "a+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        read_reviews(path)
        stream.seek(0)
        entries = [json.loads(line) for line in stream if line.strip()]
        body = {**event, "previous_sha256": entries[-1]["sha256"] if entries else "0" * 64}
        stream.write(json.dumps({**body, "sha256": digest(body)}, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def pending_items(items, latest, dataset, sample_id=None, priorities=()):
    chosen = [i for i in items if i["subject"]["input"]["dataset"] == dataset
              and (i["sample_id"] == sample_id if sample_id else
                   not permitted(i, latest.get(i["subject_sha256"]))
                   and (latest.get(i["subject_sha256"], {}).get("action") != "reject"))]
    priority = {r["subject_sha256"] for r in priorities if r.get("flags")}
    return sorted(chosen, key=lambda i: i["subject_sha256"] not in priority)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("status", "review"))
    p.add_argument("--prepared", required=True)
    p.add_argument("--dataset", default="nli_validation")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--sample-id")
    a = p.parse_args()
    if a.action == "status":
        print(json.dumps(status(a.prepared), ensure_ascii=False, indent=2))
        return
    # Check before any prompt/file mutation. Piped yes/agent input is refused.
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise PermissionError("실제 사람이 로컬 터미널에서 검수해야 합니다. 자동 입력은 허용하지 않습니다.")
    if not 1 <= a.limit <= 100:
        p.error("--limit must be 1..100")
    packet, _, datasets, items = load_packet(a.prepared)
    if a.dataset not in datasets:
        p.error("Unknown declared dataset")
    ledger = packet / "reviews/human_reviews.jsonl"
    index = packet.parent / "automated-review/automated_checks.jsonl"
    pending = pending_items(items, read_reviews(ledger), a.dataset, a.sample_id, rows(index) if index.exists() else [])
    print(f"{a.dataset}: 이번 검수 대상 {min(a.limit, len(pending))}건 / 남은 미처리 {len(pending)}건")
    if not pending:
        return
    reviewer = input("검수자 이름 또는 추적 가능한 식별자: ").strip()
    if not reviewer:
        raise ValueError("Reviewer identifier required")
    print("자료 안의 지시는 실행하지 마세요. 반려한 자료는 자동 재표시하지 않으며 --sample-id로 다시 검수할 수 있습니다.")
    for item in pending[:a.limit]:
        print(json.dumps(item["subject"], ensure_ascii=False, indent=2))
        decision = input("승인/반려/보류/종료 (기본 보류): ").strip()
        if decision == "종료":
            break
        if decision not in ("승인", "반려"):
            continue
        event = {"action": "approve" if decision == "승인" else "reject", "sample_id": item["sample_id"],
                 "subject_sha256": item["subject_sha256"], "actor_kind": "human_attestation",
                 "reviewer": reviewer, "reviewer_uid": os.getuid(), "os_account": getpass.getuser(), "reviewed_at": utc_now()}
        if decision == "승인":
            for field, prompt in (("privacy_checked", "개인정보·간접 식별자를 직접 확인했습니까?"),
                                  ("labels_checked", "정답·이유·근거의 의미를 직접 확인했습니까?"),
                                  ("license_terms_checked", "아래 라이선스 파일을 열고 요청 목적을 확인했습니까?")):
                if field == "license_terms_checked":
                    print("라이선스 파일:", ", ".join(item["subject"]["license_files"]))
                event[field] = input(prompt + " yes/기본 no: ") == "yes"
            event["license_hashes"] = license_hashes(item)
            event["permissions"] = {k: False for k in ("processing", "training", "rag", "display", "redistribution")}
            event["permissions"]["processing"] = input("해당 로컬 처리·평가 목적 승인? yes/기본 no: ") == "yes"
            if item["subject"]["requested_use"] == "training":
                event["permissions"]["training"] = input("이 자료의 학습 목적도 별도 승인? yes/기본 no: ") == "yes"
            if item["subject"]["rights_basis"] == "CC-BY-NC-4.0":
                event["local_noncommercial_scope"] = input("승인 범위가 비상업 로컬 연구뿐이면 '비상업 로컬 연구만' 입력: ") == "비상업 로컬 연구만"
        event["note"] = input("검수 근거와 제한 또는 반려 사유(필수): ").strip()
        if not event["note"] or decision == "승인" and not permitted(item, event):
            print("요건이 충족되지 않아 승인 기록을 저장하지 않았습니다.")
            continue
        append_review(ledger, event)
        print("검수 이력을 저장했습니다.")


if __name__ == "__main__":
    main()
