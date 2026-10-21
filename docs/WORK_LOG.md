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

## 2026-10-20 KST — 공개 자료 검수·암호화 정답 볼륨 준비

- 사용자 요청으로 공개 KLUE NLI/LBOX 요약/KoBLEX QA48,224건을 격리 수집했다. 출판자 라이선스/README/원자료13파일의 upstream Git blob/LFS 해시를 검증했다. 법령233,544개는 조각 단위이며 학습 정답 사례 수가 아니다. 정확 중복3쌍/어휘 유사 후보69쌍 등은 collection run의 품질 보고서에 보존했다. 유사 탐지는 의미 중복 완전 검사가 아니다.
- collection run 20261020T132133+0900-external-data-b57016, 최초 검수 패킷 20261020T132756+0900-review-evaluation-ab725f, 현재 격리 run 20261020T134803+0900-isolation-review-0385fc. 기존 원본/어댑터/평가를 덮어쓰지 않았다.
- 자동 검사892건 중 NLI 보조 주석자 불일치140건(학습 후보67/검증41/진단32), 시계 검교정 시나리오3건을 우선 검수 대상으로 기록했다. 개인정보 패턴 탐지와 출판자 정답 일치는 실제 비식별화/의미 검수를 대신하지 않는다. 사용자가 직접 검수하기로 했으나 실제 사람 검수·목적 승인 기록0건이다.
- 보호 APFS sparseimage를 AES-256 이미지 암호화로 생성하고 정답7개를 UID501/0600, 보호 디렉터리0700으로 복사했다. 최초 mounted isencrypted 조회는 resource busy로 실패해 기록을 보존했다. 정확한 자체 이미지 장치만 detach한 후 암호화를 확인하고 owners on으로 다시 attach했다. 별도 st_dev와 실제7개 SHA 일치. 비밀키는 로컬0600 파일이며 출력/외부 전송하지 않았다.
- 전용 비관리자/로그인 불가 서비스 계정·분리 배포·기존 서버 검증 후 전환·실제7정답/작업 폴더 사본 접근 거부를 수행하는 관리자 helper를 준비했다. native 관리자 인증은300초 무응답 시간 초과, wrapper exit1. root helper 실행/계정/배포 생성0, 기존 PID1399/UID501 서버 유지. 실제 분리 계정 접근 거부는 NOT_RUN이며 OS 격리 BLOCKED로 기록했다. 관리자 인증 실패를 정답 접근 거부 PASS로 바꾸지 않는다.
- 폴더 분리에 맞춰 새 준비 패킷을 만들고 입력/정답/검수 subject 바이트를 유지했다. 도구/프로토콜 해시 확인 launcher와 실제 사람 TTY 검수, 목적별 승인/OS 경로·해시/잠금 preflight를 연결했다. 학습 후보는 main guard에 맞는 rank8/8layers 설정3개 제안만 보존하며 native NLI의 freeze/3회 ledger 연결 전 학습하지 않는다.
- .venv/bin/python -m pytest backend/tests -q: 13:56:15–13:56:22 KST/exit0/66 PASS. 준비 패킷 test_workflow.py: 13:56:22 KST/exit0/16 PASS. 새 NLI preflight: 같은 시각/예상 exit2, 사람 검수/OS 격리/현재 모델 점유를 이유로 모델 로드 전 거부. 정확한 명령/시각/로그는 workflow-verification-execution.json.
- 최종 원본14개·출판자13개·보호 정답7개 총34해시 일치. preservation-verification.json. 이번 준비 작업의 새 모델 평가/학습/추론0, 유료 호출0/공개 배포0/원문 외부 전송0. 실제 완료 범위와 로컬 관리자/검수 인계는 START_HERE.txt/STATUS.json에 기록했다.
- 최종 현재 서비스UID501/PID1399와 평가자UID501로 보호 정답7개를 실제 probe했다. 모두 현재 서비스UID 읽기 성공으로 예상 BLOCKED이며 분리 계정 거부 성공이 아니다. current-isolation-verification.json, final-live-check.json에 기존 서버 ready=true/추가 추론0을 기록했다. 최신 상태는 STATUS-final.json이며 관리자 helper 해시와 검수 ledger 부재도 다시 확인했다.

## 2026-10-20 14:28–14:31 KST — 사용자 요청의 관리자 재인증

- 기존 helper SHA/현재 PID1399/미생성 서비스 계정을 다시 확인하고 read-only 적용 계획을 administrator-attempt-2-plan.json에 보존했다. helper 변경/계획 우회 없음.
- native 관리자 요청14:28:21.090729–14:31:19.913721 KST, exit1/timeout=false. 관리자 명령 실행 단계에서 Python이 Downloads의 configure_local_isolation.py를 열지 못해 errno1/Operation not permitted를 반환했다. 계정 생성 코드의 progress/적용 결과는 생성되지 않았다. 첫300초 시간 초과와 다른 원인이며 별도 execution/diagnostic JSON에 기록했다.
- 터미널 앱을 직접 조작하려는 CUA 호출은 'Computer Use is not allowed to use com.apple.Terminal for safety reasons'로 거부됐다. 이를 다른 UI 경로로 우회하지 않았다. 사용자에게 기존 터미널에서 준비된 sudo 명령을 직접 실행하도록 안내했다. 비밀번호 수집/출력0, 전역 개인정보 보호 허용 확대0.
- 정답을 읽는 현재 UID501 서비스를 분리하는 목적과 비관리자/로그인 불가 계정 범위를 설명했다. 실제 사람 검수·모델 재평가·새 학습 상태는 변하지 않았다. 사용자 터미널 실행 결과가 생기면 실제 계정/실행UID/7파일 거부를 검증해야 한다.

## 2026-10-20 14:38–14:43 KST — 사용자 터미널 적용·중단 복구·OS 실측 PASS

- 사용자가 준비한 sudo 명령을 실제 터미널에서 실행해 _recase_service UID/GID499와 분리 배포를 생성하고 기존 PID1399를 종료했다. readiness 대기 중 Ctrl-C가 발생해 원래 helper의 Exception 처리에서 KeyboardInterrupt를 복구하지 못했다. 다시 create를 실행하면 기존 계정 보호가 거부하는 것이 정상이며 계정 삭제/재생성으로 우회하지 않았다.
- 실제 PID31016/UID499 readiness503/PermissionError를 확인했다. app/runtime은 root0700이었다. private umask077 뒤 mkdir0755가 축소된 것이 직접 원인이다. 새 초기 설정은 명시 chmod0755, 진행 단계 출력, KeyboardInterrupt 복구를 추가했다. 기존 데이터/계정/DB를 유지하는 finish_local_isolation.py를 별도로 만들고 확인한 배포/계정/launchd/plist/잠금 inode 외 변경을 거부하게 했다. 실제 적용은 사용자의 로컬 터미널에서만 수행했다.
- backend83 tests PASS/exit0/6.36초, umask077 디렉터리 접근권한·Ctrl-C 복구·잘못된 잠금 사본/권한·HTTP503 오류 보존·다른 정답 해시/어댑터 거부 회귀 포함. 전체 명령/시각/로그는 outputs/runs/20261020T144223+0900-finish-isolation-d3c15a/test-execution.json. finish dry plan과 git diff --check도exit0.
- 사용자가 finish 명령을 실행했다. root0700→0755는 공개 model.lock 폴더 한 개이며 정답/키/state 폴더 권한을 넓히지 않았다. 기존 launch daemon을 중단하고 이전 PID 종료를 확인한 후 같은 모델/어댑터로 기동했다. 실제 새 PID41133/UID499, readiness200/ready=true/56 LoRA. root 결과는 원래 isolation run/finish-20261020T144251-f1772e/result.json과 개별 isolation-*.json7개다.
- 실제 protected answers7개 모두 서비스 UID499/EACCES, evaluatorUID501 실제 open/동일 SHA, 다른 nonroot UID/별도 볼륨/0700·0600/현재 서비스PID 결합 검사PASS. 작업 폴더의 기존 test·원래/이전 준비 NLI정답·암호화 키 총4경로도 실제 UID499 접근 거부. sudo 실패를 접근 거부로 계산하지 않았다.
- 독립 사후 대조에서 root 결과의 source SHA/현재 helper SHA/소프트웨어 테스트 seal 일치, 현재 실행PID·UID, 기존 모델 전체 metadata/56 LoRA, 원본14해시, 두 checkout의 model.lock 동일inode25076574와 실제 잠금 점유를 확인했다. 추가 모델 생성/평가/학습0. 근거 post-cutover-verification.json.
- 서비스의 현재DB·최신 삭제 journal은 /Users/Shared/RECASE-isolated-0385fc/state/다. 원래 runtime DB/기존 원본/어댑터/평가를 보존했다. 새 배포는 코드 복사본으로 자동 동기화되지 않는다. 분리 후 백업·삭제복구 재검증/실제 사람 검수는 NOT_RUN이다. OS PASS를 모델 성능/모든 복사본/관리자 차단/공개 운영 승격으로 확대하지 않는다.
- 실제 새 isolation-nli_diagnostic.json/보호 정답 경로를 연결한 prepared preflight를 실행했다. 자료·코드·도구 해시/OS 격리=true, 실제 사람 검수150건 누락/서버 모델 잠금 점유로 예상 exit2, 모델 호출0. 명령/시각/종료코드는 recovery run의 preflight-execution.json. 원래 helper 소스를 역구성해 이전 SHA a20f4f…와 일치함을 확인하고 configure_local_isolation.before_fix.py로 보존했다. 최신 사용자 안내/상태는 원래 isolation run/CURRENT_STATUS.txt와 STATUS-os-validated.json이다.

## 2026-10-20 14:51 KST — 다음 단계 실제 사람 검수 시작 준비

- 사용자의 다음 단계 요청으로 현재 review_prepared.py status를 실행했다. 봉인 자료/subject/ID/원문·정답 무결성 검사 exit0, nli_validation150건 승인0/반려0/대기150을 확인했다. 검수 순서는 최신 NEXT_ACTIONS의 설정/후보 비교용 validation을 먼저 따른다.
- 현재 CLI가 선택하는 우선10건을 같은 순서/subject SHA로 별도 암호화 볼륨의 protected_mount/reviews/20261020T145134+0900-human-review-start-203872/first_10_nli_validation.txt에 준비했다(0700/0600). 현재10건은 contradiction 단일 클래스여서 전체를 대표하는 표본/성능으로 해석하지 않는다. 모호한 의미/개인정보/권리의 승인·반려·보류는 사람이 판단한다. 자료 원문을 모델/외부로 전송하지 않았다.
- 실행 명령/시각/exit0, 기존 승인 집계와 batch subject SHA/CLI·protocol SHA/보호 파일 SHA는 outputs/runs/20261020T145134+0900-human-review-start-203872/에 보존했다. 사용자 검수 CLI는 sudo 없이 실행하며 실제 사람 입력 전까지 새 human attestation을 생성하지 않는다. 현재서비스PID41133/UID499를 유지했고 새 평가/학습0이다.

## 2026-10-20 KST — 사용자 검수 기록 확인·AI 검토 요청

- 사용자가 터미널에서 실제 검수한 이력을 확인했다. validation 승인1/대기149이며 최초 승인 근거가 yes라 실질 이유 보완을 안내했다. 해당 사람 기록을 에이전트가 수정하거나 삭제하지 않았다. OS 격리 PASS와 사람 검수 완료를 혼동하지 않았다.
- 사용자가 검토를 에이전트에 요청했다. AGENTS의 원문 외부 전송 사전 승인 규칙에 따라 공개 KLUE NLI 검증150건의 전제·가설·라벨을 이 채팅AI가 읽는 범위만 별도 질문했고, 승인 전 나머지 원문을 도구 출력에 노출하지 않았다. 판결문·사건 증거는 요청 범위에서 제외했다.
- 로컬 메타데이터150건은 출판자 라벨 일치150/보조 주석자 전원 동일109/의견 불일치41/개인정보 패턴 탐지0을 확인했다. 패턴 미탐지와 주석자 일치를 의미 정확성/비식별화 완료로 바꾸지 않았다.
- 이미 사용자가 채팅에 직접 제공한6문장은 AI 의미 검토로 따로 기록했다. 라벨 지지3건/문맥·판정 기준 재확인3건이며, 고장과 따뜻함 양립 가능성1건은 라벨/프로토콜 불일치 후보다. 출판자 오류를 확정하거나 원본 라벨·분모·사람 승인 이력을 변경하지 않았다. 나머지144건은 원문 열람 승인 대기다. 결과 outputs/runs/20261020T145811+0900-ai-review-preparation-73aa9c/AI_REVIEW_FIRST_SIX.txt 및 STATUS-after-six.json. 로컬 평가 모델 호출/새 학습0.


## 2026-10-20 14:38–14:47 KST — 남은 작업의 소프트웨어 준비와 사용자 검수 인계

- 기존 미커밋 검수/격리 도구와 문서 변경을 보존했다. native NLI용 prepared_data/native_training, review_prepared CLI, 평가/비교 실행기를 추가하고 기존 freeze_training_cycle과 experiments의 동일 전역3회 ledger에 연결했다. 기존 train_local.py/model.py/봉인 패킷의 입력·정답·검수 subject·도구는 수정하지 않았다.
- 실제 검수/목적 승인, 봉인/파일 해시, train/validation/diagnostic 계열·중복, 알려진 과거 학습 노출, 검증 라벨3개, OS 실제 probe, 실제 토큰 길이를 통과해야 동결한다. 실제 후보 시도 시 서명만 노출 이력으로 기록하며 진단 정답은 train/valid 출력에 넣지 않는다. 새 폴더로 후보 예산을 초기화하지 않는다.
- 검수 CLI는 전체892건을 대상으로 우선 확인 자료/승인·반려·대기 집계/10건씩 재개/지정 ID 재검수를 지원한다. TTY 없는 자동 yes는 거부하며 새 기록에는 라이선스 파일 해시를 포함한다. 실제 사람 검수 기록은 만들지 않았다.
- 후보 평가기는 실제 완료된 학습 ledger/같은 동결 주기/nli_validation을 요구한다. 비교는 같은 데이터·모델·프롬프트·생성·평가기·실행기 해시/비용·어댑터 실제 로드를 확인한다. 누락/무효/실패를 분모에 포함하고 품질/운영 자동 승격은 하지 않는다. NLI 어댑터를 기존 사건 앱에 자동 교체하지 않는다.
- 단일 OS 보고서의 answers 문자열과 묶음 보고서의 answers 배열을 혼동한 새 평가 테스트 실패1건을 확인해 형식 분기를 수정했다. 별도의 후보 비교 fixture 객체 별칭/실행 fixture의 빠진 해시 파일은 테스트 자료를 수정했다. 실제 모델/자료 실행 실패가 아니며 실패 출력을 숨기지 않았다.
- validation-final:14:46:23–14:46:32 KST/exit0. 전체88 tests(7.93초), compileall/pip check/기존54건 비교/원본14개 SHA PASS. 봉인 패킷16 tests도14:47:29–14:47:30 KST/exit0. 정확한 명령·시각·종료코드·로그는 outputs/runs/20261020T143802+0900-next-actions의 validation-final/summary.json, followup-verification.json.
- 실제 캐시 CPU tokenizer로 train300/validation150 전체를 검사했다. 전체 토큰 최대255/240, 768 초과0, 추론 prefix 불일치0. 가중치 로드/추론/학습/학습 파일 생성0. native-tokenizer-audit.json.
- 실제 native 동결 CLI: 미검수450건/이력 확인 누락으로 예상 exit2. 동결 출력 미생성/전역 후보 예산 불변, native-freeze-gate.json. 새 평가 preflight도 검수150건 누락·서버 잠금 점유·현재 세션의 다른 계정 probe 인증 없음으로 예상 exit2/모델 로드0. root OS PASS를 계정 전환 인증 부재와 혼동하지 않는다.
- 작업 중 새 root 격리 완료 결과를 읽고 실제 PID41133/UID499와 HTTP ready=true/MLX56 LoRA를 대조했다. 관리자 인증을 다시 요청하거나 계정을 재생성하지 않았다. 사용자 안내는 NEXT_ACTIONS.md로 갱신했다.
- UID499의 현재 서비스에 기존 합성12요청을 실제 전송:9완료/3개429, 미인증/잘못된 키401·타인404·CSRF403. 실제 MLX/MCP9호출, 14:46:23–14:46:43 KST/exit0, isolated-service-load.json. 큐 포함 p95 18.279초이며 동시 CPU 검사 중의 짧은 기능 부하로 일반화하지 않는다. 새 공개 자료 재평가/학습과 구분한다.
- 현재 사람 검수0/새 자료 재평가0/새 학습0/3/A~F0/6. 유료 호출·공개 배포·원문 외부 전송0. OS 검증 범위 밖 사본, 비공개 최종셋, 승인 판례 RAG, 분리 배포 백업/삭제복구 재검증, 자동 보존기간은 후속 조건으로 남긴다.


## 2026-10-20 KST — 격리 서비스 운영 백업·복사본 삭제복구 준비

- 사용자 '다음 진행'에 따라 실제 검수 현황을 재확인했다. 892건 승인/반려0, 새 학습/평가 조건은 미충족이다. `/usr/bin/sudo -n -u _recase_service -- /usr/bin/id -u`: exit1/password required. 실패한 계정 전환을 서비스 OS 접근 거부 PASS나 UID499 운영 검증으로 계산하지 않았다.
- operations_drill.py는 실제 선택된 비root UID/배포 모듈/0600 입력/현재 독립 journal/충분한 디스크를 확인하고 mode=ro SQLite 백업만 읽는다. 새 private copy에 합성 사건을 추가한 뒤 그 사건만 삭제/복구해 tombstone·세션·대기 작업·다른 사건·백업 보존을 검사한다. 원본 운영DB/삭제 journal/기존 백업 삭제·덮어쓰기0, 모델 호출0이다.
- verify_isolated_operations.py는 현재 UID/PID/배포 경로/배포 코드·worker·정책 해시를 고정한 계획을 만든다. root --apply는 이미 있는 서비스 UID로만 worker를 실행하고 metadata 결과만 operator에게 반환한다. 새 worker 프로세스 그룹에만 제한된 timeout/중단 처리를 하며 서비스/계정/모델은 변경하지 않는다. 실제 적용은 사용자 로컬 터미널의 관리자 인증이 필요하다.
- 최초 읽기 전용 plan은 공개 파일이 root 소유라는 가정 때문에 exit1이었다. 실제 clonefile 공개 소스는 UID501/0644이며 디렉터리는 root 소유였다. 서비스 계정의 쓰기를 막는 root 디렉터리·operator/root0644·정확한 해시를 확인하도록 조정했고 evaluator에 대한 불변성 경계라고 주장하지 않는다. 실제 소유권/권한 변경0. 초기 실패는 planning-initial-failure.json에 남겼다.
- 새 unit fixture의 공개 파일600 모드가 실제 배포644와 달라1개 실패했다. fixture 모드를 실제와 맞추고 worker의 임시 umask도 복원하게 해8개 테스트를 통과했다. 새로운 복구 검증은 복사본의 QUEUED 작업을 SERVER_RESTARTED로 실패 처리하고 원래 fixture의 QUEUED 상태를 보존한다.
- 실제 배포 venv/bin/python -I와 실제 배포 store/ledger/retention 모듈을 실행한 UID501 새 합성 DB 검증: exit0. 원래 fixture DB/독립 journal SHA 동일, 복구 대기 작업1건 FAILED/SERVER_RESTARTED, 삭제/세션/다른 사건/0600/무결성/재적용/백업 바이트 보존 PASS. 실제 UID499/운영 state 실행이 아니다. operator-fixture-final-execution.json/result.json.
- 최종 계획 생성14:58:16 KST/exit0, full validate14:58:16–14:58:23 KST/exit0. pytest96개/6.45초, compileall/pip check/기존54건 비교와 원본14개 SHA PASS. 정확한 명령/시각/코드는 final-verification.json/validation-final/summary.json. 초기 plan/첫 validation/fixture 결과도 보존했다.
- 정책 local-synthetic-manual-v1을 현재 수동 동작의 문서로 고정했다. 명시적 사건 선택/최신 journal 보존/새 복구본/세션 폐기/명시적 백업 폐기만 허용한다. 자동 기간 삭제/스케줄러를 설치·활성화하지 않았다. 실제 자료/파생본·물리 삭제는 별도 조건이다.
- run outputs/runs/20261020T145215+0900-isolated-operations/. plan-final.json을 사용하며 이전 plan은 worker 변경 전 초안이다. UID499 운영 결과는 사용자 실행 전 NOT_RUN, 사람 검수0·새 학습0/3·A~F0/6 유지. 유료 호출·공개 배포·원문 외부 전송0.

## 2026-10-20 15:03–15:07 KST — 사용자 UID499 백업·복구 실행 확인과 다음 검수 준비

- 사용자가 기존 plan-final.json --apply를 로컬 sudo 터미널에서 실행했다. 실제 execution.json은15:03:11.041–15:03:11.173 KST/exit0, result.json 완료15:03:11.179 KST/PASS다. 실제 UID/EUID499·배포 venv/SQLite 모듈·운영 DB 읽기 전용 백업·최신 journal 복사/보존을 확인했다. 스냅샷80사건/운영 journal1기록이며 삭제는 새 복사본의 새 합성 사건에만 수행했다.
- tombstone 재적용/멱등성·대상 증거/진술/job/events 제거·다른 사건 보존·복구 세션 폐기·0600/무결성·백업 바이트 보존 모두 PASS. 실제 스냅샷에는 대기 작업이 없어 SERVER_RESTARTED 전환0건이며 해당 전환1건은 기존 UID501 합성 fixture에서 검증했다. 운영 삭제/모델 호출/학습/서비스 중단0. 백업은 UID499 전용0700 scratch에 남으며 내용은 operator/채팅으로 복사하지 않았다.
- 사후 확인 스크립트 최초 실행은 잠금 소유자 인수에 service_uid를 넣어 exit1이었다. 실제 승인 잠금은 owner501/group499/0660·같은 inode25076574이며 서비스 오류가 아니었다. 기존 helper 호출과 대조해 검증 스크립트의 인수만 operator_uid로 고쳤고 실패 원본/진단을 보존했다. 계정/잠금/권한 변경0.
- `.venv/bin/python outputs/runs/20261020T150521+0900-operations-confirmed-6923ae/verify_receipt.py`:15:05 KST/exit0. receipt 소유자/0600·계획 digest·helper/worker/정책/배포 모듈·실제 worker 인수/UID/exit0·검증 항목·현재 서버/모델/잠금 등19개 대조 PASS. 현재 PID41133/UID499·인증된 ready=true·기존56 LoRA. 기존96 tests의 backend baseline도 그대로이며 운영 검증이나 모델 테스트를 불필요하게 재실행하지 않았다. 근거 verification.json.
- 실제 사람 ledger 재확인: validation 승인1/대기149, 전체1/892. 최초 승인 근거 yes는 의미 있는 근거 보완 권고만 남겼고 기존 기록/라벨/분모를 변경하지 않았다. native NLI 감사는 학습용300+검증149 승인 누락449건 및 노출 이력 확인 누락으로 BLOCKED. 새 학습 예약/파일/모델 로드0.
- evaluate_prepared.py preflight는15:05:50–15:05:51 KST/예상 exit2. validation149건 승인 누락·현재 실행 세션의 계정 전환 인증 부재·서버 모델 점유로 모델 로드 전 거부했다. preflight-execution.json/validation-preflight.json. 기존 root OS/운영 PASS를 취소하거나 관리자 인증 실패를 파일 접근 거부로 계산하지 않았다.
- CLI가 선택할 다음10건을 별도 보호 볼륨 reviews/20261020T150521+0900-operations-confirmed-6923ae/next_10_nli_validation.txt에0700/0600으로 준비했다. 원문을 도구 출력/채팅에 노출하지 않고 metadata/subject SHA만 next-review-batch.json에 기록했다. 실제 사람 승인 생성0, 새 자료 평가0·새 학습0/3·A~F0/6. NEXT_ACTIONS/상태/운영/체크리스트/인계 문서를 갱신했다. 다음은 sudo 없는 사람 검수이며 성공한 --apply 재실행은 불필요하다.

## 2026-10-20T15:05:56.982122+09:00 — 사용자 승인 공개 NLI150건 AI 의미 검토 완료

- 사용자가 이 채팅AI에 공개 KLUE NLI 검증150건의 전제·가설·제안 라벨 열람을 명시 승인했다. 원문은 이 범위만 읽었으며 LBOX 판결문·사건 증거를 포함하지 않았다. 사용자 위임 승인/실제 AI 수행을 구분해 authorization.json에 기록했다. 사람이 직접 읽었다는 이력으로 바꾸지 않았다.
- 150건을25건씩 실제 읽고 각 subject SHA/원라벨/AI 제안/확신 수준/판단 근거를 기록했다. 라벨 지지133건, 문맥·판정 기준 재확인12건, 라벨 수정 후보5건이다. 제안 라벨을 보고 검토했으므로 blind 평가가 아니며5건은 출판자 오류 확정이 아니다. 개인정보·인물 출처 맥락 후보13건/문구 품질7건도 별도 기록했다.
- 모든150ID의 유일성·누락0·근거150·원본 subject 결합·supported의 원라벨 일치·입력/정답 SHA 보존·human ledger SHA 보존을 검사해exit0을 확인했다. 기존 사용자 직접 승인1건(근거 yes는 보완 필요)/대기149건은 변경하지 않았다. 추가 사람 승인·원라벨 변경·분모 제외0. 원문 포함 상세150건/우선17건 보고서는 별도 암호화 볼륨의0700/0600에 저장했다.
- 개발 품질 검토 노출150건을 기존 exposures.jsonl 뒤에 locked_records/append_locked로 추가했다. 원래384건 prefix를 보존하고 총534건의 hash chain을 확인했다. 서명/해시만 남겼고 원문·정답을 노출 ledger에 쓰지 않았다. 로컬 Qwen 노출/학습이 아니라 사용자 승인 채팅AI 검토다. 새 human history coverage attestation은 만들지 않았다.
- 결과 run outputs/runs/20261020T150037+0900-ai-semantic-review-4f0bf5/: RESULT.txt, summary.json, ai-reviews.jsonl, proposed-label-changes.json, priority-17.json, privacy-context-review-13.json, verification.json, exposure-registration.json. 원래 검증셋150건에서17건을 임의로 빼지 않는다. 기존 검수/동결/OS/3회 ledger를 우회하지 않았고 새 로컬 모델 재평가/학습/유료 tool API/공개 배포0이다.

## 2026-10-20 — 사용자 '검수 해줘' 요청의 AI 후속 검토

- 작업 폴더에 이미 완료된 공개 NLI150건 AI 검토를 확인해 기존 결과를 보존했다.150개 ID/subject/원라벨/판단 근거와 현재 봉인 입력·정답·기존 사람 ledger 해시를 실제 대조했다. 현재 요청 범위는 공개 NLI 검증셋이며 다른 자료/판결문/사건 증거 원문을 열람하지 않았다.
- 쟁점17건의 원문·제안 정답을 이 채팅 AI가 읽고 두 번째 의미 판단을 기록했다. 기존 나이/배우자 해석1건을 수정 후보에서 문맥 판정으로 낮추고, 경기 투입/전반 출전1건은 외부정보 보충 금지 지침 아래 원neutral 지지로 정리했다. 최종134지지/12문맥 판정/4수정 후보이며 출판자 오류 확정 수가 아니다. 나머지133건은 이전 AI 판단을 유지했다.
- 원문 포함 후속17건·병합150건·우선16건·수정 후보4건은 별도 암호화 볼륨0700/0600에 저장했다. 원본 라벨/분모150·사람 승인1/대기149를 유지했다. 기존 개인정보 맥락13/문구 품질7 표시는 검수 완료로 바꾸지 않았다. 사용자 명의의 human attestation 생성0.
- 최초 노출 기록 append는 locked_records 기본 read-only descriptor 때문에 io.UnsupportedOperation/exit1이었다. 실제 ledger534기록/SHA d9c726… 불변을 확인하고 진단을 보존했다. 기존 ledger를 먼저 검증한 뒤 create=True writer mode를 써17건만 추가하는1회 복구로 성공했다. append 전534 prefix 바이트/chain 보존, 최종551기록 검증. 원문/정답을 ledger에 쓰지 않았다. 소스 코드 수정0.
- 정확한 완료 시각·명령·exit0은 outputs/runs/20261020T151035+0900-ai-review-followup-95bc0c/execution.json, 구조/보존 검증은 verification.json, 첫 실패는 initial-write-failure.json. 결과 요약 RESULT.txt/summary.json, 노출 확인 exposure-registration.json. 새 로컬 모델 호출/평가/학습·후보 예약/승격/gate 수정0. 실제 사람 개인정보·권리 검수와 처리 목적 승인 요건은 유지한다.

## 2026-10-20 —16건 후속 처리안과 실제 사용자 문구 선택 적용

- 사용자 요청에 따라 기존 검토의 결론을 처리안으로 구체화했다.16개 원문·라벨이 출판자 로컬 파일과 정확히 같고 해당 파일의 upstream Git blob SHA도 일치했다. 수집/변환의 오타·라벨 반입 오류0이며 원문에 있는 주석·문구 쟁점이다. 보조 주석자 투표는 근거로만 보존하고 새로운 strict gold 확정에 쓰지 않았다.
- 기존 수정 후보4+엄격 지침 적용7의 라벨 제안11건을 별도150건 초안에 반영했다. 의도 복원이 어려운5건(92/1478/296/2202/2077)은 원문과 명시 조건을 추가한 별도 AI 진단 예문을 나란히 준비했다. 원본/공식 라벨/분모150/human ledger/후보 ledger를 보존했고 ID·데이터셋/subject SHA를 새로 만들어 이전 승인 자동 이전0을 확인했다. 같은 case_family 유지, 새 독립 최종셋으로 합산0.
- 사용자가 현재 채팅의 선택 질문에 '5건 모두 별도 재작성안 사용 (권장)'으로 직접 응답했다. wording-selection.json에 정확한 응답·대조표 SHA·선택5개를 기록했다. 이 응답은 문구 사용 결정이며 최종 라벨·개인정보·라이선스·목적 검수 승인으로 바꾸지 않았다. 원본/첫 초안을 유지하고 별도 wording-selected-draft에 적용했다. 문구 대기0, 문장 변경5/라벨 차이12(기존11+재작성 중1). 가상 인물/기관·정책과 배타·전체 조건은 새 작성 사실로 표시했으며 실제 인물의 나이/현행 세법/출판자 의도 복원으로 주장하지 않았다.
- 새 작성5건의 해시·서명/동일 source family를 개발 노출 ledger 뒤에 append했다. 원551개 prefix/chain 보존, 총556개 검증. raw 문장/정답을 ledger에 쓰지 않았고 신규 독립 계열로 계산하지 않았다.
- 새150건 review-packet을 보호 볼륨0700/0600에 봉인했다. 현재 source guard3개 추가, 원봉인 scorer bytes 재사용, 실제 load_packet/150개 subject/ID·입력·정답/권리 파일 hash 결합 PASS. 실제 status 승인0/대기150, 원래 사람 승인1건 불변. 기존 파일·초안 보존 검증 PASS.
- 실제 evaluate_prepared preflight15:40:43–15:40:45 KST/예상 exit2: 미승인150·새 정답 hash6804ec88…에 대응하는 실제 OS proof 없음·현재 모델 점유. 모델 로드/추론/학습0. 이전 정답7개 격리 PASS를 새 정답에 재사용하지 않았다. 새 실제 OS 검증과 최종 사람 검수 전 평가·학습 활성화0.
- 근거 run outputs/runs/20261020T153504+0900-nli-disposition-draft-f94ac8/. build_draft.py/verification.json, apply_wording_selection.py/wording-applied-verification.json, prepare_review_packet.py/review-packet-verification.json, revised-preflight-execution.json/START_HERE.txt. 모두 실제 exit0이며 preflight 자식만 예상 exit2다. 앱/서비스/학습·평가 gate 소스는 수정하지 않았다. 관리자 인증/서비스 중단을 다시 요청하지 않았고 사용자 문구 선택은 모두 완료했다.
- 최종 실제 검수 CLI status exit0/승인0/대기150, pending_items가 변경16건을 먼저 선택함을 확인했다. 원문·원라벨/제안문장·제안라벨/근거 대조표 FINAL_REVIEW_16.txt를 보호 볼륨에 준비했다. 최초551기록 prefix의 SHA를 baseline과 다시 대조하고 최종556 chain/이전 산출물 hash/git diff --check를 확인했다. final-verification.json/FINAL_HANDOFF.txt. 문구 관련 추가 판단 대기는0이며 실제 사람 최종 검수/새 정답 OS 검증만 별도 조건으로 남긴다.

## 2026-10-20 KST — 메인·사건 화면 디자인 통합

- 사용자 요청에 따라 차콜·웜 골드·아이보리 토큰과 공통 브랜드/헤더/조작부를 적용했다. `/cases` 기록 검색·선택과 `/cases/:id` 검토실을 분리하고 증거·분석·비교·이력, 메인·관리자·개인 로그인 스타일을 통일했다.
- 프론트 typecheck/build/Node5 tests/diff exit0, explicit fixture 데스크톱/390px 전체 증거 공개·분석·인용·비교 PASS,320px 목록·검토실 가로 넘침 없음. 명령·시각·결과는 outputs/runs/20261020T154203+0900-design-unification/와 docs/frontend/11-design-system.md에 기록했다.
- 원본14개·제공 이미지12개·이전 검증 backend 해시 보존. 기존8100 운영 사본 배포/실제 MLX 새 호출/학습/유료 호출/외부 전송0. 모의 미리보기는 localhost:8123이며 전체 서비스 준비 판정을 승격하지 않는다.

## 2026-10-20 KST — 사건 기록 화면의 과한 표현 제거

- 사용자 'ai 느낌 없애줘 그 페이지 부분' 요청에 따라 `/cases`의 대형 슬로건/R/영문 장식/행 순번을 제거하고 실제 제목·요약·증거 버전 중심으로 정리했다. 첫 입장·빈 분석·증거 공개 안내도 담백하게 수정했다. 메인 랜딩/hero.js와 backend는 수정하지 않았다.
- typecheck/build/5 tests/diff exit0, 명시적 fixture 데스크톱/모바일 전체 분석·인용·버전 비교 PASS,390px/320px 가로 넘침 없음. 근거 outputs/runs/20261020T160214+0900-cases-refinement/ 및 docs/frontend/12-cases-refinement.md. 8123 미리보기 반영,8100 운영 배포/실제 MLX 새 호출/학습/유료·외부 전송0.

## 2026-10-20 KST — 남은 세 단계 후속 구현·실측과 보존기간 선택

- native600건(train300/사용자 선택 검증150/개발 진단150)을 새 보호 패킷으로 봉인했다. 원학습 바이트/원검증 계열/실제 loader/변경16건 우선 순서 PASS. 실제 freeze는 미검수450·이력 확인 누락으로 예상 exit2, 주기 생성/모델 로드/새 학습0이며 전역0/3 유지. 새 승인 이력/노출 ledger 변경0. 준비 metadata의 진단/검증 필드명 착오를 발견해 원본 보존 후 canonical native-readiness.json에 근거와 함께 정정했다.
- 참고 판례 검색/MCP에 목적별 승인·원문 SHA·출처 유형·정확 quote offset·최신 철회를 연결했다. Recall/MRR는 누락 질의를 분모에 포함하고 구간 무결성을 의미적 인용 지지와 구분한다. 합성 fixture 실제 stdio 검색→철회→BLOCKED PASS. 테스트 attestation은 임시 fixture뿐이며 실제 판례 승인/연결/품질 측정은 NOT_RUN이다. UID499 배포와 주 그래프 A~F 연결도 미완료다.
- 실제 서비스UID499/PID41133에600초·직렬최대60건·개별30초를 먼저 고정한 지속 시험을 시도했다. 첫 자체 합성 작업이30초 내 미완료로32.566초에 FAIL/exit2 중단, 완료0·후속 제출0이다. 취소 요청200이나 최종 취소 상태 미확인, 진행 중 총 모델 호출 NOT_MEASURED. 원리포트의 완료 usage0 해석을 별도 보완하고 이후 도구도 미완료 총수null로 수정했다. 스왑 사용 관측은 원인 확정이 아니다. 읽기 전용 관리자 집계 명령을 준비했고 DB 권한 확대/서비스 재시작/원인 없는 추론 재시도0이다.
- 사용자 직접 응답 ‘사건 90일, 백업 30일’을 별도 비활성 정책에 기록했다. 활성 수동 정책 SHA 보존. 새 메타데이터 미리보기의90일/30일 정확 경계·timezone·날짜 미상·실제 자료 제외·보류·복구 미확인 백업 검증 PASS. 실제 lifecycle 시각 migration/UID499 inventory/완전 폐기는 NOT_RUN이며 실제 삭제/백업·키 폐기/스케줄러 설치0이다.
- impeccable audit 적용: fixture desktop1265×720 키보드·건너뛰기·대비·overflow 확인, 구체적 미공개 heading 노출0. 사건 전환 후 focus/제목 권고, 실제 VoiceOver/확대/교차 브라우저 미실행. context orphan경고는 실제 파일 존재를 확인해 기준 경로 설정 문제 후보로만 남겼다. UI/설정 수정0이며 다른 진행 중 frontend 변경은 보존했다.
- 전체122 tests/compileall/pip check PASS, 최종 소스·명령·시각·종료코드/원본14개 보존은 run의 final-verification 기준. 앞선119/122 tests 기록과 실제 실패를 보존했다. 근거 outputs/runs/20261020T155158+0900-remaining-work-b82291/RESULT.txt 및 USER_NEXT_STEPS.txt. 새 학습/사람 승인/유료 호출/공개 배포/실제 판결문 원문 외부 전송0. LOCAL_VALIDATED 유지.

## 2026-10-20 KST — 사건 화면 선·정렬 및 데이터 현황 설명

- 사용자 요청으로 `/cases`의 중복 선을 줄이고 열 시작점을 맞췄다. 검토실은 수직선/패널 외곽선 대신 간격·면으로 구분하며 완료 실행 로그는 접어 실제 결과가 먼저 보인다. 브라우저 E2E는 접힌 실제 이벤트 열람을 포함하도록 갱신했다.
- typecheck/build/5 tests/diff exit0, fixture 데스크톱/390px 분석·인용·비교 PASS,320px 목록 가로 넘침 없음. 근거 outputs/runs/20261020T160759+0900-case-layout-and-inventory/.
- 원문/정답 출력 없이 집계와 파일 존재/합성 줄 수를 확인했다. 데모2종, 기존 합성360(252/54/54), 공개 수집48,224/격리·서비스 미연결, 준비 후보892 및 최신 수정 검증150 승인0을 구분해 문서화했다. 데이터/검수·학습 gate/backend/실제 모델/8100 운영 배포 변경0. 설명과 제한은 docs/frontend/13-case-layout-data-status.md.

## 2026-10-20 KST — lifecycle schema2와 백업 생성·복구 receipt

- 목표의 이전 turn을 progress로 분류하고 실제 체크리스트/코드/운영 상태를 다시 확인했다. 남은90일/30일 정책 기반 작업을 선택했다. 현재 서비스 상태 집계 sudo -n은 password required/exit1로 실행되지 않았고 권한을 확대하지 않았다.
- 새 소스 schema2: 새 합성 사건의 생성 시각/알려진 출처, 명시적 종료·재개·보류/해제/revision/API·offline CLI. 소유권/CSRF·동시 변경/진행 중 종료·종료 후 분석·증거 변경과 시계 역행 거부. 과거 schema1은 새 rollback 백업·중지 잠금·열 구조·transaction migration 전 쓰기 기동 거부; 날짜/출처 추정0. 원본/복구의 lifecycle metadata purge와 복구 시 잔존 사건 보류도 검증했다.
- 백업 생성 UTC receipt·실제 SHA·출처/포함 사건 SHA와 현재 독립 journal 결합 복구 proof/inventory를 추가했다. 복구 사본의 세션 폐기·대기 작업 실패·내용 보존·보류/원백업 불변을 확인한다. 나중의 사건 보류는 이전 백업에도 전파하고 journal 갱신은 과거 proof를 무효화한다. same-UID 악의적 전체 재작성에 대한 인증 경계라고 주장하지 않는다.
- 실제 CLI13개 합성 흐름과 최신 journal proof/새 inventory/새 schema2 정책 미리보기3개, 총16개 PASS. 최초 helper의 SQLite 백업 파일 SHA=원파일 SHA 가정은 AssertionError/exit1로 보존했다. 별도 실제 진단으로 원본 불변/내용·스키마 동등과 파일 바이트 차이를 확인한 뒤1회 복구했다. 학습 후보 예산과 무관한 검사 가정 수정이다.
- 전체139 tests/compileall/pip check/diff PASS. 앞선138/26/19 tests 기록도 보존했다. 근거 outputs/runs/20261020T161845+0900-retention-lifecycle-10ab30/의 RESULT/CURRENT_STATUS, validation-final, preservation-verification, cli-exercise-retry1, current-journal-proof.
- 실제 UID499 PID41133/ready 읽기 확인, 운영 DB 직접 schema probe는 미실행. 운영 배포/DB/journal/백업/계정/권한/공유 model.lock 변경·재시작·새 실제 모델 제출0. 기존 지연 작업 in-flight 호출은 NOT_MEASURED다. 원본14 SHA/노출556 chain·SHA/현재 native 승인0/학습0/3/활성 수동 정책 SHA를 유지했다. schema2 초안은 새 파일로 추가했고 이전 정책/선택/보고서 보존.
- UI lifecycle 조작부·접근성/새 배포·migration 계획 등 독립 준비를 계속할 수 있다. 실제 UID499 적용·inventory/보존 실행 스케줄러/완전 폐기는 미완료이며 사람 검수·새 정답 OS proof·독립 최종·승인 판례·새 자료 모델/A~F 차단 유지. 전체 목표를 완료/차단으로 표시하지 않고 active로 유지한다.


## 2026-10-20 KST — 공개 NLI450건 사용자 위임 조건과 학습 실행 준비

- 사용자 직접 응답 ‘공개 NLI만 AI 위임 검토 허용’을 질문·정확한450 subject·출처·라이선스·프로토콜과 결합했다. 별도 delegated_ai_review450개를 만들었고 human_reviewed/human_attestation_created=false를 유지했다. 실제 판결문·다른 과제·진단150에 대한 승인 확대0이다.
- 학습300건 문장별 AI 판단, 검증134건의 이전 판단 exact prompt/label/subject 결합 재사용, 변경16건 새 검토. 학습262/검증139 통과, 학습38/검증11 격리, 새 라벨 수정0. 원본·이전 초안·사람 ledger 불변이다. 모델 결과를 보기 전에 새 검증 분모139를 봉인했다.
- 실제 새 열람328건의 개발 노출만 append해556→884. 원556건 prefix SHA/전체 chain 확인. 기록된 로컬 노출만 snapshot으로 묶고 외부·사전학습 노출 UNKNOWN/비공개 최종셋 아님을 명시했다.
- scoped grant/AI 판단 chain/노출 snapshot을 감사·평가 preflight·native 동결/기존 전역3회 ledger에 연결했다. 사람 승인·직접 반려·변경된 subject·범위 밖 과제·진단 자료·라이선스 변경·동결 후 판단 변경을 시험했다. 새 MLX 어댑터의 생성 설정이 로컬 캐시 경로를 쓰고 평가기는 모델ID를 요구하는 불일치를 설치된 mlx_lm/lora.py에서 확인했다. 새 산출물의 생성 설정을 별도 보존하고 같은 동결 모델 ID/revision으로 연결하며 가중치 불변 receipt를 생성하도록 수정했다. 기존 어댑터 수정0이다.
- 실제 `.venv/bin/python -m pytest backend/tests -q` 최종153 passed/exit0(backend-tests-final.json/log). 앞선21개·150개 확인도 보존했다. compileall/pip check/git diff --check exit0은 post-checks.json에 명령·시각과 기록했다. 원본 데이터/어댑터/평가15개 SHA 일치. frontend 소개/PRODUCT를 증거 기반 AI 미제사건 재수사 지원으로 정정하고8123 fixture 로그인 후 실제 메인 문구·1265px 화면 확인/main-purpose.png 저장. 앞선 같은 변경의 frontend typecheck/build/Node5 tests exit0을 유지한다.
- final-packet.json의 새 v2 봉인 패킷/실제 load_packet·데이터 감사 PASS, run_authorized_training.py 기본 비변경 실행 계획 점검 PASS. 실제 새 정답3개 평가자 읽기/해시 확인, 서비스UID probe는 관리자 인증 부재로 probe_executed=false/BLOCKED다. OS 접근 거부로 오인하지 않았다. actual freeze는 예상 exit2/출력0/모델 로드0, 새 학습0/3이다. UID499/PID41133/공유 lock inode25076574 유지, 서비스 중단·재시작·추론 재시도0이다.
- 보존 실패: 구형 외부 감사가 authored_rewrites.json의 출처를 수집 폴더로 가정해 실패했다. 원문/라벨/원본 출처와 패킷 내부 재작성을 구분하는 새 확인으로 처리했다. 초기 실행 계획은 root0600 plist 읽기 거부로 중단됐고 그 뒤 계획 점검도 파일 부재로 실패했다. 기존 v2 패킷/실패를 보존하고 root metadata 결합·실제 인증 터미널에서 SHA만 확인하는 계획으로 해결했다. 권한 확장0이다.
- 사용자에게 로컬 터미널 명령을 전달했다. 인증 후 진행 중 작업 확인/실제 새 정답·변환 파일 접근 거부/동결/기존 daemon 일시 중지/기본 모델 검증/후보c1 한 개 학습/같은 검증 평가/조건 일치 비교/동일 daemon 재개 순서다. 실패 자동 재시도·자동 어댑터 교체0. 실행 결과가 생기기 전 완료로 보고하지 않는다. 세부 제한/명령은 docs/DELEGATED_NLI_REVIEW.md.
- 근거: outputs/runs/20261020T161908+0900-authorized-data-validation/. 원본 보존, 새 실제 사람 승인/유료 호출/실제 판결문 원문 외부 전송/공개 배포0. LOCAL_VALIDATED 유지.


## 2026-10-20 — 사건 lifecycle 화면·배포 후보, 실제 운영 미변경

- run 20261020T164135+0900-lifecycle-ui-9152c8. 종료/재개·보류/해제와 사유·evidence_version/revision, 중복/지연 응답 차단·오류 뒤 초안 보존·저장 불확실 시GET1회/POST 재시도0를 연결했다. 종료 후 분석/증거 공개는 잠그며 기록은 열람한다. API lifecycle GET에 현재 evidence_version을 추가했다.
- 같은 사건 재선택 시 부모 metadata 초기화 후 자식이 재조회되지 않던 문제를 refreshKey로 수정했다. SPA 제목/H1 focus도 갱신했다. fixture1265×720 실제 키보드/보류 지속/두 탭409충돌·사유 유지/재개·기존v1→v2→v3 분석/인용/비교 회귀 PASS. 중간 HMR missing refreshKey 경고는 보존하고 최종 caller/회귀를 확인했다.
- impeccable 국소 확장 절차/별도 마감 검토 P1/P2 수정0. 범위 detector1회 []는 최종 작은 상태·문구 수정 전 관측이며 반복하지 않았다. 정확 당시 시각/SHA 미기록 한계를 detector-observed.json에 기록했다. 최종 backend153/frontend12 tests·typecheck/build/compileall/pip check/diff exit0; 명령/UTC시각/로그는 validation-final. 실제 모바일/확대/VoiceOver/다른 브라우저 NOT_RUN.
- 115개 허용 코드/빌드 파일 후보 archive·파일별SHA·새 안전 전개·모듈 provenance 확인. 기존 venv와 새 합성 DB의 실제 stdio MCP/SSE/종료 후변경409·기록 열람 PASS. 후보 운영 적용0이며 실제 UID499/MLX/개인 인증의 새 배포 검증이 아니다. 운영 동명 파일 drift MATCH14/DIFFERENT12/ABSENT89를 기록하고 관리자 진단·새 백업/migration·원래 잠금·현재 journal·유실 없는 rollback의 DEPLOYMENT_REVIEW 초안을 준비했다.
- 기존15개 SHA·수동 활성 정책/90·30일 비활성·공유 잠금 inode25076574·실제PID41133/UID499 보존. 최신 사용자 공개 NLI 위임 검토의262/139 통과·49격리/노출884와결합SHA를 확인했고 사람 승인 생성0·학습0/3이다. 이전556 기록을 현재값으로 재사용하지 않았다. NLI 관리자 실행은 DELEGATED_NLI_REVIEW 문서를 우선하도록 안내를 정리했다.
- 자체fixture8137/프록시5175/탭7만 정리, 합성DB무결성ok/활성작업0. 실제 서비스/DB/journal·새 모델 요청·자동삭제/스케줄러·백업/키폐기·유료/공개/실제 판결문 외부전송0. 기존 작업 총호출 NOT_MEASURED·지연 원인 미확정. 전체목표 active, LOCAL_VALIDATED 유지.


## 2026-10-20 — 백업별 암호화·사본 복구, 실제 운영 미적용

- 이전 goal turn은 실제 UI/후보 검증을 마친 progress다. 이번 run은 20261020T170913+0900-encrypted-backups-0d84fb. 실제 sudo -n -u _recase_service id -u는 password required/exit1이라 권한을 우회하지 않았다. PID41133/UID499·공유 모델 잠금은 계속 살아 있으며 기존 지연 작업의 전체 호출/원인은 미측정·미확정이다.
- 새 encrypted_backups.py/CLI와 오류/복구 테스트11개. SQLite ro backup→128MiB/15초 한도 메모리 snapshot→백업별 새256-bit 키/96-bit nonce의 AES-GCM, 헤더AAD·별도0700 키 폴더/0600·immutable 새 파일을 구현했다. 생성 중 평문 백업 파일0이다. 설치된 cryptography50.0.2/lock을 재사용하고 app 요구사항에 명시했다. 공식50 API 문서만 조회, 키/실제 자료 외부 전송0.
- 인증 후에만 새 평문 scratch를 만들고 그 사본에만 현재 공급 journal·세션 폐기·대기 작업 실패·잔존 사건 보류를 적용한다. schema1은 새 scratch rollback/migration·과거 분류 미상 유지. 잘못된/없는 키·암호문/헤더 변조는 평문 생성 전에 거부한다. key/journal이 복구 중 변하면 PASS proof 없이 scratch를 보존한다.
- 실제 합성 CLI13개(의도한 exit1거부3개), 새 비활성 v4 정책 호환 CLI1개 PASS. 현재 키/journal·불변 archive/receipt/proof 결합·나중 보류의 과거 백업 전파·stale proof·2035미래90/30일 미리보기 확인. 미래시각은 현재 live 만료 대상이 아니다. 초기9 tests와 최종 전체164 tests(새11)/compileall/pip check/diff exit0. 명령/시각/코드SHA는 validation-final·cli-executions·new-policy-preview-execution에 기록했다.
- 키 부재는 새 테스트 키 이름 변경 후 복원한 가역 시험이며 모든 키/백업을 보존했다. 평문 scratch·기존 평문 백업/sidecar/로그·모든 키 사본·snapshot/swap/메모리·실제 물리/암호학적 폐기는 미검증이다. 같은 UID 전체 침해 방어를 주장하지 않는다. 도구는 backup/verify/inventory만 있고 자동 삭제·키 폐기 실행기/스케줄러0이다.
- 기존15개 SHA·활성 수동 정책/90·30일 비활성·공유 model.lock inode25076574·최신 공개 NLI노출884 chain/SHA·새 사람 승인0·전역 학습0/3 보존. 이전115파일 후보 archive는 보존했으나 새2소스/requirements-app 변경이 없어 적용 전 재생성이 필요하다. 실제 운영/기존백업/모델 요청·유료·공개·실제판결문 외부전송0. 전체 goal active/LOCAL_VALIDATED 유지.


## 2026-10-20 — 이메일·비밀번호 로그인과 인증 구조 정리

- 명시 사용자 요청 범위로 이메일·비밀번호 가입/로그인/로그아웃·계정별 영속 사건 소유권·공통 운영자 role 인증을 구현했다. accounts/auth_api/auth.ts/AuthView/TTY accounts CLI로 책임을 나누고 scrypt·일반 가입 user 고정·세션/CSRF·서버 역할 재확인·시도 제한을 적용했다. 오류 입력이 비밀번호를 반사하지 않는다.
- 기존 접근키 Python/CLI/테스트, 독립 로그인 HTML/CSS/원본CSS/생성기7파일과 활성 Basic/무인증 데모·중복 관리자 인증을 제거했다. 삭제 전 source-before와 파일 SHA 보존. 기존 운영 키/DB/데이터/모델·평가 산출물·실제로 사용하는 Store 합성 운영 fixture는 보존했다. 역사적 문서는 현재 인증 안내를 덧붙이고 당시 검증을 재작성하지 않았다.
- 실제 전체 backend178 tests PASS(09:19:46~09:20:19 UTC), 최종 frontend14/typecheck/build/compileall/pip check/diff exit0. 명령/시각/종료코드는 run/*-verified.json 및 *-delivery.json, 로그에 기록했다. 브라우저는 FixtureModel이며 가입/확인 불일치/잘못된 암호/로그아웃/서버 재시작 후 재로그인 같은 사건·3개 분석 보존/권한 차단·보호 링크 복귀를 확인했다. 실제 공개 증거 v1→v2→v3 분석/인용/비교 E2E PASS. 순수 query 변경 후 로그인 복귀 링크가 남던 결함은 반응형 query와 회귀2 tests로 수정했다. 로그인에서 메인 이동 시 제목 복원도 확인했다.
- 브라우저320/390px의 폼 가로 넘침0·데스크톱 배치 확인/스크린샷 보존. VoiceOver/교차 브라우저/실제 UID499·부하·계정 DB 운영 복구는 NOT_RUN이다. 독립 에이전트 검토는 실행하지 않았다.
- 기존8123 모의 서버의 활성0/대기0/fixture를 읽기 전용 요약으로 확인 후 PID54540만 정상 종료했다. 첫 확인 스크립트는 model.backend를 최상위에서 찾는 오류로 거부됐고 변경0, 진단 기록 후 수정1회로 PASS했다. 최종8123은 새 사건/계정 DB·독립 journal·기본 frontend/dist를 사용한다. 공용 암호/기본 관리자/테스트 계정0이다. 기존 미리보기 DB를 덮어쓰거나 임의 계정에 기록을 자동 이전하지 않았다. 테스트 전용8124는 검증 후 종료한다.
- 기존 데이터/어댑터/평가15개 SHA·원 제공 이미지12개·노출884 SHA/chain·활성 수동 정책·공유 model.lock inode25076574 보존. 실제 UID499 PID41133/worker41754는 변경/중단하지 않았고 추가 MLX 로드/추론/학습0이다. 유료/공개/판결문 외부 전송/운영 삭제0. 계정 DB까지 포함한 운영 이전·암호화 백업/복구·코드 복귀는 별도 통합 검증이며119파일 후보는 현재 인증 배포본이 아니다. LOCAL_VALIDATED 유지.

근거: outputs/runs/20261020T175323+0900-account-login-127a6e/RESULT.txt, backend-verified.json/log, frontend-delivery.json/log, browser-auth-validation.json, browser-case-flow.json, completion-verification.json.


## 2026-10-21 — 최신 계정 통합·현재 계정 보존 복구 검증

- 사용자 '계정 개편 끝났어. 최신 코드 기준으로 통합 검증하고 남은 작업도 순서대로 진행해'에 따라 재개. 이전119파일/174 tests는 개편 전 스냅샷으로 보존하고 누락된 역사적 RESULT 요약만 당시 JSON/log를 근거로 보완했다. 실제 운영/기존 계정·원본에는 쓰지 않았다.
- run 20261021T090314+0900-account-integration-6a7cb0. account_state.py의 bounded 계정 스냅샷/스키마·행·소유권 검사와 Accounts.db 공통 maintenance lock, 링크 거부. 새 account_backup.py/account_backups.py는 사건/계정 이미지를 독립 키로 암호화한 pair와 현재 계정 DB를 유지하는 사건 사본 복구를 제공한다. 현재 비밀번호/credential_version·권한 회수·비활성·소유권 유지, 과거 계정 자동 복원0·암호화 보류/폐기0이다.
- verify_release_database.py는 계정 contract·양쪽 동일 현재 계정 DB·생존 소유권을 요구하고 구 접근키 후보/과거 계정 사본/새 기록 없는 사건 사본을 거부한다. local_soak_check.py는 계정 로그인/CSRF/새 합성 사건/로그아웃·인증 모드 선검사를 지원한다. 실제 부하는 미실행이다.
- 기본178 PASS 후 계정 연동28 tests/전체193 PASS. 마지막 review에서 사건 receipt SHA를 계정 archive의 AEAD AAD에 결합하고 무키 해시를 모두 다시 계산한 교체도 평문 복구 전 거부하는 회귀를 추가했다. 기존 첫 후보/검증 증거는 보존했다.
- 같은 폴더의 practice 모듈/observability/프론트 빌드·명시적 practice 데이터 계약도 갱신돼 v2 묶음과 전환 검사가 PRACTICE_DATA_REQUIRED로 거부됐다. source 편집을 덮지 않고 v2 archive/부분 stage/로그를 보존했다. v3에 정확히 공개 AI 합성 입력 data/practice/v1/cases.json만 포함하고 검수 참고 정답·학습/평가 자료를 제외했다. 실제 practice endpoint도 확인했으며 이 자료는 사람 검수/독립 최종/학습 자료가 아니다.
- 최종 backend195 passed/44.63s·frontend14 tests/typecheck/build/compileall·pip check/diff PASS. 전체 pytest2번째는 archive AEAD binding 및 practice 경계 변경에 따른 재검증이며 원인 없는 반복이 아니다. 명령/UTC시각/종료코드는 backend-final-v2.json, other-validation-v3.json과 최초 other-validation.json/pip-check.log를 따른다.
- 최종123파일 후보 SHA b6532556effb35513a9decd61b4a57fa272a69e8ef4c2229a96bc0c6ea198c47/5,474,853bytes, readonly0400/0500, candidate-v3-manifest.json. 후보-only TestClient/FixtureModel·실제 stdio MCP/HTTP/SSE·v1/v2·타인 사건/작업/SSE 거부·복구 후 현재 자격정보·삭제 이력/결과/종료/보류·프로세스 재시작/새 기록 보존13항목 PASS. CLI6개 중 의도한 구 접근키·오래된 사건 사본 거부2개 포함. rehearsal-v3의 명령/시각/exit code/결과를 따른다. 실제 UID499 복귀 후보 지정/과거 버전으로 실제 코드 복귀는 미실행이다.
- 기존 공개 NLI 실행기의 비변경 계획 점검 PLAN_CHECK_PASS, 관리자 명령/모델 로드/학습0. 기존15 SHA·노출884 chain/SHA·수동 정책·실제 UID499/PID41133/41754·model.lock inode25076574/점유와 운영 공개 코드 보존. 실제 sudo-n probe는 password required/exit1·운영 DB 읽기0이며 지연/취소 최종 상태·원인/총 호출은 미확정/NOT_MEASURED다.
- 최종보존 proof는 preservation-verification-final.json. v1/v2를 포함해 새 run의 report/log에서 백업 키 원문/hex/base64 노출0, 후보 트리 외 파일0600/디렉터리0700, v2 부분 트리도 read-only로 봉인하고 실패 상태는 유지했다. 새 평문 사본/키/암호문을 임의 삭제하지 않았다.
- docs/ACCOUNT_RECOVERY.md·상태/체크리스트/인계/USER_NEXT_STEPS.txt에 실제 관리자 읽기 전용 명령·기존 사건 소유권 사람 확인·실제 판례 목적별 권리/비식별 검수·독립 최종셋·계정 DB 소실/자격정보 재발급 복구·폐기 정책의 남은 순서를 기록했다. 실제 UID499 배포/모델·새 학습0/3/자동 삭제/키 폐기/유료/공개/원문 전송/사람 승인 생성0. 전체 목표 미완료·LOCAL_VALIDATED 유지.


## 2026-10-21 — 미제사건 대응 설명과 사용자 테스트 자료 준비

- 사용자 요청으로 현재 가능한 자료 대조/불충분/충돌/검색·형식 실패/반대 증거 수정의 차이, 누락 정보·다음 확인·재검토 조건을 설명했다. NIJ/NIST 공식 일반 문헌만 검색했고 실제 사건 원문·개인정보를 반입/전송하지 않았다. 현재 그래프의 장소/날짜·신원 전제/주장당2자료·검색5건·빈 가설 목록과 고급 추론 미지원도 명시했다.
- 새로운 가상12사건/48증거/36단계 입력과 AI 제안 기준을 분리 작성했다. P01~03만 현재 그래프에 연결, 나머지9개/27단계는 수동 검토용이다. 시간 오차·동명이인·감정 충돌·정정·기록 부재·출처 중복·물품 동일성·문서 지시문·승인 철회를 포함한다. 실제 범인/해결 정답을 만들지 않았으며 모든 사건 상태는 UNRESOLVED다. 사람 검수/학습 적격/독립 최종셋으로 표시하지 않았다.
- practice.py/계정·CSRF POST /api/practice와 UI ‘테스트 사건3개 추가’. 결정적 소유자별 ID로 재호출 중복·기존 증거/분석 초기화를 막고 새 자료는 기존 공개 경계 뒤에 둔다. 입력 원문만 service에 읽히며 reviewer 제안은 모델/브라우저 API에 넣지 않았다. release에는 이 모듈과 입력 JSON을 함께 요구하고 제안 기준 경로는 거부한다. 원래 graph/testing/model은 수정하지 않았다. SPA가 사건 제목을 일반 제목으로 덮던 별도 결함도 제한적으로 수정하고 실제 최종 빌드에서 확인했다.
- 68개 파일의 최종 ZIP을 새 경로 RECASE-test-kit.zip에 만들었다. 사건별12·증거별48파일/36개 snapshot/검토 참고표/빈 결과지·해시/노출 기록을 포함한다. snapshot은 공개된 증거만, 템플릿36단계는 전부 NOT_RUN, 수동 모델 평가27단계는 NOT_RUN이다. 기존 NLI 노출 ledger는 변경하지 않았다. 초안 요약의 조사 오류를 수정한 뒤 최종 입력 SHA를 다시 봉인하고 초안 ZIP은 보존했다.
- 첫 테스트 collection은 tests.account_helpers import를 잘못 적어 exit2로 실패, 실제 서비스/모델 변경0 후1회 수정했다. 다음 기능검사는 P03 v1의 정상 RETRIEVAL_INSUFFICIENT/PARTIAL을 전부 COMPLETED로 가정해 실패했다. 진단 후 P03 v1/v2만 PARTIAL+해당 limitation을 엄격 확인하도록 수정했다. 제안 관계 라벨/증거/모델을 통과 결과에 맞춰 바꾸지 않았다. 실패 로그/진단과 새 명령·시각·exit을 보존했다.
- 최종 전체 backend194 tests PASS(40.36초), frontend14·typecheck/build/compileall/pip check exit0. 고정 fixture9단계는 COMPLETED7/PARTIAL2 포함으로 검증하며 모델 정확도라고 계산하지 않는다. 실제 IAB P01 3단계/공개 경계/인용·변경·유지 비교·P03 부분 완료·반복 seed/재시작 후 이력,320/390px 넘침0·데스크톱 QA PASS. 독립 에이전트 검토는 사이드 대화 제한으로 실행하지 않고 같은 에이전트가 직접 검토했다. VoiceOver/다른 브라우저/실제MLX는 NOT_RUN이다.
- 기존8123 UID501 fixture PID57830·활성0 확인 후 해당 미리보기만 정상 재기동, 같은 사건/계정 DB 관계형 내용 SHA 동일/기본 계정 생성0. 원래 UID499 PID41133/worker41754·공유 model.lock inode25076574/점유·원본15개/이미지12개/노출884 chain·SHA 보존을 확인했다. 실제 서비스·MLX 호출/학습/사람 승인·운영 삭제·유료/공개/실제 원문 전송0이다. 이전 계정 통합 배포 후보는 당시 근거로 보존하며 이번 데이터 의존성 재포함·실제 UID499 검증은 별도다. LOCAL_VALIDATED 유지.

근거: outputs/runs/20261021T090257+0900-user-test-kit-47fdda/RESULT.txt, *-delivery.json/log, kit-export.json, final-input-freeze.json, browser-practice-flow.json, browser-practice-review.json, browser-delivery-build.json, completion-verification.json.


## 2026-10-21 — 계정 DB 소실 시 격리 복구, 일반 추론 미구현 상태 확인

- 이전 goal turn은 계정 통합195 tests/123파일 후보·실제 CLI/MCP 사본 검증으로 progress다. 새 run 20261021T091557+0900-account-recovery-110ad4에서 관리 인증 없이 진행 가능한 계정 DB 소실 복구를 구현했다. 기존 운영/소유권/데이터를 자동 승인하지 않았다.
- identity_recovery.py/recover_accounts.py: 새 사본에 ID/이메일/이름/생성 시각만 보존, 전 계정 disabled/user/새 임의 verifier·schema9001 격리→실제 로컬 TTY의 소유권/정확 ID/확인 근거·새 비밀번호/확인→미확인 계정 보류 유지 확인 후 별도 seal. 옛 암호 해시/운영자 역할·활성 상태 복원0, 기존 파일 덮어쓰기0, 실제 서비스 게시0이다. 현재 계정 DB가 있으면 기존 보존 복구를 사용하며 이 경로로 바꾸지 않는다.
- intent fsync→DB 변경→완료 ledger. 미완료 intent/외부 변경/교체 DB/다른 ID/보류 집합 차이는 운영자 audit 없이 재시도하지 않는다. 계정1개 활성화 후에도 웹에서 거부되며 최종 seal 이후만 schema1이 된다. 운영자0·미확인 계정 disabled 유지. 기존 Accounts 핸들도 DB schema/inode 교체를 검사한다. 사용자 실제 소유권 판단을 소프트웨어가 대신하지 않는다.
- WAL/DELETE의 메모리 serialize/deserialize 실험(snapshot-format-diagnostic.json): WAL image2/2는 unable to open database file, PRAGMA journal_mode 변경도 memory만 반환하고 원 image는 유지됐다. 헤더를 수정하지 않고 검증된 known rows를 새 메모리SQLite에 생성/삽입/commit해 이식 가능한 계정 이미지를 암호화한다. 새 source WAL/DELETE 복구 모두 PASS. 옛 WAL image는 평문 기록/헤더 패치 없이 거부한다.
- 관련27 tests PASS, 전체203 PASS 보존. 기존 Accounts 핸들의 격리/파일 교체 거부 회귀 후 최종204 passed/49.63s. 최종 CLI의 --user-id 선택/이메일 조회는 실제 합성 PTY에서 정확 ID 직접 입력으로 검증했다. CLI/PTY11항목/6명령 PASS를 최초 후보와 최종 v2 사본에서 확인했고 source compileall/pip/diff PASS다. 프론트 수정/재검증0, 이전14 tests/typecheck/build의 frontend 바이트는 모두 일치했다.
- 최종125파일·5,478,937bytes archive SHA b3cc1954233186c185ee6b9fe05a6670d786af6cdb4a41779b17c9841c58ffa3, candidate-v2/0400·0500. 단위 테스트와 CLI는 합성 소유권의 UNIT_TEST_FIXTURE 입력이며 실제 사람/운영 계정 소유권 승인0이다. FixtureModel/TestClient·실제 stdio MCP로 봉인/새 암호 로그인/소유 사건과 결과 보존·과거 쿠키/암호·옛 admin 로그인 거부/일반 계정 운영 API403 확인. 원 합성 계정 파일도 삭제 대신 이름 변경으로 보존했다.
- 원본15 SHA·수동 정책·노출884 chain/SHA·학습0/3·UID499 PID41133/41754/공유잠금 inode25076574 점유 보존. 새 sudo-n probe는 password required/exit1, 운영 DB 직접 읽기/수정0·추가 MLX 요청/학습·유료/공개/원문 외부전송/자동 삭제/키 폐기0. 키/평문/ledger 보관·완전 폐기·실제 UID499/정답 OS/부하/복귀 후보/독립 데이터 gate는 남는다.
- 사용자 질문 '복잡한 상황의 일반 추론 ... 구현했어?'에 현재 graph.py/CASE_REVIEW 문서를 대조해 아직 아니라고 답했다.4주장/검색5/최대2자료·동일 장소/날짜 방문 대조·hypotheses=[]를 확인했고 ISSUES SCOPE-001의 오해 소지가 있던 IMPLEMENTED를 PARTIAL/일반 추론 NOT_IMPLEMENTED로 정정했다. P04~P12 자동 지원/통과를 주장하지 않았다. 다음 구현 우선순위를 다중 증거·시간 구간·동일인/불확실성·검사 충돌·문서 정정/전언 계보·가설/다음 확인 제안으로 명시했다. 계정 복구 검증을 일반 추론/실제 모델 성능으로 계산하지 않는다.
- docs/ACCOUNT_RECOVERY는 현재 실제 명령/범위로 갱신, 상태/체크리스트/인계/RESULT/CURRENT_STATUS/각 명령·시각·exit code·SHA를 보존했다. 전체 목표 미완료/LOCAL_VALIDATED 유지.


## 2026-10-21 다중 증거 일반 검토 — 20261021T092903+0900-general-reasoning-18336d

2026-10-21 다중 증거 검토 경로 `evidence-reasoning-v1`을 구현했다. 직접 작성한 가상 주장/자료와 별도 명시 추가한 연습12개를 새 경로로 분석한다. 공개 자료 전체를 입력하고 관측·충돌·전제·미검증 가설·사람의 다음 확인/조건부 시간 계산을 반환하며 원문 ID/연속 인용/Unicode 구간을 검사한다. 최대8주장/24자료/원문24,000자/8호출/180초, 모델 문맥4,096/출력1,024토큰·형식 정리1회/모델 재시도0이다. 한도·무효 출력은 주장별 PARTIAL로 남기고 모델 실행 실패 후 후속 호출을 중단한다. 기존 제한된 방문 대조와 저장 이력은 별도 유지한다.

전체 backend243 tests, 최종 일반 경로11 tests, frontend16/typecheck/build PASS. 실제 IAB의 임의2주장/공개2자료+숨긴정정1/저장/인용/추가공개/재분석/비교/재로딩 보존·연습12개 명시 추가·320/390px 넘침0을 확인했다. 원문 인용/형식 검사는 의미 정확도의 증명이 아니다. 고정 FixtureModel은 INSUFFICIENT 모의 응답이며 실제 MLX의 복잡한 추론 정확도·독립 최종/A~F·36단계 실모델 평가는 NOT_RUN이다. 실제 UID499/8100 배포·새 모델 요청·학습0/3·사람 승인·폐기0, LOCAL_VALIDATED 유지다. 기존 소스 해시에 결합된 NLI 실행 계획은 model.py 변경으로 무효화됐으며 재준비 전 옛 실행 명령을 사용하지 않는다.

[구현·사용법](GENERAL_REASONING.md), [결과](../outputs/runs/20261021T092903+0900-general-reasoning-18336d/RESULT.txt).
화면 마무리 검토의2개 P2(실패 상태의 완료 문구/긴 원문 구간 이동)를 수정했다. 인용 mark의 중앙 이동·실제 포커스와320/390px 원문/입력 폼을 확인했다. detector 단1회[]; reviewer 별도 읽기 전용 검토, 새 세계/리디자인 없음.132파일 후보 SHA는517c7332ef57ff6b1566b0a5ad0af376b773fe7aca4393ff9b3a235dc5432ebd이며 코드/빌드 스냅샷일 뿐 배포 승인이 아니다. 최초 브라우저 서버의 전역 Python/mcp 누락 종료와 비변경 로그를 보존하고 venv 실행으로 별도 fixture를 기동했다. 원본15 SHA/노출884 SHA/공유 lock inode25076574 보존.


## 2026-10-21 공개 사건 자료 별도 수집·전처리

사용자 요청으로 프로젝트 밖 /Users/beshu/RECASE_data_vault에 공식 공개 공고/문서1469개(FBI1266·SafetyDream10·경과7·DOJ페이지128·PDF58/748쪽)를 격리 보관했다. 영어 중심, 정확 중복 사본3개 보류·유사48쌍·텍스트가 적은13쪽 검수 대기. 상세 docs/PUBLIC_CASE_CORPUS.md, outputs/runs/20261021T092855+0900-public-case-collection-438022/RESULT.txt. 원문/중간 결과 보존, backend244 tests 및 최종 후속29 tests·데이터무결성9검사 PASS. 모델 평가/학습 NOT_RUN·실제 정확도 NOT_MEASURED·사람 승인0·서비스 반입0. 신규 목적/개인정보/라벨/계열/당시 입력·OS·동결/모델잠금 gate는 남아 있다. 기존15개/노출884/실제UID499·잠금 보존.


## 2026-10-21 모델 작업 준비·실제 CANTOPEN 진단 — 20261021T095154+0900-model-readiness-9fa3f2

현재 실제 UID499 PID41133/41754와 공유 model.lock inode25076574 점유를 확인했다. 사용자의 /usr/bin/sqlite3 -readonly 실행은 CANTOPEN14로 실패해 실제 작업/취소 상태는 UNKNOWN이다. DB 손상/파일 누락/활성 작업0을 추정하지 않는다. 현재 세션 sudo-n은 암호 필요/exit1이며 원 DB·권한·서비스를 변경하지 않았다. 뒤이은 Python 진단 안내의 두 줄이 cd 한 줄로 합쳐진 시도는 진단 미실행이다.

새 diagnose_local_service.py는 root에서 고정 plist/라벨/PID/UID를 확인한 뒤 실제 UID499로 내려가 상태 폴더/DB/WAL/SHM metadata와 readonly jobs 집계만 반환한다. 파일 생성/복구/chmod·서비스 재시작/모델 호출·원문/키/개별 사건ID 출력은 없다. immutable SQLite를 쓰지 않아 live WAL의 대기 작업을 숨기지 않는다. SQLite의 정상 WAL reader coordination 가능성은 별도 명시했다. 합성 누락/손상/심볼릭 링크·live WAL·비관리자/다른 PID 차단6 tests와 모델 생성 API 계약7 tests를 추가했고 전체257 tests/compileall/pip check/diff PASS다. 실제 root 진단 결과는 아직 대기다.

기존 공개 NLI 학습262/검증139의401개 입력에 대해 실제 캐시 tokenizer로 변경 전후 formatted prompt bytes 동일·최대245 입력토큰을 확인했다. 기존 NLI 출력 한도128/greedy/seed0/thinking off는 그대로다. CPU 토크나이저 검사이며 가중치 로드/추론/새 의미 검토0이다. 원본 데이터/정답/검토 subject/사람 이력/450개 AI 결정과 격리49를 유지한 새 protected volume v3 패킷을 봉인하고 실제 load_packet/audit_native_nli PASS를 확인했다. 새 grant/AI chain은 이전 승인/판단 해시를 계승한 소스 재결합이며 사람 승인이나 새 데이터 결정이 아니다.

preparation-plan.json은 execution_ready=false/executable=null인 준비본이다. 기존 실행기의 소스 변경 거부(exit1)를 실제 확인했으며 옛 명령을 재사용하지 않는다. 현재 CANTOPEN/작업 상태 진단·새 실제 정답 접근 거부·중지/재개 검토 전 실행기를 제공하지 않는다. 새 학습0/3·독립 최종/실제 일반 추론 품질/A~F NOT_RUN, 새 실사건 코퍼스 격리/미사용·사람 승인 생성0·운영/유료/공개/원문 외부 전송/삭제0이다.

근거: MODEL_READINESS, tokenizer-compatibility/final-packet/fresh-data-audit/preparation-plan/backend-final/preparation-commands/preservation-verification. 이전 goal turn은 일반 검토 구현·fixture/UI 증거로 PROGRESS였고 이번 turn도 신규 진단 소스/검증/보호 볼륨 새 패킷을 생성해 PROGRESS다. 인간 입력/실제 OS/모델이 남아 목표는 active다.


## 2026-10-21 Git 원격·게시 준비

사용자 지정 공개 저장소 origin=https://github.com/beshurl/skala-ai-mini-project.git, 브랜치 back/feature/recase-auth-evidence-data-pipeline. 기존 codex 이름 로컬 브랜치1개를 이름 변경하고 기존 커밋 이력을 보존했다. .gitignore에서 실제 수집 원문·모델·계정/사건DB·비밀정보·실행 산출물을 제외하고 정적 예시/운영명세/합성 연습자료와 화면 자산만 포함한다. 별도 Git 소스 사본에서 backend257 tests·추가 평가7 tests/frontend16·typecheck/build PASS, 과거 이력/소스 비밀값 검사0건. 새 클론에서 로컬 data/processed에 의존하던 테스트 실패는 보존했으며 임시 합성 자료 생성으로 수정했다. 캐시 없는 토크나이저 검사는 명시 skip하며 모델 자동 다운로드/추론0이다. 푸시 최종 결과/정확한 명령·시각·종료코드는 outputs/runs/20261021T100053+0900-github-publish-fee619/에 로컬 기록한다. 실제 수집 원문·기존 어댑터·평가·운영서비스·모델 잠금은 변경하지 않는다.

## 2026-10-21 main 통합·추가 변경 검증 및 SafetyDream 연결

사용자의 전체 변경 게시·병합 요청으로 기존 게시본 bcb1924를 main 기본 소스로 올리고, 이후 평가 실행 환경 식별/감독 시간 제한·로컬 실행 세션/복구 시뮬레이션 등 미추적 소스를 포함해 새 사본에서 검증했다. outputs/runs/20261021T101256+0900-main-merge-45ba96의 backend-tests.json/log: 10:15:25~10:16:39 KST, .venv/bin/python -m pytest -q backend/tests, exit0/271 PASS. frontend-checks.json/log: 10:15:40~10:15:45 KST, npm ci --offline --ignore-scripts --no-audit --no-fund 및 test/typecheck/build 모두 exit0, 16 tests PASS. 명령의 cwd는 run/source이며 실제 프론트 빌드/운영 서비스/모델은 변경하지 않았다. 비밀값 검사 이력/소스0건. 병합·원격 SHA·작업 폴더 최종 상태는 같은 run에 별도 기록한다. Git clean을 위해 실제 자료를 삭제하거나 소스 제외 규칙을 추가하지 않는다.

사용자 제공 SafetyDream 키는 프로젝트 밖 개인 저장소의 새0600 파일에 보관했다. 공식 HTTPS POST 최소 조회1회에 HTTP200/result00·반환1건·totalCount321을 확인했다. 원문/개인정보 저장0·키 출력/URL 노출0·전체 인증 수집/전처리/학습 NOT_RUN. 연결 결과는 개인 저장소 connection_checks/에 보관하며 키를 Git에 넣지 않는다. 모델 실행 세션 도구는 소스/시뮬레이션만 검증했으며 실제 sudo·서비스 중지/재개·학습/모델 요청은 실행하지 않았다.

게시 직전 병행 추가된 FAILED/CANCELLED/STALE 작업의 후속 모델 중단 조건과 복구 테스트를 포함했다. backend-reasoning-final.json/log: 10:18:30~10:18:35 KST, pytest -q backend/tests/test_reasoning_session.py backend/tests/test_reasoning_evaluation.py, exit0/15 PASS. 전체271 PASS 이후 변경한 두 소스에 대한 후속 검증이다.


## 2026-10-21 사건별 대화 구현 — 20261021T102531+0900-case-conversation-b79dc2

사용자의 대화형 기능 추가 요청으로 back/feature/recase-case-conversation의 별도 worktree에 구현했다. 원본의 고정 모델 평가 계획과 병행 문서/운영 소스를 보존한다. 기존 jobs·단일 Worker/MCP/모델을 사용해 사건별 질문/답변·최근3개 맥락·정확 원문 인용·현재/과거 증거 버전·20개 cursor를 연결했다. 요청 ID 재확인으로 새 모델 중복 호출을 방지하고 네트워크 오류 시 초안 보존·늦은 다른 화면 응답 거부·취소를 추가했다. 실제 모델/학습/서비스 중지·배포/키 출력/외부 전송0이다.

backend-tests.json/log: 10:33:29~10:34:50 KST, 기존 venv/python -m pytest -q backend/tests, exit0/285 PASS(새13개). frontend-final-checks.json: 10:36:21~10:36:23 KST, npm --prefix frontend test/typecheck/build 모두 exit0/22 tests PASS(새6개). 후속 문구 수정의 frontend-copy-final.json:10:39:12~10:39:14 타입/빌드 exit0. 실행 cwd는 run/source이고 원본 frontend/dist·실제 UID499·원래 model.lock을 바꾸지 않았다. 실모델 성능 NOT_RUN/NOT_MEASURED다.

실제 브라우저의 모의 계정에서 질문3개·후속/Enter·정확 인용 원문 포커스·v1→v2/이전 버전 표시·재로그인 후 보존을 확인했다. 최초 재로딩이 로그인으로 이동한 이력은 남겼으며 미리보기만의 쿠키 이름과 새 DB/journal로 분리했다. 모바일/마감 검토·비밀값/원본 보존 검사·최종 Git 결과는 같은 run에 기록한다. 자동 작업 폴더 도구가 다른 저장소의 pristine checkout을 생성해 그 사본만 정리한 뒤 올바른 프로젝트의 worktree로 교정했다. 최초 프론트 작성 경로 오류는 파일 변경0으로 보존하고 올바른 경로에서 실제 작성/검증했다.


## 2026-10-21 사건 대화·프론트 QA 게시 통합 — 20261021T132444+0900-ui-conversation-integration-5a2925

사용자 커밋·푸시·병합/백엔드 수정 요청으로 기존 사건 대화 브랜치 b37ae8e와 화면 QA를 별도 소스 사본에서 통합했다. 미검수 출처의 새 대화를 서버에서 거부하고, 공통 버튼 디자인·분석 이력 링크/로그인 복귀·사건 목록 우선순위와 모바일 긴 내용 표시를 보완했다. 메인의 최신 스크롤·읽기 전용 UI를 보존하며 메인 작성 중인 별도 backend/검수 소스는 게시하지 않는다.

게시 사본 backend286/frontend24·npm offline ci/typecheck/build PASS, 메인 동시 소스 통합 사본 backend379·후속 승인/API 관련35 PASS. 브라우저 모의 질문3·후속/인용/v1-v2/기존 분석/재로딩·320/390/1280px PASS·console0이다. source-only 검증이며 실제 MLX 대화 품질 NOT_MEASURED·학습/UID499 운영배포0·8100 제어/공유잠금 변경0이다. 상세 범위는 docs/FRONTEND_QA.md·CASE_CONVERSATION.md, 실제 Git SHA/명령·비밀값 검사 결과는 고유 run에 기록한다. 기존 평가/학습 계획은 소스 해시가 다르면 재사용하지 않는다.


## 2026-10-21 TXT·MD·JSON 사건 파일 초안 불러오기 — 20261021T140757+0900-case-file-import-2c58e5

사용자가 사건 파일 업로드를 요청하고 ‘너가 만들어 줄거긴한데 txt md json을 줄거야’라고 형식을 확정했다. 기존 합성 작성 폼에 로컬 파일 선택/원문 미리보기/묶음 사건 선택/명시 적용·이전 입력 복원/수동 확인 후 저장을 연결했다. 파일 선택은 네트워크·모델 호출을 하지 않으며 저장은 기존 인증/CSRF API만 사용한다. 파일당256KiB/문자·요청64KiB 한도·UTF-8/엄격 schema·승인 필드/정답 참고표 거부를 적용했고 세 합성 예시를 제공한다. 실제 자료 승인/검수를 생성하지 않는다.

frontend34 tests·타입/새 빌드 PASS. 실제 파서→새 합성 API의3형식+연습12건=15 저장·비공개1건 제외/모의 질문·CSRF403/타인404 PASS. IAB 실제 파일 chooser/JSON·TXT·MD/잘못된JSON/12건 선택·입력 보존/복원·저장·320/390/768/1280px 넘침0 확인. 기존8132 fixture 서버만 active0/본인 PID·명령 확인 후 같은 합성 DB/쿠키로 교체했고 실제8100 제어/모델·학습0이다. backend 제품 소스/보호 검수 도구·봉인과 메인 진행 변경은 보존한다. 상세 사용법은 docs/CASE_FILE_IMPORT.md, 명령/시각·Git/검사 결과는 고유 run에 기록한다.
