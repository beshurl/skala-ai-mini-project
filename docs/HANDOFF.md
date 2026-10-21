# RE:CASE 인수인계

## 모델 작업 준비·SQLite 진단 — 최신

현재 실제 UID499 PID41133/41754와 공유 model.lock inode25076574 점유를 확인했다. 사용자의 /usr/bin/sqlite3 -readonly 실행은 CANTOPEN14로 실패해 실제 작업/취소 상태는 UNKNOWN이다. DB 손상/파일 누락/활성 작업0을 추정하지 않는다. 현재 세션 sudo-n은 암호 필요/exit1이며 원 DB·권한·서비스를 변경하지 않았다. 뒤이은 Python 진단 안내의 두 줄이 cd 한 줄로 합쳐진 시도는 진단 미실행이다.

새 diagnose_local_service.py는 root에서 고정 plist/라벨/PID/UID를 확인한 뒤 실제 UID499로 내려가 상태 폴더/DB/WAL/SHM metadata와 readonly jobs 집계만 반환한다. 파일 생성/복구/chmod·서비스 재시작/모델 호출·원문/키/개별 사건ID 출력은 없다. immutable SQLite를 쓰지 않아 live WAL의 대기 작업을 숨기지 않는다. SQLite의 정상 WAL reader coordination 가능성은 별도 명시했다. 합성 누락/손상/심볼릭 링크·live WAL·비관리자/다른 PID 차단6 tests와 모델 생성 API 계약7 tests를 추가했고 전체257 tests/compileall/pip check/diff PASS다. 실제 root 진단 결과는 아직 대기다.

기존 공개 NLI 학습262/검증139의401개 입력에 대해 실제 캐시 tokenizer로 변경 전후 formatted prompt bytes 동일·최대245 입력토큰을 확인했다. 기존 NLI 출력 한도128/greedy/seed0/thinking off는 그대로다. CPU 토크나이저 검사이며 가중치 로드/추론/새 의미 검토0이다. 원본 데이터/정답/검토 subject/사람 이력/450개 AI 결정과 격리49를 유지한 새 protected volume v3 패킷을 봉인하고 실제 load_packet/audit_native_nli PASS를 확인했다. 새 grant/AI chain은 이전 승인/판단 해시를 계승한 소스 재결합이며 사람 승인이나 새 데이터 결정이 아니다.

preparation-plan.json은 execution_ready=false/executable=null인 준비본이다. 기존 실행기의 소스 변경 거부(exit1)를 실제 확인했으며 옛 명령을 재사용하지 않는다. 현재 CANTOPEN/작업 상태 진단·새 실제 정답 접근 거부·중지/재개 검토 전 실행기를 제공하지 않는다. 새 학습0/3·독립 최종/실제 일반 추론 품질/A~F NOT_RUN, 새 실사건 코퍼스 격리/미사용·사람 승인 생성0·운영/유료/공개/원문 외부 전송/삭제0이다.

[현재 한 줄 명령·근거](MODEL_READINESS.md). 아래 절은 시점별 이력이다.

## 다중 증거 검토 구현 — 현재

2026-10-21 다중 증거 검토 경로 `evidence-reasoning-v1`을 구현했다. 직접 작성한 가상 주장/자료와 별도 명시 추가한 연습12개를 새 경로로 분석한다. 공개 자료 전체를 입력하고 관측·충돌·전제·미검증 가설·사람의 다음 확인/조건부 시간 계산을 반환하며 원문 ID/연속 인용/Unicode 구간을 검사한다. 최대8주장/24자료/원문24,000자/8호출/180초, 모델 문맥4,096/출력1,024토큰·형식 정리1회/모델 재시도0이다. 한도·무효 출력은 주장별 PARTIAL로 남기고 모델 실행 실패 후 후속 호출을 중단한다. 기존 제한된 방문 대조와 저장 이력은 별도 유지한다.

전체 backend243 tests, 최종 일반 경로11 tests, frontend16/typecheck/build PASS. 실제 IAB의 임의2주장/공개2자료+숨긴정정1/저장/인용/추가공개/재분석/비교/재로딩 보존·연습12개 명시 추가·320/390px 넘침0을 확인했다. 원문 인용/형식 검사는 의미 정확도의 증명이 아니다. 고정 FixtureModel은 INSUFFICIENT 모의 응답이며 실제 MLX의 복잡한 추론 정확도·독립 최종/A~F·36단계 실모델 평가는 NOT_RUN이다. 실제 UID499/8100 배포·새 모델 요청·학습0/3·사람 승인·폐기0, LOCAL_VALIDATED 유지다. 기존 소스 해시에 결합된 NLI 실행 계획은 model.py 변경으로 무효화됐으며 재준비 전 옛 실행 명령을 사용하지 않는다.

[구현·사용법](GENERAL_REASONING.md), [결과](../outputs/runs/20261021T092903+0900-general-reasoning-18336d/RESULT.txt).

아래 절은 각 시점의 이력이며 일반 추론 미구현 표기는 이번 구현 이전 상태다.

**2026-10-21 최신 복구/우선순위:** run 20261021T091557+0900-account-recovery-110ad4의 backend204/125파일·합성 CLI/PTY11항목 PASS. docs/ACCOUNT_RECOVERY.md를 따른다. 계정 소실 시 새 사본에 ID만 보존하고 모두 비활성/user/새 verifier·9001 격리, 실제 로컬 TTY 확인/새 암호·별도 seal 이후만 schema1 사용 가능. 과거 암호/역할은 복원하지 않으며 실제 사람 승인/UID499 적용0이다. 기존 계정 핸들도 schema/inode 교체를 거부한다. 사용자 '복잡한 상황 일반 추론 구현했나' 질문에 **아직 미구현**이라고 코드로 확인했다. 다음 구현 우선순위는 다중 증거·시간/신원/검사 충돌·정정/전언·가설/다음 확인 제안이다. 현재 그래프4주장/검색5/2자료·빈 hypotheses/P04~P12 미지원 상태를 정확히 유지한다. 실제 관리자/데이터/모델/배포/폐기 gate는 계속 남는다.

## 미제사건 검토 안내·사용자 테스트 자료 — 2026-10-21 최신

[설명·테스트 순서](CASE_REVIEW_AND_TESTING.md), [실행 근거](../outputs/runs/20261021T090257+0900-user-test-kit-47fdda/RESULT.txt), [자료 묶음](../outputs/runs/20261021T090257+0900-user-test-kit-47fdda/RECASE-test-kit.zip). 새 가상 사건12개/증거 기록48개/공개 단계36개를 작성했다. P01~P03만 현재 방문 대조 그래프에 연결하고, P04~P12는 수동 검토/향후 구현용으로 구분한다. 현재 localhost:8123에서 계정 로그인→‘테스트 사건3개 추가’로 사용할 수 있다. 기존 계정/사건 DB는 그대로 유지했으며 반복 추가는 증거 버전·분석 이력을 초기화하지 않는다.

전체 backend194/frontend14 tests·typecheck/build/compileall/pip check PASS.9개 고정 fixture 단계는 완료7/관련 자료 부족 부분 완료2로 명시 검증했다. 실제 IAB의 P01 v1→v2→v3 분석·인용·비교, P03 부분 완료와 누락 정보, 반복 추가/재기동 후 기록 보존,320/390px 넘침0을 확인했다. 실제 모델 정확도/사건 해결률 검증이 아니다. 수동27단계의 모델 평가는 NOT_RUN이다.

입력·제안 참고표를 분리하고 단계 입력에는 그때까지 공개된 증거만 넣었다. AI 작성·사람 검수 대기·개발 노출·학습 부적격/독립 최종셋 아님을 기록했다. 기존 review-packet-v2의12건과는 다른 묶음이며 합산해 독립 자료로 세지 않는다. 기존 NLI ledger884·원본15개·제공 이미지12개·원래 모델 잠금·실제 UID499 프로세스 보존, 추가 실제MLX/학습/사람 승인/유료·공개·원문 외부 전송0이다.

새 release에 practice.py를 포함하면 data/practice/v1/cases.json도 manifest에 포함해야 한다. 누락은 PRACTICE_DATA_REQUIRED로 거부하며 검토 참고표·계정 DB는 release 허용 경로가 아니다. 기존 계정 통합 후보의 검증은 당시 스냅샷으로 보존하고, 이번 변경을 실제 UID499에 적용했다고 해석하지 않는다. 기존 graph/testing/model은 바꾸지 않았다. 시간 오차·다른 사람의 확인 기록·출처 충돌·정정 등을 일반 처리하는 기능과 실제 수사 성능은 미완료다. LOCAL_VALIDATED 유지.


**2026-10-21 최신 계정 통합:** 사용자 완료 통보 후 backend195/frontend14·타입/빌드·123파일 후보의 FixtureModel/실제 stdio MCP/HTTP·SSE·계정/사건 pair·현재 자격정보/권한/비활성/소유권·재시작 PASS. docs/ACCOUNT_RECOVERY.md와 run 20261021T090314+0900-account-integration-6a7cb0/RESULT.txt를 따른다. 구 접근키/계정 과거 사본/새 기록 없는 사건 사본 전환은 거부한다. 과거 계정 이미지는 암호화 보류만 하며 자동 복원/폐기하지 않는다. 실제 UID499·기존 소유권 연결·계정 DB 소실 복구·복귀 후보·모델/부하/정답 OS/자동 보존·독립 데이터 gate는 미완료다. 아래119·174 및 계정 작업 대기는 이력이다.

## 이메일·비밀번호 인증·미리보기 적용 — 2026-10-20 최신

사용자 요청으로 현재 checkout과 localhost:8123을 계정 방식으로 변경했다. [사용/운영자 안내](AUTHENTICATION.md), [실행 근거](../outputs/runs/20261020T175323+0900-account-login-127a6e/RESULT.txt). 공개 가입은 user, 운영자는 같은 로그인/서버 role 검사다. 계정 DB/scrypt·메모리 세션/CSRF·소유권을 분리하고 기존 접근키/Basic/중복 관리자 로그인·독립 HTML/CSS/생성기7파일을 제거했다. 삭제 전 소스와 기존 데이터/모델/평가는 보존했다.

backend178/frontend14 tests·typecheck/build/compileall/pip check/diff PASS. 실제 IAB에서 가입·잘못된 비밀번호/확인 불일치·로그아웃·재시작 뒤 같은 계정/사건/v1~v3 이력 보존·일반 계정 운영자 차단·로그인 복귀·합성 분석/인용/비교를 확인했다. 320/390px 폼 넘침0과 데스크톱 배치를 확인했다. 최종8123은 새 합성 DB/빈 계정 DB이며 공용 암호/관리자는 미생성이다.

**실제 UID499/8100은 미적용·서비스 중단/추가 모델 요청0**이다. 앞선119파일 후보/174 tests는 접근키 시점으로 보존한다. 새 계정 DB의 운영 이전·암호화 백업/복구·권한/credential_version 보존·복귀와 실제 모델 흐름의 통합 검증은 남는다. 계정 DB·현재 journal을 과거 사건 백업과 함께 롤백하지 않는다. 기존15개 SHA/이미지12개·공유 model.lock inode25076574·노출884 보존 확인, 새 학습/사람 승인/공개 배포/유료 호출0이다. LOCAL_VALIDATED 유지.


**사용자 확인한 병행 작업:**119파일 후보 생성 후17:56경 API/admin/Store·accounts/auth_api가 계정 인증 방식으로 바뀌었다. 사용자 답변은 '다른 작업에서 진행 중 — 완료 후 통합 검증'이다. 인증 변경을 덮어쓰지 않는다. 이번174 tests·3단계 이전/복귀/crypto는 변경 전 접근키 인증 스냅샷이고 현재 계정 sidecar·세션/역할·이전/복귀의 증명이 아니다. 후보119는 보존·미배포하며 계정 개편 완료 뒤 최신 전체 소스/데이터와 새 통합 검증이 필요하다. 원본/운영 서비스/DB는 그대로다.

**최신119파일 후보/전환 검사:** docs/RELEASE_TRANSITION.md와 run 20261020T173502+0900-release-transition-bcc984/RESULT.txt. 새 crypto 도구와 backup/migration/retention 연결 종료 수정 포함. 첫 SHA 실패를 GC로 재현해 지연된 SQLite close/checkpoint를 확인·수정했으며 강제GC 후 본체 SHA 유지/열린 연결0·관련38/전체174 tests PASS. manifest0644 거부는 새 manifest0600 제한 후 검증했고 archive/첫 실패 보존. schema1 공개 코드의 새 합성 분석→사본 schema2 이전/삭제 이력/새 인증·MCP·v2·종료/보류→보존한 schema2 호환 후보로 동일 DB 복귀의3단계와 최신 후보 crypto CLI PASS. 옛/오래된 DB 복귀2건 거부·새 기록 보존을 확인했다. 실제 UID499/MLX/서비스·DB/키·배포/복귀/자동삭제0·관리자 인증 부재다. schema2 fallback115는 호환성 시험용이며 최신 수정/crypto 도구는 없고 실제 복귀 후보 지정은 별도다. 현재 NLI 입력에 묶인7개 backend source SHA도 그대로였다. 아래119파일 재생성 전 상태는 시점 이력으로 구분한다.

**최신 암호화 백업:** docs/ENCRYPTED_BACKUPS.md와 run 20261020T170913+0900-encrypted-backups-0d84fb/RESULT.txt. 새 encrypted_backups.py/CLI가 메모리 일관 스냅샷·백업별 새 AES-256-GCM 키/nonce·별도0700 키 폴더/0600 파일·인증 후 새 scratch 복구/현재 journal/세션·대기 작업·보존 보류를 연결한다. 실제 합성 CLI13개(거부3개 포함), 전체164 tests PASS. 현재 키/journal·불변 암호문/receipt 결합과90/30일 미리보기·나중 보류·stale proof를 확인했다. 평문 복구 scratch를 보존하며 키 이름 변경/복원 시험은 완전 폐기가 아니다. 실제 UID499/기존 백업 전환/자동 삭제·키 폐기0·관리자 인증 부재 유지다. 새 비활성 v4 정책을 추가했고 기존 정책/후보는 보존했다. 앞선115파일 후보는 이번 새 도구/의존성 선언을 포함하지 않으므로 실제 적용 전 최신 후보를 재생성한다. 관측 sidecar/로그·snapshot/swap·키 사본/실제 완전 폐기 검증은 별도다.

**최신 UI·운영 준비:** outputs/runs/20261020T164135+0900-lifecycle-ui-9152c8/RESULT.txt. 종료/재개·보류/해제의 사유·충돌/이중 제출/지연 응답·오류 뒤 초안 보존·종료 후 쓰기 차단, SPA 제목/H1 focus·같은 사건 재선택을 구현했다. fixture1265×720 브라우저/기존 분석·인용·비교 회귀/별도 마감 검토·detector1회 [] PASS. 최종 backend153/frontend12 tests·typecheck/build/compileall/pip check/diff exit0. 실제 모바일/VoiceOver/확대/다른 엔진은 미실행.

115파일 코드·정적 빌드 후보/SHA manifest와 새 사본의 실제 stdio MCP·SSE·종료 후 쓰기 차단을 확인했다. 기존 venv/fixture만이며 UID499 운영 적용0. DEPLOYMENT_REVIEW.txt는 적용 실행기가 아니다. 관리자 작업 진단·새 백업/migration·원래 잠금·독립 journal·유실 없는 rollback 확인 후 새 적용 계획이 필요하다. 90/30일 비활성/수동 정책·원본15개/공유 잠금/최신884노출 보존, 자동 삭제/스케줄러/키 폐기·새 실제 요청0·학습0/3이다.

**현재 데이터:** docs/DELEGATED_NLI_REVIEW.md와 run 20261020T161908+0900-authorized-data-validation/CURRENT_RESULT.json. 공개 NLI450건 사용자 위임 검토 통과262/139·격리49는 AI 수행으로 유지한다. 사람/진단/실제 판결문/독립 최종 승인으로 확대하지 않는다. 새 OS probe·서비스 일시 중지의 관리자 인증이 남는다. 아래450건 직접 검수 차단/노출556/UI 미연결은 이전 시점 이력이다.

**현재 우선 상태:** outputs/runs/20261020T161845+0900-retention-lifecycle-10ab30/RESULT.txt. checkout은 schema2이고 UID499 운영 복사본/DB는 미변경이다. schema1 쓰기 Store는 MIGRATION_REQUIRED이며 자동 변환하지 않는다. case_lifecycle.py migrate는 서비스 중지 잠금·정확한 기존 열 구조·새 SQLite rollback 백업 뒤 transaction으로 생성/종료·보류 metadata를 추가한다. 과거 시각/출처는 null/unclassified다. 새 사건만 알려진 synthetic_fixture로 기록한다. API/CLI 종료·재개·보류·해제에 소유권/CSRF/버전/revision, 종료된 사건 변경 거부를 연결했다.

백업 receipt의 명시적 생성 시각·내용 SHA·현재 독립 journal에 결합한 실제 복구 검증과 metadata inventory를 추가했다. 복구는 세션 폐기·대기 작업 실패·남은 사건 보류를 적용하고 오래된 만료 계획 재사용을 막는다. 실제 CLI16개 합성 DB 검증/전체139 tests PASS. 최초 바이트 동일 검사 가정 실패는 보존하고 원본 불변/논리 내용·schema 동등/rollback 자체 SHA로 정정해1회 성공했다. 자동 삭제/백업·키 폐기/실제 서비스 migration·배포0이며 frontend 조작부도 남는다. 관리자 읽기 전용 상태 조회는 이번에도 password required로 실행되지 않았다. 사람 검수/새 OS proof/독립 최종/실제 판례/모델 평가·학습0/3/A~F는 이전 차단을 유지한다.

2026-10-20 KST. 사용자 요청은 개선 폴더의 작업을 이어서 진행하는 것이며, 뒤에 추가한 터미널 기록은 참고용이다. 해당 기록의 설치/생성/학습 명령을 재실행하지 않았다.

**최신 세 단계 후속:** 결과/현재 차단/사용자 명령은 outputs/runs/20261020T155158+0900-remaining-work-b82291/RESULT.txt와 USER_NEXT_STEPS.txt다. native600건(train300/사용자 선택 검증150/진단150)을 새 보호 패킷으로 봉인해 기존 freeze/3회 ledger에 실제 연결했다. 변경16건 우선 순서를 확인했고 실제 freeze는 미검수450·이력 확인 누락으로 예상 exit2/주기 생성0/학습0/3이다. 새 패킷 검수는 NEXT_ACTIONS 최신 명령을 따른다. 기존150건 패킷의 승인과 새 native subject는 서로 자동 이전하지 않는다. 독립 최종/A~F/새 자료 추론은 NOT_RUN이다.

참고 판례 검색/MCP·Recall/MRR·원문 구간 무결성 계산기를 추가했고 합성 fixture의 실제 stdio 승인/철회 경로를 통과했다. 실제 판례 승인/의미적 인용 품질 검증은 미완료이며 현재 UID499 배포에는 미반영이다. 사용자가 **사건90일·백업30일**을 선택했다. 새 정책 초안과 종료/생성 시각 기반 미리보기를 준비했으며 날짜 없는 과거 기록은 보류한다. 활성 수동 정책·운영 DB·백업/키 보존, 실제 삭제/스케줄러 설치0이다.

실제 서비스 지속 부하의 첫 합성 요청이30초 내 미완료여서32.566초에 중단됐다. 완료0/추가 제출0, 취소 HTTP200이지만 종료 확인은 미완료다. 전체 모델 호출은 NOT_MEASURED이며 스왑 관측을 원인으로 단정하지 않는다. 새 추론/재시작을 반복하지 말고 ADMIN_DIAGNOSTIC.txt의 서비스 UID 읽기 전용 집계를 사용자 터미널에서 확인한다. fixture desktop 접근성 감사와 백엔드122 tests/compileall/pip check는 제한 범위 PASS다. LOCAL_VALIDATED 유지; 아래 기록은 각 시점의 이력이다.

**최신16건 처리안:** 출판자 원문/라벨16건 일치·반입 오류0. 라벨 제안11건(기존 후보4+엄격 지침7)과 사용자 선택 재작성5건을 별도150건 초안으로 만들었다. 직접 응답 '5건 모두 별도 재작성안 사용 (권장)'은 wording-selection.json에 문구 선택으로 기록했다. 문구 대기0이며 사람 최종 라벨/권리 검수 승인으로 바꾸지 않았다. 원본·첫 초안·human ledger/후보 ledger 보존, 같은 계열/새 ID·subject hash 추적, 개발 작성 노출5건 append 후556기록 검증. 새 봉인 검수 패킷은 nli_validation_v2_wording_draft150건/승인0이며 실제 preflight는 미검수150·새 정답 OS proof 없음·모델 점유로 예상 exit2/모델 로드0이다. 기존 정답7개 PASS는 새 SHA 검증을 대신하지 않는다. outputs/runs/20261020T153504+0900-nli-disposition-draft-f94ac8/START_HERE.txt, CURRENT_STATUS.json, wording-applied-verification.json, review-packet-verification.json을 따른다. 새 평가/학습·gate 소스 수정0.

**최신 AI 후속 검토:** 사용자 '검수 해줘' 요청으로 기존150건 검토의 source 결합을 검증하고 쟁점17건을 재검토했다. 갱신 집계134지지/12문맥 판정/4수정 후보, 우선 판정16건이다. 나머지133건의 의미 판단은 이전 결과를 유지하며 이번에150건 전체를 다시 의미 검토했다고 계산하지 않는다. 원문/정답/분모/사람 직접 승인1건 보존, 새 노출17건 append 후551기록/chain PASS. 원라벨 변경·사람 승인·학습/추론·gate 변경0. 결과 outputs/runs/20261020T151035+0900-ai-review-followup-95bc0c/RESULT.txt. 개인정보 맥락13/문구 품질7은 여전히 검토 표식이다. 판결문·사건 증거 범위로 승인/검토를 확장하지 않는다.

**최신 AI 검토:** 사용자가 이 채팅 AI의 공개 KLUE NLI 검증150건 열람·의미 검토를 명시 승인했다.150건 AI 검토 완료(라벨 지지133/판정 기준 재확인12/수정 후보5), 개인정보·인물 맥락 후보13/문구 품질7. 승인자는사용자/수행자는AI로 기록했고 사람 직접 검수로 표시하지 않았다. 기존 직접 승인1건(근거 yes 보완 필요)/대기149건, 원본/라벨/분모를 보존했다. 개발 품질 검토 노출150건을 append해 기존384→534개 이력을 검증했다. 결과 outputs/runs/20261020T150037+0900-ai-semantic-review-4f0bf5/RESULT.txt. 상세 원문 보고서는 별도 암호화 볼륨에 있다. 실제 판결문·사건 증거의 외부 전송이나 모델 학습 승인은 이 요청에 포함되지 않는다. 새 자료 모델 재평가/학습은 NOT_RUN이며 gate 우회 없음. 아래 사람 승인0·외부 전송0은 당시 이력이며 현재 승인된 NLI 채팅 검토와 구분한다.

**최신15:05 KST — 실제 UID499 운영 검증 완료:** 사용자 --apply는15:03:11 KST/exit0, UID/EUID499로 운영 DB 읽기 전용 백업과 새 합성 복사본 삭제/복구·최신 journal 보존·세션 폐기·무결성을 통과했다. 실제 결과는 outputs/runs/20261020T145215+0900-isolated-operations/execution-4df356d4005c442992653e0cfc76fd09/result.json. 계획/코드/정책 해시와 현재 PID41133/UID499/ready=true/56 LoRA/공유 잠금은 outputs/runs/20261020T150521+0900-operations-confirmed-6923ae/verification.json에서 독립 대조했다. 같은 계획을 다시 적용하지 않는다. 백업 보관·자동 삭제 비활성·물리 삭제 미검증 범위를 유지한다. 다음은 사람 검수이며 validation 승인1/대기149, 전체 승인1/892, 학습용300건 미검수/이력 확인 누락이다. 다음10건 보호 파일과 사용자 재개 명령은 NEXT_ACTIONS에 있다. 새 자료 평가/학습0·A~F0/6. 아래 준비/실패 기록은 당시 이력이다.

**15:00 KST 운영 검증 준비:** 전체96 tests PASS. 실제 배포 인터프리터/모듈과 새 UID501 합성 DB의 읽기 전용 백업·복사본 삭제/복구/세션 폐기/대기 작업 정리 PASS. UID499 실제 state는 관리자 계정 전환 인증 부재로 NOT_RUN이다. 계정/서비스/데이터를 바꾸는 대신 hash-bound plan-final.json과 사용자 실행 명령을 NEXT_ACTIONS 4번에 준비했다. 근거 outputs/runs/20261020T145215+0900-isolated-operations/. 현재 사람 검수0·새 자료 평가/학습0 유지.

**14:47 KST 소프트웨어 준비 추가:** native NLI 동결/동일 전역3회 ledger·완료 후보 검증셋 평가/조건 일치 비교를 연결했다. 전체88 tests/봉인16 tests PASS, 실제 CPU tokenizer450건 PASS. 미검수450건/이력 확인 누락으로 동결은 예상 거부/학습0이다. UID499에서도 실제 합성12요청9완료/3개429와 인증/권한 경계를 확인했다. 새 자료 재평가·학습/A~F는 여전히 NOT_RUN. 현재 사용자 검수 명령과 이후 절차는 [NEXT_ACTIONS](NEXT_ACTIONS.md), 근거는 outputs/runs/20261020T143802+0900-next-actions/를 따른다. 현재 운영 DB는 분리 배포 state/이며 원래 runtime DB에 운영 삭제/복구를 실행하지 않는다.

**최신14:43 KST: OS 격리 PASS(검사 경로 한정).** 사용자 터미널 적용으로 생성된 UID499 전용 계정/배포를 유지하고 중단된 모델 기동을 복구했다. 원인은 root 소유 app/runtime이 umask077로0700이 된 것이며0755로 수정하고 동일 daemon만 재기동했다. 현재PID41133/UID499, 모델ready=true/기존56 LoRA, 실제 정답7개 서비스 접근 거부·평가자UID501 읽기/해시, 작업 폴더 정답/키4경로 거부, 원본14개/공유 잠금 inode를 확인했다. backend83 tests PASS. 근거는 outputs/runs/20261020T134803+0900-isolation-review-0385fc/finish-20261020T144251-f1772e/result.json 및 outputs/runs/20261020T144223+0900-finish-isolation-d3c15a/post-cutover-verification.json. 아래 과거 UID501/인증 실패 기록은 이력이다. 서비스 실제DB·최신 삭제 journal은 /Users/Shared/RECASE-isolated-0385fc/state/이다. 운영 시작/중단은 OPERATIONS의 격리 배포 절차를 따른다. 사람 검수0건·새 자료 재평가/학습 NOT_RUN, 분리 후 백업/삭제복구 재검증 NOT_RUN.

추가 공개 자료48,224건(KLUE/LBOX/KoBLEX)을 격리 수집했고892건의 검수/평가 후보를 준비했다. 자동 검사에서143건을 우선 사람 확인 대상으로 표시했다. 검수 담당은 사용자이며 실제 사람 검수·목적 승인0건, 새 자료 재평가/학습 NOT_RUN이다. 별도 암호화 APFS 이미지에 실제 정답7개와 해시 일치까지 준비했으나 관리자 인증300초 시간 초과로 전용 계정 생성·서비스 전환은 미실행이다. 기존 서버UID501/PID1399를 유지했고 OS 격리는 BLOCKED다. 관리자 적용 계획/로컬 터미널 명령/검수 CLI/전환 후 DB·삭제 journal 경로는 [최신 안내](../outputs/runs/20261020T134803+0900-isolation-review-0385fc/START_HERE.txt)에 있다. backend66개·준비 패킷16개 테스트 PASS를 실제 OS 접근 거부나 사람 검수 완료로 해석하지 않는다.

재인증2차는14:28:21–14:31:19 KST/exit1. 관리자 명령이 Downloads의 helper를 읽지 못해 errno1로 종료됐으며 계정 변경 코드는 시작되지 않았다. 터미널 앱 자동 제어는 도구 안전 제한으로 거부됐다. 사용자가 기존 로컬 터미널에서 이미 검토한 sudo 명령을 직접 실행하도록 요청했고 아직 PASS 결과는 없다. 파일 접근 허용 범위를 임의 확장하거나 다른 경로 복사로 보호 경계를 우회하지 않았다. 2차 실행/진단 JSON을 첫 실패와 별도로 보존했다.

현재 소스 경로는 backend/와 frontend/로 분리했다. [STRUCTURE](STRUCTURE.md)를 먼저 확인한다. 공유 자료·비밀키·삭제 이력 경로는 그대로다. 분리 후 루트와 backend/에서 각각57개 테스트, 프론트 빌드, 실제 MLX/MCP 분석1건, 개발 프록시 인증/API를 확인했다. 근거는 outputs/runs/20261020-folder-split/에 있다.

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

핵심 소스 backend/recase/{api,store,model,graph,worker,mcp_client,mcp_server,capability,contracts,search,governance,ingestion,temporal}.py, frontend/src/, backend/tests/. 기존 MLX 평가·비교·데이터 생성/변환·반입/학습 launcher의 덮어쓰기/조건 확인을 보완했다. 기존 CUDA 도구는 보존했지만 이번 Mac 검증 대상이 아니다.

환경은 backend/requirements-lock-macos-arm64.txt, 명령은 Makefile과 OPERATIONS.md, 결정은 docs/adr/에 기록했다. Git은 이 프로젝트 내부 `codex/recase-local` 브랜치이며 원본 기준 커밋35bfb54를 보존한다. 참고 all_total_vue_student는 수정하거나 복사하지 않았다.

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

브라우저 E2E는 cua_repl에서 `frontend/scripts/browser_e2e.mjs`의 `run(tab)`을 실행한다. 실제 모델/어댑터를 UI에서 확인하고 새 합성 세션을 생성해 검증한다. 자체 브라우저를 시작하는 별도 Playwright shell transport는 사용하지 않았다. 모의 오류 검증은 backend/scripts/serve_fixture.py의 별도 로컬 포트/새 DB로 수행했으며 최종 사용자 서버와 분리한다.

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


## 2026-10-20 후속 — 공개 NLI의 명시 사용자 위임

기존 위의 사람 검수 전제에 대한 예외는 **사용자 직접 승인한 공개 NLI450 subject에만** 적용한다. docs/DELEGATED_NLI_REVIEW.md를 먼저 읽고 outputs/runs/20261020T161908+0900-authorized-data-validation/final-packet.json의 패킷을 사용한다. 학습262/검증139 통과,49격리/진단150 미승인/사람 승인 생성0이다. 기존 패킷은 소스 코드 hash가 달라 현재 실행에 재사용하지 않는다.

실제 새 정답의 서비스 계정 probe가 관리자 인증 부재로 실행되지 않아 학습은 NOT_RUN/0회다. 같은 run의 실행기는 사용자 터미널 인증 뒤 실제 접근 차단·동결·서비스 pause·기본 모델 검증·후보1개 학습/검증·기존 서비스 재개를 수행한다. 전달한 명령의 실제 execution-*/result.json·전역 ledger·가중치/평가 결과를 확인한 후 상태를 갱신한다. 같은 명령의 자동 재실행이나 후보 추가를 하지 않는다. 기존 UID499 운영 소스/schema1 DB는 이번에 배포·마이그레이션하지 않았다. 공개 NLI 위임은 실제 판결문 승인이나 독립 최종셋 확보가 아니다.
