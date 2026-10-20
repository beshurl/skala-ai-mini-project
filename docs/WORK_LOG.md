# 작업 기록

## 2026-10-20 KST — 감사 시작

- 사용자 지시: 개선한 기존 폴더를 이어서 진행. 실행 지침은 요구사항으로 읽되 결과를 가정하지 않음.
- `sw_vers`, `uname -m`, `sysctl -n hw.memsize`, `df -h .`, `vm_stat`: exit 0.
- `.venv/bin/python -m mlx_lm.lora --help`, 함수 signature 검사: exit 0. 설치된 API 옵션을 확인.
- 원본 27개 파일 SHA-256 및 tar.gz 백업: exit 0. 경로 `outputs/runs/20261020T122029+0900-audit/`.
- 참고 프로젝트에는 명시 라이선스가 없음. 원본은 변경하지 않고 싱글턴/stdio/SSE 패턴만 참고한다.
- 기존 평가 모델 기본값 불일치 발견. 모델 다운로드/재학습 없이 로컬 캐시로 검증한다.

## 같은 날 — 평가기·기존 모델 검증

- `pytest tests/test_scoring.py -q`:13 PASS/exit0. 이후 통합/보안/데이터/시간 규칙 테스트를 합쳐41개로 확장.
- 첫 오프라인 Base 로딩은 HF Hub의 부가 문서2개 누락 검사로 exit1. 모델 파일은 정상이므로 allow_patterns로 실행 파일만 확인하도록1회 수정. 실패 폴더 보존.
- `evaluation/evaluate_mlx.py --out outputs/runs/20261020-base-v2-retry1 --limit 54`: exit0. 같은 snapshot/greedy/seed0/thinking off/max256.
- `evaluation/evaluate_mlx.py --adapter outputs/mlx_adapter --out outputs/runs/20261020-ft-v2 --limit 54`: exit0.56개 LoRA 모듈 확인.
- `scripts/compare.py` 두 run: exit0. 원시 계약 성공률0%/100%, 평균 생성2.9192/1.3633초, MLX allocator peak2.5928/2.8048GB. 노출된 합성 데이터 한계와 별도 label 진단은 EVALUATION_REPORT.
- `scripts/data_audit.py`: exit1(실제 분할 품질 FAIL). 공통 고유 prompt10/9/6개, train에 노출된 val21/54·test18/54. v2 토큰 감사는 key 개수 오류로 INVALIDATED, v3 실제 token max199/768초과0으로 수정. 원본 데이터는 바꾸지 않음.
- 추가 사용자 로그는 참고로만 대조. 과거 Base/FT 모두4B 명시,100/100 학습 종료, val3.108→표시0.000 확인. 과거 모델 오사용이라고 확정하지 않음. 원시 loss/revision은 미확인.

## 같은 날 — 로컬 앱·권한·실제 프로토콜

- FastAPI/Vue3, SQLite 소유권/공개 버전/영속 작업·이벤트, CSRF/origin/host, 실제 stdio MCP, keyword retrieval, 한 MLX 모델/worker 큐, bounded LangGraph 구현.
- 최초 fixture seed의 SQL placeholder 수 오류를 예외로 확인하고1회 수정. 이후 API/MCP/backup tests6 PASS.
- 보안/실패 테스트: 타인 사건/근거/결과/SSE/비교, 비공개 ID, 위조 capability/버전/CSRF, 큐429, cancel/timeout/STALE/restart, injection 권한 불변, 파일 traversal/symlink, invalid model/PARTIAL, 빈 검색/모델 호출0 검증. 실제 LLM의 공격 저항성이나 의미적 인용 충분성 전체를 보증하지 않음.
- 실제 MLX 브라우저 CUA 실행:304px와1265px에서 데모/사건 선택→실제 이벤트→v1보류→본인 확인 v2충돌→인용 원문→비교→무관 날씨 v3판단 유지. report-final.json/report-desktop.json, console warning/error0.
- 별도 localhost:8110/8111의 명시적 fixture 서버에서 취소/부분 완료/모델 로딩 실패 UI와 모의 호출 표기를 검증. fixture 데이터와 실제 모델 결과를 분리. 한국어 취소 문구 재확인 후 임시 서버/탭 종료. 실제 서버127.0.0.1:8100은 유지.
- impeccable의 별도 읽기 전용 마무리 검토에서 지적한4개: fixture 사용량 표시, 이전 결과 시간순 필터/선택 초기화, 양쪽 근거·인용, 모바일 분석 버튼 위치를 반영. detector1회 결과[]; 두 번째 detector 실행 안 함.

## 같은 날 — 재설치·복구·최종 검증

- `pip freeze`로 requirements-lock-macos-arm64.txt 저장. 새 `outputs/runs/20261020-clean-install/venv`에 실제 설치/`pip check`: exit0.
- 새 고정환경의 `scripts/validate_local.py --out outputs/runs/20261020-clean-install/final-validation`: exit0. pytest41개, compileall, pip check, 공정 비교 모두PASS. 명령·시작/종료 KST·exit code·로그 위치는 summary.json.
- 새 환경에서 기존 캐시/어댑터 실제 Metal 추론과 구조 검증PASS. 첫 시도는 직전 서버 종료 중 MODEL_BUSY로 차단되어 프로세스 종료 확인 후1회 재시도. lock을 우회하거나 모델을 겹쳐 로드하지 않음.
- `npm ci`/`npm run build`: exit0. install/build 로그는 clean-install 디렉터리. UI 최종 bundle 약83kB JS/10kB CSS(압축 전); 속도 benchmark로 주장하지 않음.
- `operations.py backup`, `restore`, `check`: 각 exit0, 새 DB 파일 사용. SQL dump hash 동일/integrity ok/mode0600. 원본 DB/데이터/어댑터/평가 덮어쓰기 없음.
- 활성 서버 중 두 번째 `LocalModel.load`: exit1/MODEL_BUSY 의도된 거부PASS, 기존 ready=true 유지. process-lock-test.json.
- `git diff --check`, 최종 compileall: exit0. 원본14개 산출물 SHA 전부 유지. 별도 운영/최종 평가 차단 항목은 ISSUES와 EXECUTION_CHECKLIST에서 미완료로 유지.

새 학습 후보0/3, 유료 API0, GPU 구매0, 공개 배포0, 원문 외부 전송0. 단위/fixture와 실제 MLX 결과를 혼합하지 않았다.

## 2026-10-20 KST — 사용자 후속5항목/개인 로컬 운영

- 사용자는 목표 환경을 이 Mac의 로컬 전용으로 지정했다. 검수 담당자/검수 완료 자료는 추가 제공되지 않았다.
- ledger/dataset_control: 기존360건의 학습/검증/개발 노출 기록, v1/v2 작성12건씩을 더해384개 기록. 원문/정답은 이력에 넣지 않고 보호된 서명을 사용한다. 기존360건을 새 독립 분할에서 제외했다.
- 검수 대기 v1의 [E1] 표기가 기존 E1: 계약과 달라 전체 검증 중1건이 실패했다. 최초 final-validation/원본 묶음을 보존하고 생성기·fixture를 수정해 review-packet-v2를 새로 만들었다. v2 구조 계약 오류0, 사람 검수/역할/이력 게이트는 BLOCKED. 실제 사람 승인 기록0.
- 해시 결합 목적별 대화형 검수/철회, family connected components/정확·정규화·숫자 템플릿·Jaccard 유사 후보·과거 노출·정답 계약 검사를 추가했다. 유사 탐지가 의미 중복 전부를 찾는다는 주장은 하지 않는다.
- OS verifier를 실제 data/processed/test.jsonl와 실제 서비스PID로 실행: exit2/BLOCKED. 현재 서비스/evaluator UID501, 같은 볼륨, 서비스 open 성공. sudo -n -l은 password required. 계정/보호 볼륨은 생성하지 않았고 비밀번호를 수집하지 않았다.
- freeze_training_cycle은 live 감사/OS 접근/실제 토큰 길이를 통과해야만 새 train/valid 파일과 모델·코드·자료 hash를 고정한다. train_local의 기존 approval.json true 경로를 제거하고 실패 포함3회 영속 예산을 추가했다. 실제 후보0/3, freeze 차단/출력 미생성/예산 미예약을 실제 명령으로 확인했다.
- A~F 계획은 모두 NOT_RUN. compare_af는 누락 행/자료·모델·출력 조건/어댑터/비용을 확인한다. 승인 코퍼스나 실제 여섯 실행 성능을 만들었다고 보고하지 않는다.
- local_auth: mode0700/0600의 새 자격정보, 로컬 폼→1시간 HttpOnly/SameSiteStrict 세션, 서버 재시작/설정 변경 시 거부, 최대16세션. API Basic도 점검용으로 허용. 키는 출력/커밋하지 않았다.
- 최초 내장 브라우저 Basic 창 실패 후 폼을 추가. no-referrer 폼 Origin:null 거부는 공식 Fetch 표준과 실제 헤더를 확인해 same-origin referrer 정책으로 수정. Origin null/교차 출처 검사를 우회하지 않았다. 진단 print는 제거했다.
- 실제 인증 브라우저 E2E: 실제56개 LoRA/MLX v1보류→v2충돌→v3유지/근거/비교 PASS. 새 인증 UI 관측 폭592/607px. 입력/버튼48px, 오류 포커스/aria 연결, 대비 측정 PASS. 초기304/1265px 앱 검증을 새 로그인 모바일 검증으로 전용하지 않는다.
- 실제 로컬 MLX 부하:6개 합성 세션/동시12요청,9완료/3개429. 무인증/잘못된 키401·타인404·CSRF403. raw final p95=max 집계 오류는 보존 후 같은9개 영속 작업으로 corrected 파일에서 선형 보간 정정, 추가 추론0. 지연/호출/토큰/실제 작업 ID 보존.
- 삭제 journal/서버 중단 잠금/secure_delete+compact/복구 재적용/기동 중간중단 재생을 추가. verify_deletion_recovery.py 실제 CLI6명령 exit 기대값 통과. 삭제된 사건·증거·작업·이벤트가 과거 백업 복구 후 없음, 세션 폐기/다른 사건 유지/0600/integrity PASS. 백업 바이트는 남으며 물리 삭제/보존기간은 미확정이다.
- clean locked venv의 scripts/validate_local.py --out outputs/runs/20261020-next-gates/final-validation-retry1:57 tests/compileall/pip check/기존 비교 모두exit0, 원본14개 SHA 유지. npm build exit0. 추가 집계 수정은 같은 평가 percentile 함수를 재사용하며 별도 compile/소스 확인을 수행했다.
- 모든 새 결과는 outputs/runs/20261020-next-gates. make serve는 현재 개인 인증/독립 삭제 journal/실제 모델로 유지. 유료 호출0/공개 배포0/실제 판결문 원문 외부 전송0. LOCAL_VALIDATED만 유지한다.

## 2026-10-20 13:40–13:44 KST — 프론트·백엔드 폴더 구분

- 사용자 요청으로 Python 서비스/도구/학습/평가/테스트/requirements/환경 예시를 backend/로 이동했다. Vue는 frontend/에 유지하고 로그인 HTML·브라우저 검증 스크립트도 frontend/로 모았다. 공유 data/outputs/runtime/.venv는 이동하지 않았다.
- Makefile, pytest.ini, 서비스 공용 경로와 MCP 자식 실행 디렉터리, CLI 기본 경로·학습 launcher·검증 도구를 새 구조에 맞췄다. 과거 실행 로그의 명령/경로는 당시 기록으로 보존했다.
- `.venv/bin/python backend/scripts/validate_local.py --out outputs/runs/20261020-folder-split/validation`: 13:40:36–13:40:43 KST/exit0. 57 tests/compileall/pip check/기존54건 비교 PASS, 원본 산출물14개 SHA 유지. 상세 명령·시각·종료코드는 validation/summary.json.
- backend/에서 `../.venv/bin/python -m pytest tests -q --tb=short`: exit0/57 passed(6.37초). backend/의 운영·동결·평가·학습 CLI10개 --help도 13:43:48–13:43:49 KST/모두exit0, backend-cli-help.json. 새 학습/평가 실행은 하지 않았다.
- frontend/에서 `npm run build`: exit0. 프록시 수정 후 최종 빌드도 exit0, frontend-build-final.log. requirements4개와 로그인 HTML의 이동 전후 바이트 동일, move-integrity.json.
- make serve로 새 backend/ 서버를 기동했다. HTTP 로그인/정적 자산/실제56개 LoRA readiness·MCP를 거친 MLX 합성 분석1건 COMPLETED/INSUFFICIENT를 확인했다. JOB-6884bdcc36aa4290, 실제 모델1호출. 후속 재검사는 같은 저장 작업을 확인했고 추가 추론0.
- 첫 개발 프록시 로그인은 Vite 문자열 프록시 기본값이 Host를 바꿔 ORIGIN_DENIED403/exit1이었다. 명시적 changeOrigin:false로 수정1회 후 개발 로그인·API·CSRF 쓰기·교차 출처 거부를 확인했다. 인증/Origin 경계를 완화하지 않았다. runtime-smoke.json은 실패 원인과 최종 HTTP 검증의 시각/exit0을 기록한다.
- 근거는 outputs/runs/20261020-folder-split/. 실제 브라우저 화면 재검증을 했다고 주장하지 않는다. 모델·검수·OS 격리/승격 상태는 그대로다.
