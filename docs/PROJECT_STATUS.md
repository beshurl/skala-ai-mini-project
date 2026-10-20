# 현재 상태

2026-10-20 KST. **LOCAL_VALIDATED: 합성 사건의 제한된 로컬 분석 흐름.** 전체 서비스 개발 목표는 미완료이며 PILOT_READY/PRODUCTION_READY로 승격하지 않는다.

## 완료한 현재 범위

- 원본27개를 백업/해시 보존. 데이터·기존 평가·어댑터14개는 그대로다. 참고 학생 프로젝트는 읽기만 했으며 코드 복제/변경 없음.
- 추가 사용자 기록으로 과거 Base/FT 모두4B 명시,100회 학습 완료, 검증 loss3.108→표시0.000 확인. 과거 exact revision/원시 loss는 여전히 UNVERIFIED. 재설치/학습 명령은 재실행하지 않았다.
- 현재4B snapshot을 고정해 Base/기존 FT 각각54건 실제 평가. 기존 어댑터56개 LoRA 모듈/실제 Metal 추론 확인. 출력 계약 성공률 Base0%, FT100%는 노출된3템플릿 데이터의 결과다.
- FastAPI/Vue3 사건·공개 증거·권한 있는 공개·영속 job/SSE·취소/부분 완료/실패·근거 원문·버전 비교. actual MCP stdio + keyword 검색 + bounded LangGraph + singleton MLX.
- clean locked venv에서41개 자동 테스트/compileall/pip check/비교 PASS, 실제 Metal 추론 PASS. frontend npm ci/build PASS.
- 실제 MLX 브라우저304/1265px에서 v1판단 보류→v2충돌→무관 증거v3판단 유지 PASS. 오류/취소/부분 완료는 명시적 fixture 서버에서 별도 PASS.
- 실제 DB backup/새 복구본/무결성/SQL digest 일치, 모델 중복 프로세스 거부 확인.

## 단계별 상태

| 단계 | 상태 | 범위/차단 |
|---|---|---|
| 0 감사 | PASS | 과거 부족한 메타데이터는 구분 |
| 1 명세/계약 | PASS 로컬 범위 | 라벨·시간/식별 규칙·JSON Schema |
| 2 평가기 | PASS | 누락/무효/인용/비교 조건 검증 |
| 3 반입/정제 | IMPLEMENTED + BLOCKED | 로컬 synthetic fixture 검증; 실제 자료/승인/사람 검수 없음 |
| 4 데이터/분할 | FAIL | 정확 프롬프트 중복10/9/6,3템플릿 반복, 독립 최종셋 없음 |
| 5 Base 검증 | PASS | 동일4B 개발54건 |
| 6 학습/모델 선택 | 기존 재사용 + BLOCKED | 기존100회 로그/어댑터 확인. 새 학습0회. 독립 검증셋 선택 보류 |
| 7 서빙 | PASS 로컬 | 한 모델/큐/취소/timeout, 공개 운영 부하는 미검증 |
| 8 검색 | IMPLEMENTED | 현재 사건 keyword 경로 검증. 참고 판례·Recall/MRR BLOCKED/NOT_MEASURED |
| 9 MCP | PASS | 실제 stdio/권한 도구 호출 |
| 10 그래프 | PASS 로컬 | 최대4호출/180초/루프0, 검증/버전 일관성 |
| 11 앱 | PASS 로컬 | 실제 브라우저 전체 흐름 |
| 12 회귀 | PASS 범위 제한 | 자동41개 + 실제 모델/fixture 브라우저 별도. 광범위 보안 보증 아님 |
| 13 최종 비교 | BLOCKED | 개발 A/B만 실행, 독립 최종 평가/전체 A~F는 미실행 |
| 14 운영 | LOCAL_VALIDATED | clean install/복구 확인; OS 정답 격리·운영 인증·부하·삭제 정책·공개 배포 미완료 |

## 실행 상태와 다음 작업

로컬 서버는127.0.0.1:8100, 실제 MLX/기존 어댑터로 실행한다. 사용자는 브라우저에서 새 합성 데모를 시작할 수 있다. 재기동은 `make serve`, 검증은 `make check`. 모델 평가/학습 전 서버를 중단해야 한다.

다음 우선순위는 검수된 독립 사건/시나리오·문서 계열 데이터와 목적별 승인/사람 검수, OS 수준 평가 정답 격리다. 이를 확보하기 전 새 학습/실제 판례 RAG/최종 성능/공개 운영 승격을 진행하지 않는다. 유료 호출·공개 배포·원문 외부 전송0건.

세부 명령/증거/제약은 EXECUTION_CHECKLIST, EVALUATION_REPORT, ISSUES, HANDOFF를 참조한다.
