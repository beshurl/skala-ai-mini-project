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
