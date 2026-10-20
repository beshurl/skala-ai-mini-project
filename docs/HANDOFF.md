# RE:CASE 인수인계

2026-10-20 KST. 사용자 요청은 개선 폴더의 작업을 이어서 진행하는 것이며, 뒤에 추가한 터미널 기록은 참고용이다. 해당 기록의 설치/생성/학습 명령을 재실행하지 않았다.

## 최신 후속 상태 — 아래 초기 단계 기록보다 우선

사용자가 목표를 이 Mac의 로컬 전용으로 지정했다. 후속 구현/실측/차단 사유는 [NEXT_PHASE_REPORT](NEXT_PHASE_REPORT.md), 준비·운영 명령은 [NEXT_PHASE_PROTOCOL](NEXT_PHASE_PROTOCOL.md)이다. 57 tests PASS, 개인 접근키 인증·실제 MLX 제한 부하·삭제 복구 확인. 기존360건 제외/노출 기록, 검수 대기12건 v2(미검수), 학습3개 제한/동결/A~F 비교 gate를 추가했다. 사람 검수0·새 학습0/3·A~F0/6·실제 판결문0. 현재 서비스 UID가 실제 기존 정답 파일을 읽어 OS 격리는 BLOCKED다.

`make serve`는 개인 인증을 요구한다. localhost:8100, 키 runtime/personal-auth/key.txt, 삭제 journal runtime/deletions.jsonl. 비밀키/삭제 journal은 Git 제외이며 덮어쓰지 않는다. 기본 무인증 재기동 명령을 사용하지 않는다.

## 초기 단계에서 완료한 것

- 원본27개 파일 백업과 해시, 기존 데이터/어댑터/평가14개 해시 유지.
- 추가 기록으로 과거4B Base/FT 평가·100회 학습 완료·반올림 검증 손실 확인. 현재 캐시4B revision과56개 LoRA 모듈을 실제 검증.
- 고정 조건의 Base/기존 FT 각54건 실제 평가와 비교 거부/누락·무효/근거 검증 평가기.
- FastAPI/Vue3 앱, 제한된 로컬 세션/CSRF/소유권, 공개 증거/권한 있는 공개, 저장된 작업·SSE·취소/부분 완료/실패, 근거 원문과 시간상 이전 결과 비교.
- 실제 stdio MCP, 현재 사건 keyword 검색 hit에 제한한 입력, 단일 MLX 모델/큐/timeout, 버전/취소의 원자적 저장 확인.
- 새 잠금 환경에서41개 자동 테스트, 설치/compileall/pip check/실제 Metal 추론 PASS. frontend npm ci/build PASS.
- 실제 MLX 브라우저304/1265px 전체 흐름 PASS. 오류/취소/부분 완료는 명시적 fixture 서버로 별도 PASS. 브라우저 console warning/error 없음.
- 실제 DB backup/새 복구본/무결성/SQL digest, 서버 재시작 상태, 중복 모델 프로세스 거부 확인.

## 변경한 것

핵심 소스 recase/{api,store,model,graph,worker,mcp_client,mcp_server,capability,contracts,search,governance,ingestion,temporal}.py, frontend/src/, tests/. 기존 MLX 평가·비교·데이터 생성/변환·반입/학습 launcher의 덮어쓰기/조건 확인을 보완했다. 기존 CUDA 도구는 보존했지만 이번 Mac 검증 대상이 아니다.

환경은 requirements-lock-macos-arm64.txt, 명령은 Makefile과 OPERATIONS.md, 결정은 docs/adr/에 기록했다. Git은 이 프로젝트 내부 `codex/recase-local` 브랜치이며 원본 기준 커밋35bfb54를 보존한다. 참고 all_total_vue_student는 수정하거나 복사하지 않았다.

## 개선 효과와 해석

동일54건의 엄격한 label/reason/evidence_ids 계약 성공률 Base0%→기존 FT100%, 평균 생성2.9192→1.3633초, MLX allocator peak2.5928→2.8048GB. 모델 로딩 시간은 지연 수치에서 제외했다. 이 비교는 기존 어댑터의 합성 도메인 효과 확인이고 이번에 새 학습을 수행한 결과가 아니다.

데이터 분할 사이에 같은 prompt와3개 템플릿이 반복되어 일반화 증거가 부족하다. 이전15건의33.33%→100% 수치와 새54건을 직접 Before/After로 섞지 않는다. 모델 이름은 추가 로그에서 양쪽4B로 확인했고,0.6B는 코드 기본값 결함이었다. 과거 revision/hash/원시 loss는 미확인으로 남긴다.

앱에서는 신원 미확인 v1을 INSUFFICIENT로 유지하고, 본인 확인 v2에서 CONTRADICTED로 바뀌며, 무관한 날씨 v3에서는 판단을 유지했다. 인용 버튼은 실제 공개 원문을 가리킨다. 이런 제한된 흐름을 전체 가설 갱신 정확도로 일반화하지 않는다.

## 채택하지 않은 것

새 학습 후보0개. 벡터/Hybrid/reranker/앙상블/병렬 다중 모델/무제한 재검토/자동 checkpoint resume/외부 tracing은 도입하지 않았다. 이점이 없었다는 실험을 꾸미지 않고 필요성과 검증 근거가 부족한 상태로 남겼다. 실제 판례 도구는 BLOCKED를 명시하며 합성 판례로 성공을 대신하지 않는다.

## 검증하지 못한 것

독립 최종 평가, 실제 판결문 이용 목적별 권한/사람 개인정보·라벨 검수, 정답 디렉터리의 OS 사용자 격리, 실제 사용자 인증/운영 부하/폭넓은 보안·접근성·브라우저 호환, 삭제/보존 자동화, 실제 운영 환경 배포. **LOCAL_VALIDATED는 합성 로컬 흐름에 한정하며 PILOT_READY/PRODUCTION_READY가 아니다.**

## 실행 방법

현재 루트 `/Users/beshu/Downloads/recase_macos_16gb`에서 `make serve`, 접속 http://127.0.0.1:8100 . 기존 `.venv`와 모델/어댑터를 사용한다. 앱은 실제 MLX로 기동한다. UI에서 로컬 데모 입장/새 합성 데모 시작 후 사건을 선택한다.

```bash
make check
make frontend
make serve
```

새 설치는 OPERATIONS.md의 lock 기반 새 venv/npm ci 명령을 따른다. 모델은 오프라인 기존 캐시만 재사용하므로 새 장비에서 별도 모델 준비가 필요하다. 전체 평가/학습 전 실행 중인 모델 서버를 중단한다. `MODEL_BUSY`를 우회하지 않는다.

```bash
RECASE_RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
make eval-base RUN_ID="$RECASE_RUN_ID"
make eval-ft RUN_ID="$RECASE_RUN_ID"
make compare BASE="outputs/runs/$RECASE_RUN_ID-base/metrics.json" TUNED="outputs/runs/$RECASE_RUN_ID-ft/metrics.json"
```

브라우저 E2E는 cua_repl에서 `scripts/browser_e2e.mjs`의 `run(tab)`을 실행한다. 실제 모델/어댑터를 UI에서 확인하고 새 합성 세션을 생성해 검증한다. 자체 브라우저를 시작하는 별도 Playwright shell transport는 사용하지 않았다. 모의 오류 검증은 scripts/serve_fixture.py의 별도 로컬 포트/새 DB로 수행했으며 최종 사용자 서버와 분리한다.

## 결과 위치

- 원본/감사/추가 사용자 기록/데이터 결함: outputs/runs/20261020T122029+0900-audit/
- 고정54건: outputs/runs/20261020-base-v2-retry1/, outputs/runs/20261020-ft-v2/
- clean 환경: outputs/runs/20261020-clean-install/ (final-validation/summary.json, real-inference.json, frontend 로그)
- 브라우저/복구/lock: outputs/runs/20261020-browser-e2e/ (report-final.json, report-desktop.json, failure-ui-report.json, screenshots, restore-verification.json)
- 전체 판정과 한계: EXECUTION_CHECKLIST.md, EVALUATION_REPORT.md, IMPROVEMENT_REPORT.md, ISSUES.md.

## 롤백 방법

기존 데이터/어댑터/평가 결과는 그대로라 별도 복원 없이 사용할 수 있다. 코드 원복은35bfb54 또는 원본 tar를 **새 폴더**에서 확인한다. 현재 폴더에 reset --hard/덮어쓰기를 하지 않는다. DB는 operations.py restore로 새 파일을 만들고 서버를 중단한 뒤 RECASE_DB를 바꾼다. backup/restore는 기존 목적지를 거부하며 파일 mode0600/SQL integrity/digest 확인을 수행했다.

## 다음 작업

1. 독립 사건/문서/시나리오 계열과 검수된 평가/훈련 데이터를 확보한다. 정확/유사 중복과 노출 이력을 먼저 해결한다.
2. 실제 판결문은 processing 및 학습/검색/표시/재배포를 각각 승인하고 사람이 비식별화·라벨을 검수한다. 현재 반입 출력은 격리 상태로 유지한다.
3. 서비스/평가기 OS 계정·보호 볼륨을 분리해 실제 정답 파일 접근 거부를 시험한다.
4. 검수된 검증셋에서 설정/모델을 고정한 후 제한된 새 학습 후보(최대3개)와 공정한 A~F 비교를 진행한다.
5. 목표 운영 환경·실제 인증·부하·삭제/복구 정책을 검증한 후 파일럿/공개 배포 여부를 별도 판정한다. 유료 호출/공개 배포/원문 외부 전송은 사전 승인 전 실행하지 않는다.

후속 시 검수 대기 자료는 outputs/runs/20261020-next-gates/review-packet-v2/candidates.jsonl을 사용한다. v1과 최초 실패는 보존했다. 사람이 내용/라벨/권리/계열/노출을 검수하기 전 새 학습을 실행하지 않는다. 관리자 OS 분리는 아직 수행하지 않았다.
