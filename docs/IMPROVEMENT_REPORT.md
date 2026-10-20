# 개선 기록

모든 결과는2026-10-20 KST 로컬 장비의 해당 검증 범위다. 원본 데이터/어댑터/평가14개 해시는 그대로다. 새로운 학습을 수행해 모델을 개선했다고 주장하지 않는다.

## IMP-001 — 평가를 재계산하고 조건을 확인할 수 있게 변경

1. 기존 문제: label만 추출하는 평가와 조건을 보지 않는 비교, 고정 결과 경로 덮어쓰기.
2. 근거: 원본 evaluation/evaluate_mlx.py, scripts/compare.py는 감사 tar와 기준 커밋35bfb54에 보존. 기존15건 metrics에는 revision/생성 조건이 없었다.
3. 원인: 모델·데이터·출력 계약의 식별정보와 무효/ID 검증이 부족했다. 추가 로그는 기존 실행 모델이4B였음을 확인하므로 모델 오사용을 원인으로 단정하지 않는다.
4. 변경: scoring.py, evaluate_mlx.py, compare.py. 고정3라벨, 필수 필드/근거 ID, gold 분모, 누락/중복, raw/복구, manifest, 고유 run, 불일치 비교 거부. 데이터/어댑터는 변경하지 않았다.
5. 선택 이유: 재학습보다 먼저 평가기의 신뢰성을 확보해야 한다. 추측 label 추출/여러 LLM 복구 대신 제한된 형식 복구1회를 택했다.
6. 비교 조건: 평가기 자체는 직접 계산 가능한 작은 예시/오류 입력으로 테스트했다. 모델 점수 Before/After와 혼동하지 않는다.
7. Before/After: 기존 자동 회귀 테스트 NOT_RUN → 정상/전부 오답/단일 클래스/누락/중복/잘린 JSON/금지 ID/비교 조건 거부 테스트 PASS. 오류율/지연 개선 수치는 NOT_MEASURED.
8. 한계: 기존15건을 새 계약으로 점수 재계산해 성능이 향상됐다고 해석할 수 없다. 의미적 인용 충분성은 미측정.
9. 결정: 채택.
10. 재현/롤백: `make check`, 각 모델 run의 raw_predictions로 재계산. 이전 소스는35bfb54/원본 tar를 별도 폴더에 복구.

## IMP-002 — 기존4B 어댑터의 실제 효과와 한계를 재검증

1. 기존 문제: 학습을 했다는 보고와 파일만으로 어댑터 사용/공정 비교를 확정할 수 없었다.
2. 근거: adapter_config와 원본15건, 추가 사용자 터미널 기록. 새 실행에서56개 LoRA 모듈과 adapter_loaded=true 확인.
3. 원인: 과거 실행 식별정보 누락. 데이터에는 정확/템플릿 중복이 있다.
4. 변경: 현재 캐시 revision·tokenizer/config/adapter hash·동일54 IDs·동일 system/thinking/greedy/seed/max256으로 Base와 기존 FT를 순차 실행했다. 새 학습0회.
5. 선택 이유: 사용 가능한 어댑터를 보존하고 필요한 검증만 수행한다. 기존 학습을 처음부터 반복하지 않는다.
6. 조건: EVALUATION_REPORT와 두 manifest의 데이터/모델/설정 일치. Apple M5/16GiB, MLX0.32.4/MLX-LM0.32.2. evaluator protocol recase-eval-v2.

| 지표 | Base4B | 기존 FT4B | 차이/해석 |
|---|---:|---:|---|
| 계약 성공률 | 0% | 100% | +100퍼센트포인트; 의미 추론 전체의 향상으로 일반화하지 않음 |
| 계약 기준 Macro F1 | 0 | 1 | 합성 노출54건만 |
| 평균 생성 지연 | 2.9192s | 1.3633s | -1.5559s, 관측53.3% 감소. 출력 길이도 감소 |
| MLX peak allocated | 2.5928GB | 2.8048GB | +0.2120GB |

8. 한계: 같은3템플릿, train↔test 공통 고유 prompt9개, test18/54건의 prompt가 train에 존재. 54건 모두 EOS stop/런타임 실패0이지만 실사용 신뢰도는 입증하지 못한다. 별도 사후 label-only 진단은 주 지표를 변경하지 않는다.
9. 결정: 합성 로컬 데모에 한해 재사용, 실제 서비스 모델 승격 보류.
10. 재현/롤백: 두 run의 manifest/raw/predictions/metrics와 compare.py. 어댑터 원본과 캐시 그대로 유지하므로 파괴적 복구가 필요 없다.

## IMP-003 — 사건·증거·분석 이력이 연결된 로컬 앱

1. 기존 문제: RE:CASE 폴더에는 학습/평가 도구만 있고 사건 검토 UI/API가 없었다. 참고 프로젝트는 운영 인시던트 채팅 용도였다.
2. 근거: 원본 파일 목록, 감사 문서. 참고 코드는 읽기만 했다.
3. 원인: 사건 소유권·공개 버전·영속 job/result/SSE 상태가 미구현이었다.
4. 변경: recase/api.py, store.py, mcp_server/client.py, graph.py, worker.py, frontend/. 로컬 세션/CSRF, owner별 격리, 공개 증거, 다음 증거 공개, 큐1모델, 취소/시간초과/STALE/재시작 실패, 인용, 결과 비교를 추가했다. 실제 검색 hit가 모델 입력 후보를 제한하며 빈 검색은 PARTIAL/호출0회로 표시한다.
5. 선택 이유: 여러 모델/무한 재계획 대신 한 모델과 bounded graph를 택해 자원과 근거 흐름을 설명할 수 있게 했다. 캐시/벡터DB/앙상블은 도입하지 않았다.
6. 조건: 별도 합성 사건, 실제 캐시 MLX/기존 어댑터. mock 테스트와 실제 브라우저 모델 실행을 분리했다.
7. Before/After: 전체 흐름 NOT_APPLICABLE(앱 미구현) → 실제 사건 선택/진행/인용/공개/재분석/변경 비교/무관 증거 판단 유지 PASS. API는 사용자B의 사건/결과/SSE 접근404, CSRF/origin/host 차단, 큐 제한/취소/timeout/버전 변경 테스트 PASS.
8. 한계: 방문 부정 관계의 합성 데모다. 범용 사실 추출/가설 생성/실사용 인증/독립 평가에 대한 성능 개선 주장은 하지 않는다.
9. 결정: LOCAL_VALIDATED 범위 채택.
10. 재현/롤백: make serve, scripts/browser_e2e.mjs를 cua_repl에서 실행. DB backup/restore와 이전 커밋 별도 checkout.

## IMP-004 — 판결문 반입과 검수 경계

1. 기존 문제: 단일 permission_confirmed와 출력 덮어쓰기, 제한된 TXT/PDF 경로, 개인정보 검수/목적별 승인 경계 부족.
2. 근거: 원본 ingest_judgments.py, rights_manifest.example.json. 실제 판결문은 제공되지 않았다.
3. 원인: 처리 허용과 학습/검색/화면 표시/재배포 허용이 분리되지 않았다.
4. 변경: ingestion.py/governance.py, v2 manifest. 로컬 TXT/HTML/PDF, dry-run/limit/resume/hash dedup/파싱 실패 격리/경로·symlink 제한/QUARANTINED와 false 사람 검수 필드.
5. 선택 이유: 자동 수집·라벨 확정 대신 권한과 검수 상태를 보존한다. 승인 없는 API/스크래핑/OCR은 추가하지 않았다.
6. 조건: 로컬에서 작성한 synthetic fixture만 사용. 실제 수집0건.
7. Before/After: 이전 테스트 NOT_RUN → dry-run 무쓰기/resume 중복방지/권한 거부/경로 탈출/HTML script 제거/깨진 PDF 격리/용도별 승인 게이트 PASS. 실제 비식별화 정확도 NOT_MEASURED.
8. 한계: regex는 완전 비식별화가 아니며 실제 승인/사람 검수/OCR/목적별 이용 조건 확보가 필요하다.
9. 결정: 격리용 로컬 파이프라인 채택; 실제 학습·참고 RAG 연결 BLOCKED.
10. 재현/롤백: tests/test_governance.py, 새 --output 또는 --resume. 기존 산출물 보존.

## IMP-005 — 설치·자원 충돌·복구를 실행으로 확인

1. 기존 문제: 의존성 범위만 있고 설치/실행/백업 복구 증거가 없었다.
2. 근거: 원본 requirements/README, 새 clean install 로그.
3. 원인: 환경 잠금과 작업 상태/DB 복구 절차 미구현.
4. 변경: exact requirements lock, Makefile, environment/validate_local/operations CLI, model/server lock, SQLite0600/schema version, 복구시 진행 작업 실패 처리.
5. 선택 이유: 단일 Mac 환경에서 재현성과 실패 처리를 우선한다. 사용량을 공개 서비스 처리량으로 일반화하지 않는다.
6. 조건: 별도 clean venv, 같은 M5와 모델 캐시. 백업은 새 목적지만 허용한다.
7. Before/After: 설치·복구 NOT_RUN → clean install/pip check/전체 테스트/실제 Metal 추론 PASS, SQL dump digest 동일 복구 PASS, 중복 모델 프로세스 MODEL_BUSY 거부 및 기존 readiness 유지 PASS.
8. 한계: 다른 OS, 다른 장비, 공인 운영 환경, 암호화/재해 복구는 NOT_RUN. 새 학습 launcher는 보호된 사전검사까지 구현했고 본 학습은 실행하지 않았다.
9. 결정: 로컬 운영 절차 채택, 공개 운영 승격 보류.
10. 재현/롤백: OPERATIONS.md의 실제 명령, 원본 manifest/tar, 별도 DB 복구본과 기존 모델/어댑터 유지.

## 채택하지 않은 구성

새 학습, 벡터/Hybrid/reranker, 병렬 다중 모델, 복잡한 Multi-Agent, 앙상블, 자동 최종 정답 생성, 외부 tracing은 실행/채택하지 않았다. 효과가 없었다는 실험 결과를 만든 것이 아니라 현재 필요성/데이터/검증 근거가 부족해 보류한 것이다.

## IMP-후속 — 데이터/실험/개인 운영 경계

기존 문서의 수동 승인 플래그와 일반 학습 launcher만으로는 목적별 검수·노출·후보 예산을 연결할 수 없었다. 새 해시 결합 ledger/목적별 검수·철회/계열·중복·노출 감사/live freeze/실패 포함3개 제한/A~F 비교 검사를 추가했다. 실제 자료 통과가 아닌 차단 경로를 검증했으며 검수 완료0·학습0/3·A~F0/6을 유지한다. 같은 UID의 전면 재작성과 의미적 중복 탐지에는 한계가 있다.

Mac 로컬 전용 목표에 맞춰 보호된 접근키·폼/쿠키 인증, 기존 owner/CSRF 유지, 실제 MLX12요청의9완료/3제한, 독립 삭제 journal과 과거 백업 재생을 검증했다. 초기41→후속57개 자동 테스트는 검사 범위 증가이며 모델 품질 향상을 뜻하지 않는다. 로그인 화면은 기존 네이비/바이올렛/시스템 한글을 유지했다.

실제 기존 정답 파일의 서비스 UID 읽기는 성공하여 OS 격리 판정을 BLOCKED로 남겼다. 물리 삭제·자동 보존기간·실제 판결문 승인·최종셋은 미완료다. 원본14개 산출물 SHA를 보존하고 새 출력만 만들었다. 증거/재현/실패/정정/롤백은 NEXT_PHASE_REPORT/PROTOCOL을 따른다. 소스 롤백은 이전6e10346을 별도 checkout에서 확인하고, 비밀키/삭제 journal은 과거 DB와 함께 롤백하지 않는다.
