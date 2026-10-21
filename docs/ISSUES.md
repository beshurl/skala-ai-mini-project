# 미해결 문제와 상태

| ID | 상태/우선순위 | 문제·근거 | 다음 작업 |
|---|---|---|---|
| AUTH-INTEGRATION-001 | SOURCE_FIXTURE_VALIDATED/P1 | 2026-10-21 계정 개편 후 backend195/frontend14·123파일 후보의 실제 stdio MCP/합성 계정·사건 pair/현재 비밀번호·권한·비활성·소유권/재시작 PASS. 구 접근키 코드·계정 과거 사본·새 기록 없는 사건 사본 전환 거부 | ACCOUNT_RECOVERY 참조. 실제 UID499·기존 소유권 연결/계정 DB 소실 복구·복귀 후보/관리자·모델·OS·부하·폐기 정책은 미완료. 계정 이미지는 암호화 보류/자동 복원0 |
| DB-001 | RESOLVED_SOURCE_NOT_DEPLOYED/P1 | 새 전환 시험에서 GC 뒤 DB SHA 변화1건. backup/migration/retention의 미종료 SQLite 연결·지연 checkpoint 재현 후 closing() 수정, 강제GC 뒤 본체 SHA 유지/연결0·전체174 tests PASS | run 20261020T173502+0900-release-transition-bcc984. 실제 UID499 적용은 별도. 이전 실제 MLX 지연 원인으로 연결하지 않음 |
| BACKUP-001 | SOURCE_FIXTURE_VALIDATED/P1 | 백업별 새 AES-256-GCM 키/nonce·메모리 snapshot·키 폴더 분리·인증 후 사본 복구와 현재 키/journal 결합. 합성 CLI13개·전체164 tests PASS | ENCRYPTED_BACKUPS 참조. 실제 UID499·기존 평문 백업 전환·sidecar/로그/키 사본·APFS/swap·물리/암호학적 완전 폐기 미검증. 키/백업 폐기0 |
| DATA-001 | FAIL/P0 모델 승격 차단 | 기존 분할 간 정확 프롬프트 중복10/9/6, 정규화3템플릿 반복 | 사건/문서/시나리오 계열 메타데이터와 검수된 새 독립셋을 확보해 분할. 원본은 보존 |
| DATA-002 | PARTIAL/P0 | 공개 수집48,224건 격리. 사용자 공개 NLI450건 AI 위임 검토 통과 학습262/검증139·49격리, 노출884. 실제 사람 승인으로 기록하지 않음 | DELEGATED_NLI_REVIEW의 현재 범위·실행 전 OS 인증을 따른다. 독립 최종/진단/실제 판결문 승인으로 확대하지 않음 |
| EVAL-001 | BLOCKED/P0 | 최종 블라인드 평가셋 없음. 개발54건 결과로 실제 신뢰도 주장 불가 | 독립 시나리오와 사람 검수로 고정 최종셋 준비; 개발 노출 이력 관리 |
| SECURITY-001 | PASS 검사 경로/시점 한정 | UID499 서비스/UID501 평가자, 실제 보호 정답7개와 작업 폴더 정답/키4경로 거부. 14:43 root 결과 | 새 평가/학습 전 현재 UID·실제 경로/해시·접근 거부 재확인. 다른 사본/관리자 차단까지 일반화하지 않음 |
| SCOPE-001 | PARTIAL / WORKFLOW_IMPLEMENTED / P1 | evidence-reasoning-v1의 임의 가상 입력·다중 공개 자료·충돌/가설/다음 확인/정확 인용·오류 보류 경로와 fixture/UI 검증 완료 | GENERAL_REASONING 참조. 실제 MLX 복잡한 관계/인용 의미 정확도·독립 최종·36단계 평가 NOT_RUN. 실제 UID499 미배포 |
| OPS-001 | PARTIAL/P1 | Mac 로컬 전용. 개인 접근키·쿠키·UID499 실제 MLX 제한 부하 PASS. 지속 부하 미측정 | 공개 운영으로 일반화하지 않음; 사람 검수·운영 정책 전 파일럿 차단 |
| OPS-003 | OPEN/P1 | 실제 UID499 지연/취소 상태 미확정. 사용자 mac sqlite readonly 집계가 CANTOPEN14로 실패해 작업 상태 UNKNOWN. 새 진단 도구6 tests/전체257 PASS지만 실제 root 결과 대기 | MODEL_READINESS의 한 줄 명령으로 실제 UID499 metadata/WAL/집계부터 확인. DB 손상·작업0 추정/권한 확대·원인 없는 재시작 금지 |
| OPS-002 | PARTIAL/P1 | 실제 UID499의 운영 읽기 전용 백업·새 합성 복사본 삭제/복구·journal/세션/무결성/백업 보존 PASS. 실제 결과 execution-4df356d4005c442992653e0cfc76fd09/result.json 및15:05 사후 대조. 자동 보존기간·물리 삭제·실제 자료 파생본은 미검증 | 현재 수동 정책을 유지하고 실제 자료 연결 전 보존·폐기 정책 결정. 성공한 --apply 재실행 불필요 |
| EVAL-002 | UNVERIFIED/P2 | 과거 exact revision/원시 loss/history hash 없음 | 추가 사용자 로그는 저장소명·완료·반올림 loss를 확인. 누락값은 추측하지 않음 |
| TRAIN-001 | NOT_RUN/P2 | native NLI 동결/전역3회 제한/완료 후보 검증셋 평가 도구 연결. 실제 새 학습0/3 | 사람 검수·이력 확인·실행 전 OS probe/빈 모델 잠금을 통과한 뒤 필요한 경우만 실행 |
| RETRIEVAL-001 | IMPLEMENTED + BLOCKED/P1 | 승인/해시/철회 결합 참고 검색/MCP와 Recall/MRR·인용 구간 무결성 구현, 합성 stdio PASS. 실제 승인 판례/검수 검색 정답/의미적 인용 정확도 미측정; UID499 미배포 | 실제 corpus/목적별 사람 승인과 qrels부터 확보. 주 그래프 A~F RAG 연결/실측은 별도 |
| UI-001 | PARTIAL/P2 | 사건 관리 종료/재개·보류·사유·충돌/중복/지연 응답 처리, SPA 제목/H1 focus·동일 사건 재선택 수정. fixture1265×720 실제 브라우저·별도 마감 검토 PASS | run 20261020T164135+0900-lifecycle-ui-9152c8. 실제 모바일/VoiceOver/확대/다른 브라우저/UID499 배포는 미실행 |
| RETENTION-001 | IMPLEMENTED_SOURCE_ONLY/P1 | 사용자90/30일. schema2 lifecycle·명시적 백업/migration·백업 receipt/inventory와 UI 연결. 최종 backend153/frontend12 tests·fixture 브라우저 PASS | 실제 UID499 migration/배포/inventory·자동 보존 계획/스케줄러·백업 완전 폐기 미검증. 활성 수동 정책 보존·운영 삭제0 |
| MIGRATION-001 | CANDIDATE_REFRESHED_NOT_DEPLOYED/P1 | 최신119파일 후보·전환 검사·공개 schema1 코드의 새 합성 사본 이전/새 기록 후 schema2 동일 DB 코드 복귀·옛 DB 거부 PASS. 전체174 tests | RELEASE_TRANSITION 참조. 실제 관리자 진단/UID499·root 게시/일관 백업/migration/잠금/journal/실제MLX·정답OS·배포/복귀 후보 지정·운영 검증은 남음. 과거 --apply 재사용 금지 |

## 해결한 장애와 재시도

1. 오프라인 HF snapshot이 README/.gitattributes 누락으로 실패: 실행에 필요한 확장자만 allow_patterns로 지정해 기존 캐시 재사용. 수정1회, 다운로드0. 실패 run 폴더 보존.
2. 최초 합성 사건 DB insert의 placeholder 수9/column8 불일치: SQLite 예외로 실패한6개 테스트를 확인하고8개로 수정, 이후 통과. 같은 원인 수정1회.
3. 토큰 감사에서 Transformers5 BatchEncoding key 수2를 길이로 잘못 측정: v2 결과 INVALIDATED, return_dict=False 및 회귀 테스트 추가. v3에서 실제 max199 확인.
4. clean 환경 실제 추론이 직전 서버 graceful shutdown 중 MODEL_BUSY로 거부됨: 보호장치 정상. 이전 프로세스 종료를 확인한 후1회 재시도해 통과. 겹쳐 로드하거나 lock을 우회하지 않음.
5. UI 최종 검토: fixture 사용량을 모의 호출로 표시, 시간상 이전 결과만 선택/서버 비교 허용, 두 버전의 근거와 인용 표시, 작은 화면의 분석 버튼을 사건 헤더로 이동. 별도 검토 후 실제 브라우저로 재확인.

알려진 중대 문제가 해결되지 않은 상태에서 PILOT_READY/PRODUCTION_READY로 표시하지 않는다.

후속 실제 검증/실패 보존은 NEXT_PHASE_REPORT.md. DATA/EVAL/SECURITY 차단은 계속 유효하다. 초기 신규 자료 [E1] 표기 불일치는 v2의 E1:·명시적 evidence로 수정했고 최초 실패를 보존했다. 로그인 no-referrer 폼 Origin:null은 same-origin 정책으로 수정했으며 출처 검사를 우회하지 않았다.
