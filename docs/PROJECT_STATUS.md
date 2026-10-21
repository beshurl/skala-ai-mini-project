# 현재 상태

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

## 계정 소실 복구·다음 추론 구현 — 2026-10-21 최신

[복구 결과](../outputs/runs/20261021T091557+0900-account-recovery-110ad4/RESULT.txt)/[사용법](ACCOUNT_RECOVERY.md). backend204 tests와125파일 후보의 합성 CLI/PTY11항목을 통과했다. 새 사본에 과거 ID만 보존하고 모든 계정을 비활성/user·새 verifier·격리 스키마로 시작한다. 사용자가 로컬 TTY에서 소유권/새 암호를 확인한 계정만 활성화하고 보류 유지 확인 후 별도 봉인한다. 과거 암호/운영자 역할 복원0·실제 사람 승인/UID499 운영 적용0이다.

사용자 질문으로 **복잡한 일반 추론은 아직 미구현**임을 명확히 했다. 현재 그래프는 같은 장소/날짜의 제한된 방문 대조·최대4주장/검색5/2자료·hypotheses=[]이며 다음 구현 우선순위는 다중 증거·시간 구간·동일인/불확실성·검사 충돌·문서 정정/전언·가설/다음 확인 제안이다. 계정 검증을 일반 추론 검증으로 계산하지 않는다. 실제 운영 관리자/소유권·MLX/OS/부하·독립 최종/승인 판례/A~F·학습0/3·보관/폐기 조건은 계속 남아 있다.

## 미제사건 검토 안내·사용자 테스트 자료 — 2026-10-21 최신

[설명·테스트 순서](CASE_REVIEW_AND_TESTING.md), [실행 근거](../outputs/runs/20261021T090257+0900-user-test-kit-47fdda/RESULT.txt), [자료 묶음](../outputs/runs/20261021T090257+0900-user-test-kit-47fdda/RECASE-test-kit.zip). 새 가상 사건12개/증거 기록48개/공개 단계36개를 작성했다. P01~P03만 현재 방문 대조 그래프에 연결하고, P04~P12는 수동 검토/향후 구현용으로 구분한다. 현재 localhost:8123에서 계정 로그인→‘테스트 사건3개 추가’로 사용할 수 있다. 기존 계정/사건 DB는 그대로 유지했으며 반복 추가는 증거 버전·분석 이력을 초기화하지 않는다.

전체 backend194/frontend14 tests·typecheck/build/compileall/pip check PASS.9개 고정 fixture 단계는 완료7/관련 자료 부족 부분 완료2로 명시 검증했다. 실제 IAB의 P01 v1→v2→v3 분석·인용·비교, P03 부분 완료와 누락 정보, 반복 추가/재기동 후 기록 보존,320/390px 넘침0을 확인했다. 실제 모델 정확도/사건 해결률 검증이 아니다. 수동27단계의 모델 평가는 NOT_RUN이다.

입력·제안 참고표를 분리하고 단계 입력에는 그때까지 공개된 증거만 넣었다. AI 작성·사람 검수 대기·개발 노출·학습 부적격/독립 최종셋 아님을 기록했다. 기존 review-packet-v2의12건과는 다른 묶음이며 합산해 독립 자료로 세지 않는다. 기존 NLI ledger884·원본15개·제공 이미지12개·원래 모델 잠금·실제 UID499 프로세스 보존, 추가 실제MLX/학습/사람 승인/유료·공개·원문 외부 전송0이다.

새 release에 practice.py를 포함하면 data/practice/v1/cases.json도 manifest에 포함해야 한다. 누락은 PRACTICE_DATA_REQUIRED로 거부하며 검토 참고표·계정 DB는 release 허용 경로가 아니다. 기존 계정 통합 후보의 검증은 당시 스냅샷으로 보존하고, 이번 변경을 실제 UID499에 적용했다고 해석하지 않는다. 기존 graph/testing/model은 바꾸지 않았다. 시간 오차·다른 사람의 확인 기록·출처 충돌·정정 등을 일반 처리하는 기능과 실제 수사 성능은 미완료다. LOCAL_VALIDATED 유지.


## 계정 개편 후 통합 검증 — 2026-10-21 최신

사용자 완료 통보 후 최신 backend195/frontend14 tests·typecheck/build/compileall/pip check PASS. [계정 복구 안내](ACCOUNT_RECOVERY.md), [실행 결과](../outputs/runs/20261021T090314+0900-account-integration-6a7cb0/RESULT.txt)를 따른다. 계정/사건 암호화 pair와 공통 maintenance lock·소유권 검사를 추가했다. 현재 비밀번호/권한/비활성/credential_version을 보존한다. 새123파일0400/0500 후보에서 실제 stdio MCP/HTTP/SSE·v1/v2 분석·최신 삭제 이력·복구 후 로그인·재시작/새 기록 보존을 확인했다. 구 접근키 코드·계정 과거 사본·오래된 사건 사본 전환은 거부한다.

소스/새 합성 자료/FixtureModel/UID501 한정이다. 실제 UID499 운영 배포/모델 요청/학습/자동 삭제/키 폐기0. 운영 복귀 후보·기존 사건 소유권 연결·계정 DB 소실 시 재발급/복구·관리자 진단·실제 모델/부하/정답 OS·독립 최종셋/승인 판례/A~F·학습0/3은 미완료다. LOCAL_VALIDATED 유지. 아래119/174 및 계정 작업 대기는 당시 이력이다.

## 이메일·비밀번호 인증·미리보기 적용 — 2026-10-20 최신

사용자 요청으로 현재 checkout과 localhost:8123을 계정 방식으로 변경했다. [사용/운영자 안내](AUTHENTICATION.md), [실행 근거](../outputs/runs/20261020T175323+0900-account-login-127a6e/RESULT.txt). 공개 가입은 user, 운영자는 같은 로그인/서버 role 검사다. 계정 DB/scrypt·메모리 세션/CSRF·소유권을 분리하고 기존 접근키/Basic/중복 관리자 로그인·독립 HTML/CSS/생성기7파일을 제거했다. 삭제 전 소스와 기존 데이터/모델/평가는 보존했다.

backend178/frontend14 tests·typecheck/build/compileall/pip check/diff PASS. 실제 IAB에서 가입·잘못된 비밀번호/확인 불일치·로그아웃·재시작 뒤 같은 계정/사건/v1~v3 이력 보존·일반 계정 운영자 차단·로그인 복귀·합성 분석/인용/비교를 확인했다. 320/390px 폼 넘침0과 데스크톱 배치를 확인했다. 최종8123은 새 합성 DB/빈 계정 DB이며 공용 암호/관리자는 미생성이다.

**실제 UID499/8100은 미적용·서비스 중단/추가 모델 요청0**이다. 앞선119파일 후보/174 tests는 접근키 시점으로 보존한다. 새 계정 DB의 운영 이전·암호화 백업/복구·권한/credential_version 보존·복귀와 실제 모델 흐름의 통합 검증은 남는다. 계정 DB·현재 journal을 과거 사건 백업과 함께 롤백하지 않는다. 기존15개 SHA/이미지12개·공유 model.lock inode25076574·노출884 보존 확인, 새 학습/사람 승인/공개 배포/유료 호출0이다. LOCAL_VALIDATED 유지.


## 병행 계정 개편·검증 범위 — 현재

119파일 후보를 만든 뒤17:56경 api.py/admin.py/store.py와 새 accounts/auth_api가 아이디·비밀번호 계정 방식으로 변경됐다. 사용자는 **다른 작업에서 진행 중 — 완료 후 통합 검증**이라고 답했다. 변경은 보존하며 이번119파일 후보·174 tests와3단계 이전/복귀 시험은 개편 전 접근키 인증 스냅샷 근거로 한정한다. 현재 계정 인증/계정 DB·세션 sidecar의 이전/백업/복구·역할·코드 복귀는 미검증이다. 이번 main-DB 전환 검사를 전체 계정 배포 승인으로 사용하지 않는다. 실제 UID499 서비스는 이전 버전 그대로이며 관리자 진단도 인증 대기다. 개편 완료 후 최신 소스/화면·계정 데이터와 통합 검증한다.

## 최신119파일 후보·DB 전환 검사 — 최신

[결과](../outputs/runs/20261020T173502+0900-release-transition-bcc984/RESULT.txt)/[전환 검사 사용법·한계](RELEASE_TRANSITION.md). 최신 암호화 도구와 SQLite 연결 종료 수정을 포함한119파일 후보를 갱신했다. 읽기 전용 코드 트리의119개 SHA/미기록 파일·schema 선언을 검사하고, 중지 잠금 아래 현재 기록·결과·삭제 이력·보존 상태가 없는/달라진 전환 사본을 거부하는 verify_release_database.py를 추가했다. 표준 빈 lock·SQLite WAL/SHM 조정 sidecar 생성 가능성은 문서화했다.

현재 운영의 공개 코드만 복사한 schema1 합성 분석→새 사본 schema2 migration/journal→새 개인 인증·MCP/SSE·v2 결과/종료·보류 기록→이전 schema2 후보로 동일 DB 코드 복귀의3단계 PASS. schema1/오래된 schema2 사본 복귀는 exit2로 차단했고 새 기록이 유지됐다. 최신 후보 안의 암호화 백업/복구도 PASS. 이는 UID501/TestClient/FixtureModel·실제 stdio MCP이며 실제 UID499/MLX/운영 접근키·배포/복귀는 NOT_RUN이다.

첫 시험1건의 SHA 변화는 backup/migration/retention의 지연된 SQLite 연결 종료·WAL 체크포인트로 진단했다. 연결을 명시적으로 닫아 강제GC 후 본체 SHA 유지·열린 연결0·관련38/전체174 tests·compileall/pip check/diff·새 frontend build PASS다. 새 manifest0644 거부는0600 제한 후 재검증했고 첫 실패·archive를 보존했다. 실제 관리자 계정 전환은 password required/exit1, 서비스/DB 변경·새 실제 모델 요청·자동 삭제/키 폐기0다. 현재 NLI262/139·49격리/노출884·학습0/3·독립 최종/판례/A~F·부하/실제 접근성 미완료, LOCAL_VALIDATED 유지다. 아래 후보 재생성 필요/옛 테스트 수치는 각 시점 이력이다.

## 백업별 암호화·복구 증명 — 최신

[결과](../outputs/runs/20261020T170913+0900-encrypted-backups-0d84fb/RESULT.txt)/[사용법과 한계](ENCRYPTED_BACKUPS.md). 메인 사건 SQLite를 읽기 전용·일관된 메모리 스냅샷에서 AES-256-GCM으로 암호화하고 백업마다 새 키를 별도0700 디렉터리/0600 파일에 생성한다. 생성 중 평문 백업 파일0이다. 인증 후 새 복구 사본에만 현재 journal·세션 폐기·대기 작업 실패·복구 보류를 적용한다. 변조/잘못된·없는 키는 평문 scratch 생성 전 거부하며 복구 중 입력 변경은 PASS proof를 만들지 않는다.

실제 합성 CLI13개(예상 실패3개 포함)·전체164 tests/compileall/pip check/diff PASS. 현재 공급 journal/사용 가능한 검증 키·암호문·receipt에 결합한 inventory와90/30일 미리보기를 확인했다. 나중의 보류는 이전 백업에 전파하고 journal 변경/키 부재는 이전 복구 proof를 무효화한다. 새 비활성 정책은 data/local_operations_policy.90d-30d.encrypted.proposed.json이다.

실제 UID499·운영 서비스/DB/기존 백업 변경·새 모델 요청·자동 삭제/스케줄러·백업/키 폐기0. 관리자 비대화식 조회는 password required로 실행되지 않았다. 테스트 키를 이름 변경 후 복원한 것은 복구 차단 시험이며 완전 폐기 증명이 아니다. 평문 복구 scratch/이전 평문 백업·관측 sidecar/로그·APFS/swap/키 복제·같은 UID 침해는 미검증이다. 앞선115파일 배포 후보는 이번 새 도구를 포함하지 않아 실제 적용 전 재생성이 필요하다. 현재 NLI262/139·49격리/노출884·새 학습0/3·독립 최종/판례/A~F·장시간 부하 미완료와 LOCAL_VALIDATED를 유지한다.

## 사건 관리 화면·배포 후보 — 최신

[결과와 한계](../outputs/runs/20261020T164135+0900-lifecycle-ui-9152c8/RESULT.txt). 종료/재개·보존 보류/해제와 필수 사유 입력을 연결했다. 서버 확인 상태만 표시하고 증거 버전/revision 충돌·중복 제출·지연 응답·불확실한 저장 뒤 재조회 실패를 처리한다. 종료 후 새 분석/증거 변경은 잠그며 과거 결과는 열람한다. 다른 탭의 증거 변경 시 사유를 보존하고 내용 새로고침을 요구한다. 같은 사건 재선택의 상태 갱신과 SPA 제목/H1 focus도 수정했다.

fixture 브라우저1265×720에서 키보드 제출·재접속 후 보류·두 탭 충돌·재개·기존 v1→v2→v3 분석/인용/비교 회귀 PASS. 별도 마감 검토의 중대 수정0·범위 detector1회 []다. 최종 backend153/frontend12 tests·typecheck/build/compileall/pip check/diff exit0. 실제 모바일·확대·VoiceOver·교차 브라우저는 NOT_RUN이다.

코드·빌드115파일을 새 배포 후보로 묶고 SHA·새 폴더 전개·사본 모듈 provenance를 확인했다. 기존 venv/새 합성 DB의 실제 stdio MCP 분석·SSE·종료 후 쓰기 차단/기록 열람 PASS. 운영 파일 차이는 MATCH14/DIFFERENT12/ABSENT89로 기록했다. [배포 검토 초안](../outputs/runs/20261020T164135+0900-lifecycle-ui-9152c8/DEPLOYMENT_REVIEW.txt)은 관리자 작업 진단·새 백업/migration·원래 잠금 inode·최신 journal·변경 유실 없는 rollback 확인 전 적용 불가다. **실제 UID499·MLX·개인 인증의 새 배포 검증은 아니며 운영 적용0**이다.

90/30일 비활성 초안·활성 수동 정책을 유지했다. 운영 DB/서비스·자동 삭제·스케줄러·백업/키 폐기·새 실제 모델 요청0. 기존15개 SHA/공유 잠금/최신 승인 공개 NLI 노출884기록 보존. 현재 NLI 학습262/검증139·49격리는 아래 위임 검토 절을 따르며 사람 승인으로 바꾸지 않는다. 새 학습0/3·독립 최종/승인 실제 판례/A~F·장시간 부하 미완료, LOCAL_VALIDATED 유지. 아래는 각 시점 이력이다.

## 공개 NLI 사용자 위임 검토 — 최신

사용자가 **“공개 NLI만 AI 위임 검토 허용”**을 명시했다. [범위·결과·실행 안내](DELEGATED_NLI_REVIEW.md). 기존450건에 대한 AI 판단을 기록하고 학습262/검증139를 통과,49건을 격리했다. 검증134건의 이전 검토는 실제 문장·라벨·subject 결합 후 재사용했고 변경16건은 새로 검토했다. 새 실제 열람328건을 append해 노출556→884/prefix·chain 보존을 확인했다. 사람 승인 생성0·새 라벨 변경0, 실제 판결문/진단150의 승인 확대0이다. 공개 개발용 NLI이며 외부·사전학습 노출 UNKNOWN/독립 최종셋 아님을 유지한다.

별도 grant와 AI 판단 ledger를 데이터 감사·검증·동결에 연결하고 실제 사람 반려·변경/범위 밖 subject를 거부한다. 새 어댑터의 로컬 모델 경로/평가기 모델ID 불일치도 생성 설정 원본과 가중치를 보존하는 방식으로 수정했다. 백엔드153 tests/compileall/pip check/diff exit0, 실제 데이터 감사와 비변경 실행 계획 점검 PASS다. 기존 데이터/어댑터/평가15개 SHA 일치, 원래 공유 model.lock inode를 보존했다. 메인 서비스 소개는 증거 기반 AI 미제사건 재수사 지원으로 반영하고 fixture 화면을 확인했다. UID499 운영 복사본 배포는0이다.

**실제 새 학습은 NOT_RUN/0회**다. 새 정답3경로의 평가자 읽기는 확인했으나 현재 서비스 계정 probe는 관리자 인증 부재로 실행되지 않았다. freeze는 OS gate에서 예상 exit2/출력0/모델 로드0이다. 서비스 PID41133/UID499와 기존 잠금 점유를 확인했으며 중단/재시작/추론 재시도0이다. 같은 run의 `run_authorized_training.py --execute`는 사용자 로컬 터미널 인증 후 실제 접근 차단 확인→동결→서비스 일시 중지→기본 모델 검증→후보1개 학습·같은 검증 평가→기존 서비스 재개를 수행하도록 준비했다. 실제 결과 파일을 확인하기 전 실행 완료로 바꾸지 않는다. LOCAL_VALIDATED 유지.

## 보존정책의 시각 기록·복구 검증 연결 — 최신

[결과](../outputs/runs/20261020T161845+0900-retention-lifecycle-10ab30/RESULT.txt). 사건90일/백업30일을 계산할 수 있도록 소스에 schema2 lifecycle과 백업 생성·복구 receipt를 추가했다. 새 합성 사건만 생성 시각/출처를 기록하고 과거 schema1은 날짜 null/출처 unclassified로 보존한다. schema1의 쓰기 기동을 거부하며 중지 잠금·열 구조 확인·새 rollback 백업·transaction migration을 요구한다. 종료/재개/보존 보류/해제는 소유권·CSRF·증거 버전·lifecycle revision을 검사한다. 진행 중 분석이 있으면 종료를 거부하며 종료된 사건은 분석·증거 변경을 거부한다.

실제 CLI16개(주 흐름13개와 최신 journal 재검증3개)를 새 합성 DB에서 실행해 migration의 내용 보존,90/30일 만료 미리보기, 뒤늦은 사건 보류의 과거 백업 전파, 독립 journal 변경 시 복구 proof 무효화를 확인했다. 복구 사본은 세션 폐기·대기 작업 실패 처리·남은 모든 사건 보류를 적용해 과거 만료 계획의 재사용을 막는다. SQLite 백업이 원본과 바이트 동일하다는 잘못된 검증 가정의 첫 실패는 보존했고, 별도 진단 후 원본 보존/관계형 내용·스키마/백업 자체 SHA 결합을 나눠 검사해1회 복구 PASS했다.

**운영 UID499/DB/백업에는 미배포·변경0**이다. 현재 서비스 진단 sudo -n은 password required로 거부됐고 새 모델 호출은0이다. 자동 삭제/스케줄러/백업·키 완전 폐기도0·미검증이다. 새 정책 초안은 data/local_operations_policy.90d-30d.schema2.proposed.json이며 활성 수동 정책 SHA는 보존했다. UI 종료·보류 조작부와 실제 UID499 배포/재검증은 남는다. 사람 검수/새 정답 OS proof/독립 최종셋/실제 승인 판례/A~F·학습0/3 차단은 유지하며 LOCAL_VALIDATED를 승격하지 않는다. 전체139 tests/compileall/pip check/diff PASS이며 상세 명령·시각은 새 run의 검증 기록을 따른다.

## 세 단계 후속 — 최신

[전체 결과](../outputs/runs/20261020T155158+0900-remaining-work-b82291/RESULT.txt)와 [사용자 다음 단계](../outputs/runs/20261020T155158+0900-remaining-work-b82291/USER_NEXT_STEPS.txt)를 먼저 따른다. 사용자 보존기간 선택은 **사건90일·백업30일**로 기록했다. 새 정책 초안과 종료/생성 시각 기반 미리보기를 추가했다. 합성 경계값/날짜 미상/보류/복구 미검증을 검사했고 실제 삭제0·스케줄러 비활성이다. 현재 소스의 사건 종료일 부재 때문에 과거 날짜를 추정하지 않으며 활성 수동 정책·운영 DB는 변경하지 않았다.

사용자 선택 재작성 검증150건을 train300/diagnostic150과 새 native600건 패킷으로 봉인해 기존 동결/3회 ledger에 연결했다. 변경16건 우선 표시/동일 원검증 계열/학습 바이트 보존을 확인했다. 실제 동결은 미검수450건·노출 이력 확인 누락으로 예상 exit2이며 주기 생성0·새 학습0/3·추가 데이터 추론0이다. 독립 최종셋/A~F 비교는 NOT_RUN이며 새 정답의 실제 OS 재검증도 필요하다.

승인 원문 해시·processing/rag/display 목적 승인·사람 개인정보 검수와 최신 철회를 확인하는 참고 판례 검색/MCP 및 Recall@k/MRR·인용 구간 무결성 계산기를 구현했다. 합성 fixture 실제 stdio MCP 성공/철회 차단 PASS, 원출처 유형을 반환한다. 실제 승인 판례/검수된 검색 정답/의미적 인용 정확도는 미확보·NOT_MEASURED다. UID499 운영 복사본에는 아직 배포하지 않았으며 주 그래프 A~F RAG 연결·실행도 미완료다.

실제 UID499 지속 시험은 **첫 합성 요청이30초 내 미완료여서32.566초에 FAIL 중단**했다. 완료0·추가 제출0, 자체 작업 취소 HTTP200이나 최종 취소 상태는 미확인이다. 진행 중 모델 호출 총수는 NOT_MEASURED이며 준비 응답200을 분석 성공으로 계산하지 않는다. 스왑 사용은 관측했지만 원인은 미확정이다. [읽기 전용 관리자 진단](../outputs/runs/20261020T155158+0900-remaining-work-b82291/ADMIN_DIAGNOSTIC.txt)을 준비했다. 재시작/모델 중복 실행0이다.

fixture UI1265×720의 키보드/건너뛰기/대비/overflow를 점검했다. 사건 전환 후 focus·제목 개선 권고와 실제 VoiceOver/확대/교차 브라우저 미실행이 남는다. 접근성 감사는 전체 적합성 인증이 아니다. 백엔드122 tests/compileall/pip check PASS. 새 사람 승인/실제 판결문 외부 전송/공개 배포/백업·키 폐기0이며 **LOCAL_VALIDATED 유지**다. 아래 기록은 각 시점의 이력이다.

2026-10-20 KST. **LOCAL_VALIDATED: 합성 사건의 제한된 로컬 분석 흐름.** 전체 서비스 개발 목표는 미완료이며 PILOT_READY/PRODUCTION_READY로 승격하지 않는다.

## 16건 후속 처리와 사용자 문구 선택 반영 — 최신

출판자 원문·라벨16건과 반입 결과가 모두 같음을 확인했다. 기존 수정 후보4건과 엄격 추론 지침에 따른 문맥7건의 라벨 제안11건을 작성했다. 의도 복원이 어려운 나머지5건은 원문/명시 조건을 추가한 별도 진단 예문을 대조해 준비했고, 사용자가 **5건 모두 별도 재작성안 사용**을 선택했다. 문구 선택 대기0건이다. 재작성은 원문 오타 복원이나 실제 인물·현행 정책의 사실 확인이 아니다.

원본/첫 초안/공식 라벨/기존 사람 승인1건을 유지하고, 별도150건 초안에11개 라벨 제안+5개 문장 재작성을 반영했다. 원본 대비 라벨 차이는12건(앞선11건+재작성 중1건), 문장 차이는5건이다. 같은150계열을 보존하며 새 독립 최종 자료로 합산하지 않는다. AI 작성5건을 개발 노출로 append해 이력551→556건/prefix·chain을 확인했다. 사용자의 선택은 문구 사용 결정이며 최종 라벨·개인정보·권리·목적 승인으로 바꾸지 않았다.

[최신 안내](../outputs/runs/20261020T153504+0900-nli-disposition-draft-f94ac8/FINAL_HANDOFF.txt)에 새 검수 패킷·변경16건 대조표와 실행 명령이 있다. 실제 load_packet의150개 subject 결합/해시 검증 PASS이며, 새 패킷 사람 승인0/대기150이다. 실제 CLI에서 변경16건이 먼저 나오도록 검수 순서도 확인했다. 실제 사전검사는 승인150건 누락·새 정답 SHA와 기존 OS proof 불일치·현재 모델 점유로 예상 exit2/모델 로드0이다. 이전 정답 격리 PASS를 새 정답에 재사용하지 않는다. 새 평가/학습0·후보 예산 불변, 서비스/학습·평가 gate 소스 수정0. 아래134/12/4는 원본 자료 AI 검토 집계이며 새 초안의 승인 상태와 구분한다.

## 공개 NLI AI 검토 후속 확인 — 이전 기록

사용자의 '검수 해줘' 요청으로 기존150건 AI 검토의 ID/subject/원라벨/근거/입력·정답 해시 결합을 모두 확인하고 쟁점17건만 의미 재검토했다. 갱신 집계는 **원라벨 지지134 / 문맥·기준 판정12 / 라벨 수정 후보4**다. 기존 후보 중 배우자 호칭/현재 나이 해석1건은 문맥 판정으로 낮추고, 전반 출전 여부1건은 현재의 외부정보 보충 금지 지침 아래 원neutral 지지로 정리했다. 수정 후보는 출판자 오류 확정이 아니며 나머지133건은 기존 AI 판단을 유지한다.

원본/라벨/분모150·사람 직접 승인1/대기149 이력은 보존했다. 개인정보 맥락13건/문구 품질7건의 기존 표시도 유지하며 사람 개인정보·라이선스 검수 완료로 바꾸지 않는다. 두 번째 검토 노출17건을 추가해 이력534→551건을 확인했다. 로컬 모델 추론/새 학습0, 평가/학습 gate 변경0. [후속 결과](../outputs/runs/20261020T151035+0900-ai-review-followup-95bc0c/RESULT.txt)와 연결된 보호 볼륨의 우선16건 보고서를 따른다.

## 사용자 위임에 따른 공개 NLI AI 검토 완료 — 1차 기록

사용자가 공개 KLUE NLI 검증150건의 전제·가설·제안 라벨을 이 채팅 AI가 읽는 것을 명시 승인했다. 실제 수행자는AI/위임 승인자는사용자로 분리 기록했으며 직접 사람 검수 이력을 생성하거나 사용자 명의로 바꾸지 않았다.150건 모두 근거를 작성했다. 라벨 지지133/문맥·판정기준 재확인12/라벨 수정 후보5(재확인 총17), 개인정보·인물 맥락 후보13/문구 품질7이다. 이는 gold-aware AI 데이터 검토이며 확정된 라벨 오류 수나 모델 정확도가 아니다.

원본 라벨/입력·정답 SHA/분모150과 기존 직접 검수1건·대기149건을 보존했다. 기존 승인1건의 근거 yes는 보완이 필요하다. AI가 읽은 개발 품질 검토 노출150건을 기존384건 뒤에 hash chain으로 추가해534건을 확인했다. 원문 열람 승인은 해당 공개 NLI150건에 한정하며 LBOX 판결문·사건 증거는 포함하지 않는다. 새 모델 평가/학습 NOT_RUN, 기존 실제 검수·동결/3회 ledger/실제 OS 접근 gate는 유지한다. 결과는 [AI 검토 요약](../outputs/runs/20261020T150037+0900-ai-semantic-review-4f0bf5/RESULT.txt), 상세 원문/근거는 그 요약에 연결된 별도 암호화 볼륨의 보고서에 있다.

## 격리 운영 검증 완료 — 15:03 실행 / 15:05 사후 대조

사용자가 로컬 터미널에서 plan-final.json을 적용했다. **실제 서비스 UID/EUID499의 백업·복사본 삭제/복구 PASS**다. 운영 DB의 읽기 전용 SQLite 백업(사건80개 시점), 독립 journal1개 기록 보존, 새 복사본의 합성 사건 삭제·tombstone 재적용·세션 폐기·다른 사건 보존·0600·무결성·백업 바이트 보존을 확인했다. 운영 삭제/모델 호출/학습/서비스 중단은0이다. 실제 스냅샷에는 대기 작업이 없어 SERVER_RESTARTED 전환은0건이며 해당 전환은 앞선 합성 fixture1건에서 검증했다.

[실제 UID499 결과](../outputs/runs/20261020T145215+0900-isolated-operations/execution-4df356d4005c442992653e0cfc76fd09/result.json)를 계획·worker·배포 모듈·정책 해시와 대조했다. [독립 사후 확인](../outputs/runs/20261020T150521+0900-operations-confirmed-6923ae/verification.json)에서 현재 PID41133/UID499, 인증된 ready=true, 기존 모델/56 LoRA와 공유 잠금 inode 일치를 확인했다. 기존96 tests 대상 backend 소스도 변경되지 않았다. 같은 --apply 명령을 재실행하지 않는다. 백업은 서비스 전용0700 경로에 보관되며 자동 기간 삭제·물리 삭제·실제 자료 파생본 정책은 별도 미완료 조건이다.

다음 단계는 검증셋 사람 검수다. 현재 nli_validation 승인1/150·대기149, 전체892건 중 승인1건이다. 학습용300건도 미검수이며 노출 이력 확인이 없어 학습 데이터 감사는449건 승인 누락으로 BLOCKED다. 평가 사전검사도149건 승인 누락, 현재 서버의 모델 점유, 실행 세션의 계정 전환 인증 부재로 모델 로드 전 차단됐다. OS 격리/운영 검증 PASS를 취소하는 결과가 아니다. 다음10건을 보호 볼륨에 준비했으며 [검수 재개 안내](NEXT_ACTIONS.md)를 따른다. 새 자료 평가0·새 학습0/3·A~F0/6, LOCAL_VALIDATED 판정을 유지한다.

## 격리 운영 검증 준비 — 이전 기록

새 `verify_isolated_operations.py`/`operations_drill.py`가 실제 서비스 UID에서 운영 SQLite 읽기 전용 백업과 새 복사본의 합성 사건 삭제/복구를 수행하도록 준비됐다. 운영 사건/삭제 journal/기존 백업은 변경하지 않으며 모델 호출·서비스 중단은0이다. 실행계획은 worker·배포 코드·수동 운영정책 해시와 현재 UID/PID/경로를 고정한다.

전체96 tests/compileall/pip check/기존 비교/원본14개 SHA PASS. 실제 배포 venv와 SQLite 모듈을 사용한 새 합성 DB/UID501 검증에서 복구 시 tombstone 재적용·세션 폐기·대기 작업 SERVER_RESTARTED·생존 사건·0600/무결성/백업 바이트 보존을 확인했다. **실제 UID499와 운영 state의 실행은 아직 NOT_RUN**이다. 현재 비대화식 sudo 계정 전환은 password required로 거부됐다. 현재 OS 격리 PASS와 이 별도 운영 검증 준비를 구분한다.

사용자 로컬 관리자 실행 명령은 [NEXT_ACTIONS 4번](NEXT_ACTIONS.md)에 있다. 근거/최종 계획은 outputs/runs/20261020T145215+0900-isolated-operations/. 실제 사람 검수0·새 자료 평가0·새 학습0/3·A~F0/6을 유지한다. `data/local_operations_policy.json`은 현재 합성 로컬 수동 삭제·백업 보관 동작을 문서화하며 자동 기간 삭제/백업 폐기를 활성화하지 않는다.

## NLI 학습·평가 연결 준비 — 14:47 KST 기록

native NLI를 기존 freeze_training_cycle/train_local/전역3회 ledger에 연결했다. 봉인 자료·실제 사람 검수/목적 승인·계열/중복·알려진 학습 노출·실제 OS 접근을 다시 확인하고 train/validation만 학습 파일로 변환한다. 진단 정답은 학습 파일에 넣지 않는다. 실제 완료된 학습 ledger와 같은 동결 주기를 요구하는 후보 검증셋 평가/조건 일치 비교 도구도 준비했다. 검수 CLI는 전체892건의 이어서 검수·반려·진행 집계를 지원한다. [사용자 실행 안내](NEXT_ACTIONS.md)를 따른다.

전체88 tests/compileall/pip check/기존 비교 PASS, 봉인 패킷16 tests PASS. 실제 캐시 CPU tokenizer로 train300/validation150의 전체 길이·추론 prefix를 검사해 모두≤768(최대255/240) 확인했다. 실제 미검수450건/노출 이력 확인 누락에서는 동결 출력·학습 예산 사용 없이 exit2다. 현재 세션의 새 평가는 검수150건 누락/서버 모델 점유와 다른 계정 probe 인증 부재로 모델 로드 전 차단됐다. 이는 아래 root에서 검증한 OS PASS를 취소하는 결과가 아니며 실행 시점의 실제 probe 권한도 요구한다는 뜻이다.

격리 서비스 UID499에서도 기존 합성12요청을 실제 실행해9완료/3개429, 인증401/타인404/CSRF403, 실제 MLX/MCP9호출을 확인했다. 짧은 기능 부하이며 지속 용량/새 자료 품질 평가가 아니다. 근거 outputs/runs/20261020T143802+0900-next-actions/. 사람 검수0/새 자료 재평가0/새 학습0/3/A~F0/6 유지. 실제 판례 RAG·비공개 최종셋·분리 배포의 백업/삭제복구 재검증·보존기간은 후속 조건이다. 아래 이전 단계 기록의 'native NLI 연결 전' 상태는 이 준비로 대체한다.

## OS 정답 격리 완료 — 14:43 KST

사용자 터미널에서 전용 계정 생성/전환을 실행한 뒤 중단됐던 설정을 복구했다. root 소유 모델 잠금 디렉터리가 umask077 때문에0700이 된 원인을 수정해0755로 제한적으로 바로잡았다. 현재 실제 서비스는 _recase_service UID499/PID41133, 평가자는beshu UID501이다. 별도 암호화 볼륨의 실제 정답7개에서 평가자 읽기/해시 일치와 서비스EACCES를 확인했고 작업 폴더의 정답 사본·키4경로도 접근 거부했다. 기존 Qwen3-4B/어댑터56개와 ready=true, 원본14개 해시, 원래 checkout과 공유하는 잠긴 model.lock inode를 확인했다. OS PASS는 검사한 파일/경로/시점에 한정한다.

근거는 [실제 root 검증 결과](../outputs/runs/20261020T134803+0900-isolation-review-0385fc/finish-20261020T144251-f1772e/result.json), [독립 사후 대조](../outputs/runs/20261020T144223+0900-finish-isolation-d3c15a/post-cutover-verification.json). 전체 backend83 tests PASS. 서비스DB/삭제 journal은 /Users/Shared/RECASE-isolated-0385fc/state/가 현재 경로이며 원래 runtime/DB는 전환 당시 자료다. 아래 미완료 OS 기록은 이전 시도의 이력이다. 분리 배포의 백업·삭제/복구 정책 재검증은 NOT_RUN이며 기존 UID501 운영 시험을 새 계정에 일반화하지 않는다. 준비한892건의 사람 검수0건, 새 자료 모델 재평가/새 학습 NOT_RUN은 유지한다.

## 추가 공개 데이터·검수·격리 준비 — 이전 기록

공개 KLUE NLI27,998건·LBOX 요약20,000건·KoBLEX QA226건을 수집해 총48,224건을 격리 보관했다. KoBLEX 참고 법령233,544개는 텍스트 조각이며 독립 정답 사례 수에 합산하지 않는다. 출판자 파일13개와 기존 산출물14개의 해시를 보존했다. 실제 법원 API 반입이나 서비스/RAG 연결을 완료한 상태가 아니다.

준비한892건의 자동 검사는 NLI 주석자 불일치140건과 시계 검교정 시나리오 문구 모호성3건을 사람 우선 검수 대상으로 표시했다. 사용자가 검수 담당을 수락했으나 실제 사람 검수·목적별 승인 기록은0건이다. 정답7개를 별도 AES-256 암호화 APFS 이미지에 복사하고 해시를 확인했다. 관리자 인증 요청이300초에 시간 초과돼 서비스 계정은 생성되지 않았고 서비스/평가자는 여전히 UID501이다. 실제 서비스 계정 접근 거부는 NOT_RUN이며 OS 격리는 BLOCKED다.

14:28–14:31 KST 사용자 요청으로 재인증했다. 이번에는 관리자 명령 실행 단계에 도달했으나 Python이 Downloads의 helper 파일을 여는 단계에서 errno1/Operation not permitted로 종료됐다. macOS 개인정보 보호 경계로 추정되며 계정 생성/서버 전환 코드는 시작되지 않았다. 터미널 앱 자동 조작도 도구의 안전 제한으로 거부돼 사용자 본인의 기존 터미널에서 준비된 sudo 명령을 실행하도록 안내했다. 근거: 같은 run의 administrator-attempt-2-execution.json/diagnostic.json. 기존 UID501 서버를 유지하며 새 자료 재평가·학습은 NOT_RUN이다.

backend66 tests와 준비 패킷16 tests PASS. 현재 서비스UID501로 보호 정답7개를 모두 읽을 수 있음을 실제 확인했다. 새 자료의 모델 재평가·새 학습은 NOT_RUN, 후보 사용0/3이다. native NLI 학습은 기존 동결/3회 ledger에 계약을 연결한 후에만 실행한다. 상세 절차·실측·현재 차단 사유는 [검수·격리 안내](../outputs/runs/20261020T134803+0900-isolation-review-0385fc/START_HERE.txt), [상태](../outputs/runs/20261020T134803+0900-isolation-review-0385fc/STATUS-final.json)를 따른다. 아래 초기 기록의 실제 판결문0건은 당시 법원 반입/운영 승인 범위이며 이번 공개 벤치마크 수집과 구분한다.

## 후속 현황

목표는 사용자 지정 **이 Mac의 로컬 전용**이다. 기존360건 노출 등록/신규 독립 분할 제외, 신규12건 검수 대기 v2, 해시 결합 목적별 검수·철회/중복·계열·노출 감사, 실제 OS 접근 verifier, 최대3회 학습 gate와 A~F 비교 검사를 추가했다. 실제 사람 검수0건·새 학습0/3·A~F0/6이며 OS 정답 읽기 거부는 실패했다.

개인 접근키/브라우저 세션 인증, 실제 MLX 동시12요청의9완료/3제한, 합성 DB 삭제/복구 재적용을 확인했다. clean venv 최종57 tests PASS. 원본14개 해시 유지. 상세 판정과 증거는 [NEXT_PHASE_REPORT](NEXT_PHASE_REPORT.md), 절차는 [NEXT_PHASE_PROTOCOL](NEXT_PHASE_PROTOCOL.md)이다.

## 완료한 초기 범위

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
| 12 회귀 | PASS 범위 제한 | 자동57개 + 실제 모델/fixture 브라우저 별도. 광범위 보안 보증 아님 |
| 13 최종 비교 | BLOCKED | 개발 A/B만 실행, 독립 최종 평가/전체 A~F는 미실행 |
| 14 운영 | LOCAL_VALIDATED | 개인 로컬 인증·UID499 제한 부하·검사 경로 OS 격리·운영 백업/복사본 삭제복구 PASS. 자료 검수·실제 자료 보존/폐기·지속 부하는 미완료, 공개는 범위 밖 |

## 실행 상태와 다음 작업

로컬 서버는 localhost:8100(127.0.0.1 bind), 실제 MLX/기존 어댑터와 개인 접근키 인증으로 실행한다. runtime/personal-auth/key.txt의 키로 로그인한다. 사용자는 브라우저에서 새 합성 데모를 시작할 수 있다. 현재 격리 배포의 중단/기동은 OPERATIONS의 launchctl 절차를 따르며 `make serve`를 추가 실행하지 않는다. 검증은 `make check`. 모델 평가/학습 전 서버를 중단해야 한다.

다음 우선순위는 검수된 독립 사건/시나리오·문서 계열 데이터와 목적별 승인/사람 검수, OS 수준 평가 정답 격리다. 이를 확보하기 전 새 학습/실제 판례 RAG/최종 성능/공개 운영 승격을 진행하지 않는다. 유료 호출·공개 배포·원문 외부 전송0건.

세부 명령/증거/제약은 EXECUTION_CHECKLIST, EVALUATION_REPORT, ISSUES, HANDOFF를 참조한다.

## 폴더 구조

프론트 소스/로그인 화면/브라우저 E2E는 frontend/, Python 앱·도구·학습·평가·테스트·requirements는 backend/로 분리했다. 공유 data/outputs/runtime/.venv는 루트에 유지한다. 실행은 기존 make serve/make check를 사용하며 현재 경로는 STRUCTURE.md를 따른다. 이전 실행 기록의 옛 파일 경로는 당시 기록이다.
