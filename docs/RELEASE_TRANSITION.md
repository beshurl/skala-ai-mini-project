# 로컬 배포 후보와 DB 전환 검사

**2026-10-21 최신:** [ACCOUNT_RECOVERY](ACCOUNT_RECOVERY.md)의123파일 계정 후보와 --accounts/--target-accounts 검사가 최신입니다. 같은 현재 계정 DB·권한/credential_version·소유권을 결합하고 구 접근키 코드/계정 과거 사본/새 기록을 잃는 사건 사본 전환을 거부합니다.195 backend/14 frontend 및 새 합성 후보 복구/재시작 PASS. 실제 UID499 복귀 후보/배포는 미검증입니다. 아래119파일·174 및 병행 변경 안내는 당시 스냅샷 이력입니다.

**병행 계정 개편 안내:** 후보 생성 뒤 api.py/admin.py/store.py와 새 accounts/auth_api가 계정 인증 방식으로 변경됐다. 사용자는 다른 작업에서 개편 중이며 완료 후 통합 검증하도록 답했다. 이번119파일/174 tests·3단계 시험은 그 변경 전의 접근키 인증 스냅샷 근거다. 현재 계정 인증·accounts sidecar/세션의 이전·백업·복구·역할·배포/복귀 호환성은 여기서 검증하지 않았다. 후보는 보존하지만 현재 checkout용 배포본으로 사용하지 않는다. 계정 작업 완료 뒤 최신 소스와 별도로 다시 통합한다.

현재 후보는 [20261020T173502+0900-release-transition-bcc984](../outputs/runs/20261020T173502+0900-release-transition-bcc984/RESULT.txt)의119파일·5,457,530bytes다. archive SHA256은 `6d21511eaa16bdb560ed99fda0b7366ad56b736e8bad57e826e735c3fb6916e4`이며 파일별 SHA는 같은 run의 candidate-manifest.json에 있다. 암호화 백업·DB 전환 검사 도구와 최신 SQLite 연결 종료 수정을 포함한다. 모델/어댑터·원본/정답·DB·journal·키·환경설정·검수 ledger는 포함하지 않는다. 정책은 별도의 비활성 초안이며 묶음을 전개한다고 자동 활성화되지 않는다.

**실제 UID499 운영에는 미적용**이다. 현재 후보는 새 폴더에 전개한 후 디렉터리0500·파일0400으로 두고 현 사용자UID501에서만 검증했다. 단계별 모듈 경로/파일 해시와 실제 stdio MCP·FixtureModel·TestClient HTTP를 확인했다. 기존 venv를 재사용했으며 실제 MLX·UID499·운영 접근키·OS 정답 접근·브라우저/보조공학·장시간 부하 검증을 대신하지 않는다. 같은 UID의 소유자는 권한을 바꿀 수 있으므로 이 읽기 전용 시험을 악의적인 같은 UID에 대한 보안 경계라고 주장하지 않는다.

`backend/scripts/verify_release_database.py`는 새 후보와 데이터 전환을 점검한다. 실제 DB/서비스를 바꾸는 명령은 없다. 올바른 소유자의0600 일반 DB/journal과 검토한 manifest/stage를 지정하고 source/target의 표준 maintenance 잠금을 확보한다. 아직 없으면 빈 `.server.lock`을 새로 만들 수 있다. SQLite의 읽기 전용 접근도 WAL/SHM 조정 sidecar를 만들거나 갱신할 수 있다. DB 본체·독립 삭제 journal·세션·코드의 내용은 바꾸지 않는다.

```bash
.venv/bin/python backend/scripts/verify_release_database.py \
  --source-db CURRENT_STOPPED_CASES.db \
  --target-db NEW_MIGRATED_OR_RESTORED_CASES.db \
  --deletions CURRENT_INDEPENDENT_JOURNAL.jsonl \
  --release-manifest PRIVATE_RELEASE/candidate-manifest.json \
  --release-root PRIVATE_RELEASE/candidate-app \
  --out PRIVATE_REPORT_DIR/new-transition-check.json
```

이는 경로 예시이며 현재 UID499 DB에 그대로 실행하지 않는다. 실제 운영에서는 먼저 [관리자 읽기 전용 작업 진단](../outputs/runs/20261020T155158+0900-remaining-work-b82291/ADMIN_DIAGNOSTIC.txt)으로 지연/취소 작업의 최종 상태를 확인한다. 이후 새 중지·백업·migration·현재 journal/보호 정답·동일 model.lock inode·인증/권한·실제 모델·rollback 계획을 검토한다. 기존 성공한 isolation/operations --apply를 반복하지 않는다. 관리자 비밀번호는 로컬 sudo 프롬프트에만 입력한다.

검사는 다음을 요구한다.

- manifest의 허용 경로·SHA·개수/크기·현재 코드와 같은 schema2 선언. 미기록 파일/bytecode·링크·변경된 코드는 거부한다. 현재 사용자 소유의0400/0600 코드 또는 root 소유0444/0644 게시 파일을 지원하지만 실제 root 게시/UID499 조합은 미실행이다.
- source/target 서버 중지 잠금·무결성·알려진 테이블/열·참조 관계·대기/실행 작업0. 100,000행/64MiB 비교 한도가 있으며 부족하면 거부한다.
- 현재 공급 journal의 소유권과 tombstone. 대상에 삭제 사건·연결 자료가 남으면 거부한다. journal이 운영에서 실제 최신 경로인지는 관리자가 확인한다.
- 현재 사건/증거/주장·작업 결과를 포함한 전체 job 행·이벤트/감사·lifecycle 이력의 보존. 현재 행이 누락·변경된 오래된 사본은 거부한다. 더 강한 `restore_hold`만 명시적 조건 아래 허용하며 종료일/출처/증거 변경을 보류로 위장하지 않는다.
- schema1→2 원사건의 날짜/출처는 null/unclassified·보존 보류. 다른 DB 사본으로 전환하면 세션0. 동일 DB를 쓰는 코드 복귀는 세션을 되돌리지 않고 현재 DB를 유지한다.
- 검사 중 DB 본체/journal/manifest/코드가 바뀌면 PASS proof 없음. 보고서는 행 내용·쿠키·키를 내보내지 않는다. 로컬 해시는 독립 서명/악의적인 같은 UID 방어가 아니다.

세 단계 사본 시험은 실제 운영 코드의 공개 `.py`만 새 읽기 전용 폴더로 복사해 schema1 합성 분석을 수행하고, 새 DB 사본에 schema2 migration·삭제 journal을 적용한 뒤 새 개인 인증/CSRF/MCP/SSE·v2 분석·종료/보류 기록을 만들었다. 이후 schema1 사본과 새 기록이 없는 schema2 사본은 exit2로 거부했다. 보존한 이전115파일 schema2 후보를 새로 전개해 **동일한 현재 DB**로 코드 복귀하고 새 사건·결과·종료/보류·세션·쓰기 차단을 유지함을 확인했다. 새119파일 후보 안의 암호화 백업 CLI도 실제 생성·복구를 통과했다. 이115파일 후보는 호환성 시험용이며 새 암호화 도구/연결 종료 수정을 포함하지 않는다. 실제 운영의 복귀 후보 지정·MLX/UID499 검증은 별도다.

첫 시험1건의 DB 본체 SHA 변화는 이전 backup/migration/retention 함수가 sqlite3 연결 종료를 가비지 수집에 맡겨 VACUUM/WAL 체크포인트가 늦어진 원인으로 확인했다. `closing()`으로 명시적으로 닫도록 수정하고 강제GC 뒤에도 본체 SHA가 같고 열린 연결0임을 검증했다. 첫 실패·별도 진단·수정 뒤38개 관련/전체174개 테스트 기록을 보존했다. 새 묶음의 manifest0644는 엄격 검사가 거부해 새 manifest만0600으로 제한한 뒤 전개 내용을 검증했다. archive를 덮어쓰거나 이전 실패를 지우지 않았다.

현재 판정은 LOCAL_VALIDATED 유지다. 이 검사가 실제 배포·백업/키 폐기·90/30일 자동 삭제·모델 학습·파일럿/공개 운영을 승인하거나 실행하지 않는다. 현재 서비스/DB/모델 잠금·기존 백업/키는 보존한다.
