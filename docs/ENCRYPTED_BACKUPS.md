# 로컬 암호화 백업·복구 검증

**2026-10-21 계정 확장:** 새 [ACCOUNT_RECOVERY](ACCOUNT_RECOVERY.md)의 account_backup.py가 사건/계정 이미지를 별도 키로 암호화한 pair와 현재 계정 DB를 유지하는 사건 복구를 검사합니다.195 backend/14 frontend·123파일 합성 후보 PASS이며 실제 UID499 미적용입니다. 과거 계정 자동 복원/폐기·계정 DB 소실 복구는 미완료입니다. 아래 메인 DB 전용 proof는 계정 복구 증명이 아닙니다.

현재 상태는 **소스 구현·새 합성 사본 검증 / UID499 미적용**이다. [암호화 기능 실행 결과](../outputs/runs/20261020T170913+0900-encrypted-backups-0d84fb/RESULT.txt), [비활성90/30일 초안](../data/local_operations_policy.90d-30d.encrypted.proposed.json)을 따른다. 이후 [119파일 후보·전환 검사](RELEASE_TRANSITION.md)에 새 모듈/CLI·의존성·명시적 SQLite close 수정을 포함해 재생성했고 후보 안의 암호화 생성/복구도 확인했다. 전체174 tests PASS다. 앞선115파일 후보는 당시 버전으로 보존했다. 활성 수동 정책은 그대로이며 자동 삭제·스케줄러·백업/키 폐기 실행기는 없다.

`backend/scripts/encrypted_backup.py`는 `backup`, `verify`, `inventory`만 지원한다. 설치된 lock의 cryptography50.0.2를 재사용하며 app 의존성에도 선언했다. [cryptography50 공식 AESGCM API](https://cryptography.io/en/50.0.0/hazmat/primitives/aead/#cryptography.hazmat.primitives.ciphers.aead.AESGCM)를 사용한다. 백업마다 새256-bit 키와96-bit nonce를 생성하고 그 키를 하나의 변경 불가 암호문에만 사용한다. 컨테이너 헤더의 형식·시각·자료 분류·보류·사건 SHA 목록·평문 SHA/크기는 AAD로 인증한다. 키 바이트는 헤더/receipt/로그에 넣지 않는다.

생성은 읽기 전용 SQLite backup API로 커밋된 WAL까지 메모리에 일관되게 복사한 뒤 바로 암호화한다. 생성 중 별도 평문 백업 파일을 만들지 않는다. 스냅샷128MiB/15초·사건1000개, inventory100백업/키/증명의 한도가 있다. 실제128MiB 최대 크기/운영 부하는 미측정이다. 새로운 nonroot 사용자 소유의0700 디렉터리·0600 일반 파일·독립 inode를 요구하며 기존 파일·symlink/상위 경로·키와 백업의 같은/중첩 디렉터리를 거부한다. Mac의 대소문자 무시 경로도 디렉터리 inode 계열로 확인한다. 중간 실패의 새 키/파일은 자동 제거하지 않는다.

다음은 새 합성 사본용 경로 예시다. 실제 운영 DB는 서비스 계정의 현재 작업 진단·관리자 인증·배포 검증 뒤 별도 계획으로 다룬다. 실제 키 값은 명령 인자·채팅·환경변수에 넣지 않는다. 아래 `--key`는 새 파일 경로이며 도구가 키를 생성한다. KEY_DIR와 BACKUP_DIR는 서로 포함되지 않는 별도0700 디렉터리로 미리 준비한다. 보고서 상위 폴더도0700이어야 한다.

```bash
.venv/bin/python backend/scripts/encrypted_backup.py backup \
  --db PRIVATE_SYNTHETIC_CASES.db \
  --target BACKUP_DIR/new.recase --receipt BACKUP_DIR/new.json \
  --key KEY_DIR/new.key

.venv/bin/python backend/scripts/encrypted_backup.py verify \
  --receipt BACKUP_DIR/new.json --key KEY_DIR/new.key \
  --deletions CURRENT_INDEPENDENT_JOURNAL.jsonl \
  --scratch PRIVATE_REPORT_DIR/new-restore --out PRIVATE_REPORT_DIR/new-proof.json

.venv/bin/python backend/scripts/encrypted_backup.py inventory \
  --db PRIVATE_SYNTHETIC_CASES.db --deletions CURRENT_INDEPENDENT_JOURNAL.jsonl \
  --receipt BACKUP_DIR/new.json --key KEY_DIR/new.key \
  --verification PRIVATE_REPORT_DIR/new-proof.json --out PRIVATE_REPORT_DIR/new-inventory.json

.venv/bin/python backend/scripts/plan_local_retention.py \
  --inventory PRIVATE_REPORT_DIR/new-inventory.json \
  --policy data/local_operations_policy.90d-30d.encrypted.proposed.json \
  --out PRIVATE_REPORT_DIR/new-retention-preview.json
```

복구는 암호문/헤더·키 인증을 통과한 뒤에만 새0700 scratch에 평문 DB를 만든다. 그 복구 사본에만 현재 명시적으로 공급한 독립 삭제 journal을 적용하고 모든 세션을 폐기·대기 작업을 실패 처리·남은 사건을 보류한다. schema1은 새 scratch의 별도 rollback 백업 후 명시적으로 migration하며 과거 출처/날짜는 unknown으로 둔다. 원본 DB/암호문/키/receipt/journal을 수정하지 않는다. 복구 중 key/journal/receipt/암호문이 바뀌면 PASS proof를 만들지 않고 진단용 scratch를 보존한다. 잘못된 키·변조·없는 키는 평문 scratch 생성 전에 거부한다.

inventory는 정확한 암호문/receipt·복구 proof·현재 공급 journal SHA와 실제 사용 가능한 검증 키 SHA를 결합한다. journal이나 키가 달라지면 restore_verified=false다. 현재 사건에 나중에 설정한 보류도 그 사건을 포함한 과거 백업에 전파한다. 메타데이터만 출력하고 현재 키 바이트/경로·사건 원문/소유자/세션은 출력하지 않는다. planner는 여전히 PREVIEW_ONLY이며 실제 삭제 동작이 없다. 공급된 journal이 운영에서 실제 최신 것인지는 관리자가 현재 경로와 실행 환경에서 확인해야 한다. 로컬 SHA receipt를 악의적인 같은 UID의 전체 재작성에 견디는 독립 인증으로 주장하지 않는다.

검증은 현 사용자UID501의 새 합성 자료만 대상으로 했다. 실제 UID499/기존 백업 전환·운영 배포/관리자 권한 변경은0이다. 실제 생성·복구 CLI13개(의도한 인증/키 부재 실패3개 포함), 전체164 tests·compileall/pip check/diff PASS. 미래2035 시각은90/30일 만료 경계의 명시적 미리보기로만 사용했다. 실제 날짜를 조작하거나 현재 만료 대상으로 보고하지 않는다.

**완전 폐기는 미검증이다.** 이번 키 부재 시험은 새 테스트 키의 이름을 옮겼다가 복원했으며 모든 원본 키와 백업을 보존했다. 복구 scratch와 schema1 rollback 사본은 평문이며0700/0600으로 남아 있다. 이전 평문 백업·운영 관측 sidecar/배포 로그·다른 사본·APFS/Time Machine snapshot·swap·메모리의 키/평문·키 복제 목록은 이 도구의 암호화/폐기 범위가 아니다. 별도 디렉터리는 같은 UID나 잠금 해제된 Mac의 전체 침해를 막는 경계가 아니다. 키 삭제/암호학적 폐기/물리 삭제를 실행하거나 성공했다고 표시하지 않는다.
