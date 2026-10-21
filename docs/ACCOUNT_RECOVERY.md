# 계정 인증과 재해 복구

2026-10-21 최신 근거: `outputs/runs/20261021T091557+0900-account-recovery-110ad4/`. 백엔드204 tests PASS, 새125파일 후보의 실제 CLI/PTY·FixtureModel·stdio MCP에서 계정 소실/격리/새 암호 발급/봉인/사건 복구11항목을 확인했다. 실제 사람 소유권 승인·UID499 운영 전환·MLX/부하·OS 정답 검증은 실행하지 않았다. 이전 계정 통합/암호화 pair 결과는 `20261021T090314+0900-account-integration-6a7cb0`에 보존한다.

## 현재 계정 DB가 있으면 보존

정상 사건 복구는 **현재 계정 DB와 최신 독립 삭제 journal을 유지**한다. 과거 비밀번호·권한·활성 상태·credential_version을 과거 사건 백업과 함께 되돌리지 않는다. `account_backup.py`는 서로 다른 새 키로 사건/계정 이미지를 암호화하고 사건 receipt SHA를 계정 AEAD AAD에 결합한다. 두 파일을 섞고 무키 해시를 재계산해도 거부한다. 키는 별도0700 폴더/0600 파일로 보관한다.

사건/계정 파일은 서로 다른0600 파일, 디렉터리는 운영자 소유0700이어야 한다. 새 백업 PAIR와 복구 SCRATCH/REPORT는 존재하지 않아야 한다. 모델/서버를 직접 중단하는 기능은 없으며 오프라인 작업은 현재 서버 잠금을 요구한다. 아래는 새 합성 사본용 경로 예시다. 실제 UID499 경로에 그대로 실행하지 않는다.

```sh
.venv/bin/python backend/scripts/account_backup.py backup \
  --db CASES.db --accounts CURRENT_ACCOUNTS.db --deletions CURRENT_JOURNAL.jsonl \
  --directory NEW_PRIVATE_PAIR --key-directory EXISTING_PRIVATE_KEYS

.venv/bin/python backend/scripts/account_backup.py verify \
  --manifest NEW_PRIVATE_PAIR/pair.json --key-directory EXISTING_PRIVATE_KEYS \
  --accounts CURRENT_ACCOUNTS.db --deletions CURRENT_JOURNAL.jsonl \
  --scratch NEW_PRIVATE_SCRATCH --out NEW_PRIVATE_REPORT.json
```

복구는 사건 사본에만 최신 삭제 이력·세션 폐기·진행 중 작업 실패·보존 보류를 적용한다. 현재 계정/역할/자격정보는 바꾸지 않는다. 평문 사건 scratch는 비공개로 남는다. 웹 세션은 메모리 전용이므로 실제 서비스 전환 시 프로세스를 재시작한다.

## 현재 계정 DB를 잃었을 때

새 `recover_accounts.py`는 **별도의 새 사본**만 만든다. 현재/기존 DB를 덮어쓰지 않는다. 백업의 ID·이메일·이름·생성 시각을 보존하지만 모든 계정을 비활성화하고 role=user로 바꾸며, 과거 암호 해시 대신 사용할 수 없는 새 임의 verifier를 넣는다. 이전 운영자도 자동으로 복구하지 않는다. 과거 계정 이미지는 메모리에서만 인증/검사한다.

격리 스키마9001은 웹 앱이 거부한다. 기존 Accounts 핸들도 스키마 변경/파일 inode 교체를 거부해 검토한 복구 후 재시작을 요구한다. 새 pair는 SQLite API로 이식 가능한 계정 이미지를 다시 만들어 WAL 계정도 지원한다. 예전 WAL 형식의 계정 이미지는 헤더를 임의 수정하거나 평문으로 쓰지 않고 거부한다.

```sh
.venv/bin/python backend/scripts/recover_accounts.py stage \
  --manifest PRIVATE_PAIR/pair.json --key-directory PRIVATE_KEYS \
  --db NEW_RECOVERED_ACCOUNTS.db --proof NEW_RECOVERY.json
```

그 다음 단계는 **사용자의 실제 로컬 터미널**에서 한다. 이메일은 외부에서 소유권을 확인한 계정을 지정한다. 프로그램이 표시하는 계정 ID를 직접 입력하고 확인 근거·새 비밀번호/확인을 입력한다. 비밀번호를 인자·환경변수·파이프·채팅에 넣지 않는다. 확인 근거에는 원문·개인정보·비밀번호를 쓰지 않는다. 프로그램은 실제 신원을 판정하지 않으며 사용자가 확인한 이력만 기록한다.

```sh
.venv/bin/python backend/scripts/recover_accounts.py activate-user \
  --db NEW_RECOVERED_ACCOUNTS.db --proof NEW_RECOVERY.json --email owner@example.com
```

선택적으로 이미 알고 있는 `--user-id USER-...`를 함께 지정할 수 있다. 계정 하나를 활성화해도 아직 웹에서 사용할 수 없다. 미확인 계정은 비활성으로 남긴 뒤 마지막 봉인을 별도로 확인한다. 이 단계도 TTY만 허용하며 화면의 **보류 N개 유지** 문구를 직접 입력한다.

```sh
.venv/bin/python backend/scripts/recover_accounts.py seal \
  --db NEW_RECOVERED_ACCOUNTS.db --proof NEW_RECOVERY.json --out NEW_SEAL.json
```

봉인 후에만 스키마1로 전환된다. 활성 계정도 일반 사용자이며 운영자는0명이다. 필요한 경우 검토 완료 후 `accounts.py create-admin`으로 별도의 새 운영자 계정을 로컬 터미널에서 만든다. 미확인 계정을 활성화하거나 과거 운영자 권한을 복원하지 않는다. 봉인 뒤의 추가 복구 활성화/수정은 이 복구 이력을 재사용하지 않고 새 검토 절차를 따른다.

intent를 먼저 fsync해 기록하고 DB 변경/완료를 이어 쓴다. 중단된 intent·외부 DB 변경·교체 파일·다른 계정 ID·보류 집합 불일치는 자동 재시도하지 않고 운영자 점검을 요구한다. 초기 proof/행동 ledger/봉인 proof는 별도로 보존한다. 같은 UID의 악의적 전체 재작성까지 막는 독립 서명은 아니다.

복구된 계정은 별도로 현재 journal을 적용한 사건 사본과 소유권/결과를 검증해야 한다. 백업 뒤 생긴 계정이나 현재 권한 회수 이력을 백업만으로 복원할 수는 없다. 누락된 ID나 미확인 소유자는 계속 보류한다. 기존 접근키 세션 소유자를 새 이메일/첫 가입자에 자동 연결하지 않는다. 전체 운영 전환/원래 소유권 연결은 실제 관리자 진단·사람 판단이 남아 있다.

## 코드·사건 DB 전환 검사

`verify_release_database.py`는 account-password-v1 manifest와 같은 현재 계정 DB를 양쪽에 요구한다. 과거 계정 사본/구 접근키 후보·새 기록을 잃는 사건 사본 전환을 거부한다.

```sh
.venv/bin/python backend/scripts/verify_release_database.py \
  --source-db CURRENT_STOPPED_CASES.db --target-db PROPOSED_CASES.db \
  --accounts CURRENT_ACCOUNTS.db --target-accounts CURRENT_ACCOUNTS.db \
  --deletions CURRENT_JOURNAL.jsonl --release-manifest PRIVATE_RELEASE/candidate-manifest.json \
  --release-root PRIVATE_RELEASE/candidate-app --out NEW_PRIVATE_CHECK.json
```

이 도구는 실제 서비스/DB를 전환하지 않으며 잠금/SQLite 조정 sidecar를 만들 수 있다. 실제 root 게시/UID499·복귀 후보·MLX·정답 OS·장시간 부하/보조공학 검증은 남았다. 현재 후보125파일/0400·0500도 운영에는 미적용이다. 이전 후보/실패/원본은 보존한다.

사건90일·백업30일은 사용자 선택대로 유지한다. 계정 pair·복구 ledger·평문 scratch·모든 키 사본/APFS/swap을 포함한 보관/폐기 정책은 미완료이며 pair는 자동 폐기 대상이 아니다. 자동 삭제·키 폐기·스케줄러0이다. 새 학습0/3·독립 최종셋/승인 판례/검색 정답/A~F와 복잡한 일반 추론의 구현/평가는 별도 남은 항목이다.
