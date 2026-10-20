# 실행 체크리스트

2026-10-20 KST. [x]는 아래에 연결된 **한정된 검증 범위**에서 실제 PASS한 항목만 표시한다. 전체 프로젝트 완료를 뜻하지 않는다. BLOCKED/FAIL/NOT_RUN/IMPLEMENTED는 미완료다.

## 검증 근거 색인

| 근거 ID | 수행 명령/검증 대상 | 시각·종료코드·결과 파일 |
|---|---|---|
| R0 | 원본27개 SHA-256/tar 보존, 원본 산출물14개 재검사 | 12:20 KST/0. outputs/runs/20261020T122029+0900-audit/original_manifest.json, original_project.tar.gz; 최종 validation summary의 original_artifacts_preserved |
| R1 | sw_vers, uname -m, sysctl, CLI --help/signature, environment.py | 2026-10-20 KST/0. 같은 audit 디렉터리 environment-after.json |
| R2 | 추가 사용자 터미널 기록 대조(재실행하지 않음) | supplemental_user_log.json. 입력 파일hash와 기존4B/100회/loss 확인, 과거 revision 미확인 |
| T1 | 새 고정환경에서 scripts/validate_local.py → pytest41개/compileall/pip check/compare | outputs/runs/20261020-clean-install/final-validation/summary.json 에 시작·종료 KST/명령·exit code 개별 기록. 모두0 |
| M1 | evaluate_mlx.py --out outputs/runs/20261020-base-v2-retry1 --limit54 | manifest started_at, exit0, raw/predictions/metrics.json. Base54건 실제 실행 |
| M2 | 위와 동일 --adapter outputs/mlx_adapter --out outputs/runs/20261020-ft-v2 | manifest started_at, exit0,56 LoRA모듈/54건 실제 실행 |
| D1 | scripts/data_audit.py --out …/data_audit_v3.json | exit1=실제 데이터 중복/분할 결함 탐지. 토큰 측정 자체 PASS. v2 토큰2개 결과는 INVALIDATED |
| W1 | scripts/browser_e2e.mjs run(tab), 실제 MLX | outputs/runs/20261020-browser-e2e/report-final.json, report-desktop.json.304/1265px. 각 completed_at UTC→KST+9시간. assertion PASS |
| W2 | 명시적 fixture 서버의 취소/부분 완료/모델 미준비 UI | failure-ui-report.json, fixture-partial.png, fixture-unavailable.png. 실제 모델 테스트와 구분 |
| B1 | operations.py backup/restore/check; SQL dump digest 및 restart 테스트 | exit0. service-backup.sqlite3, service-restored.sqlite3, restore-verification.json. T1의 Store backup/recover 테스트 |
| I1 | clean venv pip install lock/pip check/pytest/실제 Metal 추론 + npm ci/build | outputs/runs/20261020-clean-install/install.log, final-validation/, real-inference.json, frontend-npm-ci.log, frontend-build.log. exit0 |
| P1 | 서버 활성 중 다른 프로세스 LocalModel.load 호출 | process-lock-test.json. 별도 호출 exit1/MODEL_BUSY, 기존 ready=true. 의도한 접근 거부 PASS |

변경 파일은 항목별 아래에 적고 전체 변경은 Git diff와 IMPROVEMENT_REPORT를 따른다. 공통 한계: 합성 로컬 환경, 개발 노출 평가셋, 실제 판결문/사람 검수/인터넷 운영 미검증.

## A. 현황과 명세

- [x] A01 PASS — 기존 변경·데이터·결과 보존. R0, .gitignore/AGENTS.md. 원본 파일의 SHA 일치.
- [x] A02 PASS — 현재 환경·의존성·모델 revision 확인. R1/M1/M2, requirements lock/model.py. 과거 revision은 별개 UNVERIFIED.
- [ ] A03 UNVERIFIED — 과거 Base/FT는 R2로4B와 수치/학습 완료 확인, 당시 정확 revision·생성 sampler/hash 미기록. 새 비교 M1/M2는 유효한 개발 비교로 분리.
- [x] A04 PASS — 실제 어댑터 적용. M2/I1, model.py.56개 LoRA 모듈과 실제 응답 생성.
- [x] A05 PASS — 기존 평가셋을 개발 노출셋으로 분류. D1/R2, EVALUATION_PROTOCOL/REPORT.
- [x] A06 PASS — 라벨·시간/식별 경계 정의와 테스트. T1, REQUIREMENTS/contracts.py/temporal.py.
- [x] A07 PASS — 주장·가설·참고 판례 역할 분리. T1/W1, contracts/graph/MCP. 참고 판례는 미연결.
- [x] A08 PASS — 통과 기준·재시도/실험 예산 기록. EVALUATION_PROTOCOL/EXPERIMENT_LOG/ADR. 새 학습0회.

## B. 평가와 데이터

- [x] B01 PASS — 평가기 단위 검증. T1/test_scoring.py, 손계산 perfect/wrong/single class 등.
- [x] B02 PASS — 누락/무효 예측 분모 유지. T1/scoring.py. 예상3건에 누락을 넣어 직접 확인.
- [x] B03 PASS — 출처/이용 목적 기록. T1/DATA_GOVERNANCE/ingestion.py. 실제 수집0건, 권한 미확보 출처는 BLOCKED.
- [x] B04 PASS — fixture와 실제 수집 구분. T1/W1/W2, source_type/provenance. 실제 법원 자료로 표시하지 않음.
- [x] B05 PASS — 미검수 자료 사용 거부. T1/test_governance.py/governance.py. 반입은 항상 quarantine; 실제 학습/RAG 연결 없음.
- [ ] B06 IMPLEMENTED — raw/clean 해시·페이지·정제 구간은 추적 가능. 실제 판결문→검수 SFT 전환 이력은 BLOCKED. ingestion.py/DATA_GOVERNANCE.
- [ ] B07 FAIL — 기존 분할에 그룹 메타데이터 부족, 반복 템플릿/정확 중복. D1. 신규 그룹 분할/독립 데이터 필요.
- [ ] B08 FAIL — 중복 검사는 수행했으나 데이터가 통과하지 못함. D1/test_data_audit.py. 탐지기 PASS를 데이터 품질 PASS로 바꾸지 않음.
- [ ] B09 BLOCKED — 서비스/MCP의 논리적 정답 경로 격리는 T1에서 확인. 같은 OS 계정의 정답 파일 읽기 거부는 미구현.
- [x] B10 PASS — 실제 토크나이저 길이와 초과 검사. D1 v3, max199/768초과0, 손상된 v2 결과 INVALIDATED.

## C. 모델

- [x] C01 PASS — Base4B 추론/54건 평가 실행. M1.
- [x] C02 PASS — 현재 캐시의 train full template와 inference prefix 일치 확인. chat_template_inspection.json. 과거 template hash 미기록 한계.
- [ ] C03 NOT_RUN — 새 학습 smoke 미실행. R2의 기존100회 완료를 보존하고 데이터 결함 해결 전 새 학습 보류.
- [x] C04 PASS — 기존 어댑터 저장 파일 보존/재로딩. R0/R2/M2/I1.
- [ ] C05 BLOCKED — M1/M2는 고정 개발54건 비교. 누수 없는 검증셋의 모델 선택 평가는 아직 없음.
- [x] C06 PASS — 합성 데모 한정 FT 재사용/승격 보류 이유 기록. EVALUATION_REPORT/ADR-003.
- [x] C07 PASS — M1/M2의 모든 원시 응답·실패·토큰·지연·MLX peak 보존. 전체 시스템 메모리는 미측정.
- [x] C08 PASS — 모델/서버 중복 로딩, 동시 생성, 큐 제한. T1/P1/model.py/worker.py.

## D. 검색·MCP·에이전트

- [ ] D01 IMPLEMENTED — 현재 사건 keyword 기준선과 작은 fixture 검색 테스트는 통과. 독립 검색 품질 Recall/MRR는 NOT_MEASURED, 참고 판례 코퍼스 BLOCKED.
- [x] D02 PASS — 인용이 실제 공개 텍스트 구간으로 연결. T1/W1/search.py.
- [x] D03 PASS — 활성 검색 경로의 owner/public/version 제한. T1/MCP/store. 미승인 실제 판례는 검색 경로 자체 차단.
- [x] D04 PASS — 실제 stdio 세션 초기화/list_tools/call_tool. T1/W1/mcp_client/server.py.
- [x] D05 PASS — 미공개/타인 사건 API/MCP/SSE 접근 거부. T1/W1. 임의 파일/URL 도구 없음.
- [x] D06 PASS — 모델 최대4호출,180초,루프0,복구1회. T1/graph/worker/ADR-002.
- [x] D07 PASS — 구조/근거 ID/식별 전제 검증, 빈 검색 PARTIAL/모델 호출0. T1/graph/contracts. 의미적 근거 충분성은 사람 미검수.
- [x] D08 PASS — 실제 새 증거 공개 후 v1→v2 판단 변경. W1.
- [x] D09 PASS — 실제 무관 증거 공개 후 v2→v3 판단 유지. W1.
- [x] D10 PASS — 작업 snapshot/증거 버전/재시작 상태 정합성. T1/B1. 결과 캐시 없음, 자동 checkpoint resume 미구현.

## E. 애플리케이션·운영

- [x] E01 PASS — 실제 브라우저304/1265px 전체 정상 흐름. W1. 다른 브라우저/실제 사용자 접근성 평가는 미실행.
- [x] E02 PASS — API/SSE/결과/비교 인증·소유권. T1/API/store.
- [x] E03 PASS — 취소·부분 완료·모델 준비 실패 화면. W2. 이 오류 시험은 fixture이며 실제 모델 정상 흐름과 구분.
- [x] E04 PASS — 권한/CSRF/origin/host/capability/queue/injection/version/파일 경로 회귀. T1. 모든 보안 결함 부재를 보증하지 않음.
- [x] E05 PASS — fixture/실제 MLX 평가/브라우저 증거 구분. T1/M1/M2/W1/W2/I1.
- [ ] E06 BLOCKED — 공정한 개발 A/B는 완료. 독립 최종셋/참고 코퍼스와 전체 A~F 비교는 미완료.
- [x] E07 PASS — 변경·실측·부작용·미채택 구성·범위를 기록. IMPROVEMENT_REPORT.
- [x] E08 PASS — 실제 새 파일 백업/복구/digest/무결성/재시작 상태. B1. 이전 소스는 별도 checkout/tar로 복구 가능.
- [x] E09 PASS — 새 잠금 환경 설치/실제 Metal, frontend npm ci/build. I1. 모델 캐시는 기존 것을 재사용했으며 새 장비 다운로드는 미검증.
- [x] E10 PASS — LOCAL_VALIDATED 범위와 파일럿/공개 운영 차단 항목 판정. PROJECT_STATUS/ISSUES/OPERATIONS.

## 후속 검증 — Mac 로컬 전용

- [x] N01 PASS — 정확/정규화/어휘 유사·계열 연결·과거 노출·정답 계약 검사와 해시 결합 목적별 검수/철회. 57 tests의 관련 회귀와 candidate-audit-v2.json. 실제 데이터 승인 완료와는 별개.
- [x] N02 PASS — 기존360건 이력 등록/신규 독립 분할 제외. v1/v2 작성 노출까지 현재384개 기록. v2 신규12건은 검수 대기.
- [ ] N03 BLOCKED — 검수 완료 독립 자료/최종셋0건. 노출 범위의 실제 사람 확인 없음.
- [ ] N04 BLOCKED — os-isolation-final.json, 실제 정답 파일 서비스 UID501 읽기 성공. 다른 계정/보호 볼륨 필요.
- [x] N05 PASS — freeze/학습 gate 예상 거부, 영속3개 제한의 실패 포함/새 폴더 reset 거부 회귀, A~F 누락/정보 조건/어댑터/비용 검사.
- [ ] N06 NOT_RUN — 새 학습0/3, 검증셋 모델 선택·최종 A~F0/6. 검사기 구현을 실제 실험 실행으로 보고하지 않음.
- [x] N07 PASS — 개인 접근키/폼·쿠키 인증, 잘못된 키401·타인404·CSRF403, 실제 브라우저 MLX 전체 흐름. 현재 로그인 관측 폭592/607px.
- [x] N08 PASS — real-local-load-corrected.json: 실제12요청/9완료/3개429.9호출/토큰/큐 지연 기록. 짧은 기능 부하에 한정.
- [x] N09 PASS — deletion-recovery/report.json: 실제 합성 DB CLI 삭제/복구6명령, 삭제 재생/세션 폐기/다른 사건 보존. 기동 중간중단 재생은 API fixture 회귀.
- [ ] N10 NOT_CONFIGURED — 자동 보존기간/백업 완전 삭제/실제 자료의 파생 인덱스·학습본 삭제 정책.
- [x] N11 PASS — clean venv final-validation-retry1:57 tests, compileall/pip check/이전 비교 exit0, 원본14개 해시. frontend final build0.

초기 final-validation의1개 근거 표기 실패와 v1 자료를 보존했다. 후속 p95 집계 정정은 같은9개 영속 작업에서 재계산했으며 추가 모델 호출하지 않았다. LOCAL_VALIDATED 유지, 파일럿 승격 BLOCKED. 상세 NEXT_PHASE_REPORT.

## 폴더 구분 후 경로 검증

- [x] F01 PASS — backend/로 Python 소스·도구·의존성 이동, frontend/로 UI·로그인·브라우저 검증 구분. 공유 경로 유지, STRUCTURE.md.
- [x] F02 PASS — 루트/백엔드 실행 위치에서 각각57 tests, compileall/pip check/기존 비교/원본14개 SHA, CLI10개 --help. outputs/runs/20261020-folder-split/validation/summary.json, backend-cli-help.json.
- [x] F03 PASS — 최종 Vue 빌드 exit0, 실제 MLX/MCP 합성 분석1건, HTTP 로그인/자산 및 개발 프록시 인증/API/CSRF/교차 출처 거부. frontend-build-final.log, runtime-smoke.json. 이번 검증은 브라우저 화면 검증이나 새 성능 평가가 아니다.
