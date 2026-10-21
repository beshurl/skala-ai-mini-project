# 실제 모델 작업 전 상태 확인

2026-10-21. 준비 소스/데이터 검증 완료, 실제 관리자 진단·모델 작업 미완료.

현재 실제 UID499 PID41133/41754와 공유 model.lock inode25076574 점유를 확인했다. 사용자의 /usr/bin/sqlite3 -readonly 실행은 CANTOPEN14로 실패해 실제 작업/취소 상태는 UNKNOWN이다. DB 손상/파일 누락/활성 작업0을 추정하지 않는다. 현재 세션 sudo-n은 암호 필요/exit1이며 원 DB·권한·서비스를 변경하지 않았다. 뒤이은 Python 진단 안내의 두 줄이 cd 한 줄로 합쳐진 시도는 진단 미실행이다.

새 diagnose_local_service.py는 root에서 고정 plist/라벨/PID/UID를 확인한 뒤 실제 UID499로 내려가 상태 폴더/DB/WAL/SHM metadata와 readonly jobs 집계만 반환한다. 파일 생성/복구/chmod·서비스 재시작/모델 호출·원문/키/개별 사건ID 출력은 없다. immutable SQLite를 쓰지 않아 live WAL의 대기 작업을 숨기지 않는다. SQLite의 정상 WAL reader coordination 가능성은 별도 명시했다. 합성 누락/손상/심볼릭 링크·live WAL·비관리자/다른 PID 차단6 tests와 모델 생성 API 계약7 tests를 추가했고 전체257 tests/compileall/pip check/diff PASS다. 실제 root 진단 결과는 아직 대기다.

기존 공개 NLI 학습262/검증139의401개 입력에 대해 실제 캐시 tokenizer로 변경 전후 formatted prompt bytes 동일·최대245 입력토큰을 확인했다. 기존 NLI 출력 한도128/greedy/seed0/thinking off는 그대로다. CPU 토크나이저 검사이며 가중치 로드/추론/새 의미 검토0이다. 원본 데이터/정답/검토 subject/사람 이력/450개 AI 결정과 격리49를 유지한 새 protected volume v3 패킷을 봉인하고 실제 load_packet/audit_native_nli PASS를 확인했다. 새 grant/AI chain은 이전 승인/판단 해시를 계승한 소스 재결합이며 사람 승인이나 새 데이터 결정이 아니다.

preparation-plan.json은 execution_ready=false/executable=null인 준비본이다. 기존 실행기의 소스 변경 거부(exit1)를 실제 확인했으며 옛 명령을 재사용하지 않는다. 현재 CANTOPEN/작업 상태 진단·새 실제 정답 접근 거부·중지/재개 검토 전 실행기를 제공하지 않는다. 새 학습0/3·독립 최종/실제 일반 추론 품질/A~F NOT_RUN, 새 실사건 코퍼스 격리/미사용·사람 승인 생성0·운영/유료/공개/원문 외부 전송/삭제0이다.

## 지금 필요한 사용자 실행

다음 **한 줄만** Mac 터미널에서 실행한다. 경로 이동이 필요 없다. sudo 암호는 로컬 프롬프트에만 입력하고 결과 JSON만 전달한다.

```sh
sudo /Users/beshu/Downloads/recase_macos_16gb/.venv/bin/python /Users/beshu/Downloads/recase_macos_16gb/backend/scripts/diagnose_local_service.py --expected-pid 41133
```

반환값의 `probe.classification`, 실제 uid/euid, `database_opened`, `job_state`를 함께 확인한다. DIAGNOSTIC_COMPLETE는 진단 시도가 끝났다는 뜻이며 DB 정상/모델 유휴 판정이 아니다. 데이터 오류·접근 거부·불명확한 상태를 자동 복구/재시작으로 바꾸지 않는다. PID가 달라지면 확인 없이 숫자만 바꾸지 않는다. 이 도구는 권한을 넓히거나 이전 백업으로 DB를 대체하지 않는다.

## 준비 근거

[이번 결과](../outputs/runs/20261021T095154+0900-model-readiness-9fa3f2/RESULT.txt), [CPU 입력 호환성](../outputs/runs/20261021T095154+0900-model-readiness-9fa3f2/tokenizer-compatibility.json), [새 데이터 감사](../outputs/runs/20261021T095154+0900-model-readiness-9fa3f2/fresh-data-audit.json), [실행 불가 준비본](../outputs/runs/20261021T095154+0900-model-readiness-9fa3f2/preparation-plan.json). 기존 패킷/실행 계획과 모든 실패 이력은 보존한다. 일반 추론 경로의 실제 정확도 검증은 [GENERAL_REASONING](GENERAL_REASONING.md)을 따르며 이 NLI 준비와 구분한다.
