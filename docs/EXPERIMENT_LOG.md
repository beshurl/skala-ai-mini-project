# 실험 기록

## 2026-10-20 KST — 재현 비교 계획

- 변경 원인군: 평가기 신뢰성/조건 식별 및 일관성. 모델·학습 데이터·어댑터는 보존.
- 평가 프로토콜: EVALUATION_PROTOCOL.md v2. 기존 54건 개발 평가 전체.
- 후보: 기존 Base 4B와 기존 100 iteration LoRA. 새 학습 후보 0/3.
- 생성: 동일 snapshot, greedy, thinking off, seed 0, 최대 256 tokens. 원시/복구 결과 구분.
- 호출 전 예상 시간 3~10분. OOM·과도한 메모리 압박·불안정시 중단하고 실패를 보존.
- 기존 15건 로그는 revision·생성 설정이 없어 UNVERIFIED. 기존 점수 재계산과 새 모델 평가는 분리.

### 재시도 1 — 캐시 부가 파일 검사

- 증상: `outputs/runs/20261020-base-v2` 생성 후 모델 로딩 전 exit 1. HF Hub가 README/.gitattributes 누락으로 오프라인 snapshot 전체를 거부.
- 원인 확인: config/tokenizer/weight 파일은 존재하며 문서 2개만 누락. 모델 자체 손상이 아님.
- 수정: snapshot_download allow_patterns를 모델 실행 파일 확장자로 제한. 다운로드·캐시 삭제 없음.
- 예상/판정: 기존 캐시로 모델 로딩 성공, 모든 54건 예측 저장. 추가 비용 0, 재학습 0. 동일 원인 수정 예산 1/2 사용.

## 추가 사용자 기록 수신 — 기존 실험 확인 범위 갱신

2026-10-20 KST에 사용자 제공 터미널 기록을 참고용으로 수신했다. 명령을 재실행하지 않았다.

- Base와 FT 모두 `--model mlx-community/Qwen3-4B-4bit`를 명시했다. 기존 실행이 0.6B였다는 근거는 없으며, 평가 코드의 잘못된 기본값과 실제 실행을 구분한다.
- `ITERS=100` 학습 완료 출력, LoRA 8 layers/rank 8, 학습 가능 3.670M/4022.468M 파라미터가 기록되어 있다.
- 검증 손실은 iter 1에서 3.108, iter 100에서 화면 표시값 0.000이다. 반올림된 출력이며 원시 손실이 정확히 0이라는 뜻이 아니다.
- 기존 15건 Base/FT 수치가 파일과 일치한다. 저장소 revision과 원시 손실 로그는 여전히 불명확하며 일반화 분할의 누수 문제는 별도로 남는다.
- 기록은 기존 수행 증거로 사용하고, 설치/데이터 생성/학습을 다시 실행하는 지시로 취급하지 않는다.

## 고정54건 실행 결과

Base run20261020-base-v2-retry1와 FT run20261020-ft-v2. 동일 dataset bytes hash/sample ID/revision/system/tokenizer/greedy/seed0/thinking off/max256을 compare.py로 확인했다. 각각54/54 EOS stop, runtime 실패0, 누락0. FT는56 LoRA 모듈과 실제 adapter_loaded=true.

- 원시 계약 성공률 Base0%, FT100%. 계약 기준 accuracy/F1 0/1.
- 평균 생성 지연2.919159/1.363288초. p95 4.028731/1.548652초. 모델 호출각54회.
- 입력 토큰각7642, 출력6839/2697. MLX peak allocated2.592801/2.804819GB.
- 명세 후 설정/프롬프트/어댑터를 점수에 맞춰 바꾸지 않았다. 새 학습0회. 계약 오류 해석용 label-only 사후 진단은 별도 파일에 보존하며 선택 지표를 바꾸지 않았다.
- 데이터 중복을 이유로 일반화/최종 평가 주장은 기각한다. 고유 prompt가 train↔test9개 겹치며 test18/54건이 train에서 본 prompt다.3개 템플릿 계열도 모두 겹친다.

결정: 기존 FT는 합성 로컬 데모에 한해 재사용. 독립 검수 데이터와 최종 평가, 참고 판례 코퍼스, 실사용 모델 승격은 BLOCKED. 벡터/Hybrid/앙상블/다중 모델 탐색을 추가하지 않는다.

## 애플리케이션 검증(모델 성능 비교와 분리)

현재 사건 keyword 검색 + 실제 MCP + LangGraph + 기존 FT의 새 합성 데모를304/1265px CUA 브라우저에서 실행했다. v1 식별 부족 판단 보류, v2 본인 확인 후 충돌, v3 무관 증거에서 유지, 원문 인용과 양쪽 비교를 통과했다. 이는 다른 데이터/프롬프트의 통합 검증이며 위 A/B의 RAG·Agent 순수 효과 실험이 아니다.

오류/취소/부분 완료/미준비 UI는 명시적 fixture 서버에서 별도로 검증했다. clean locked environment에서는41개 자동 테스트와 실제 Metal 추론1건을 확인했다. 실패/검토 한계는 EVALUATION_REPORT/ISSUES에 남겼다.

## 후속 독립 데이터/실험 통제 주기

주기 post-legacy-independent-v1, 새 학습0/3, 실제 A~F0/6. 기존 학습/평가를 재학습 명령으로 재실행하지 않았다. 신규 v2의12개 제안 정답은 사람 검수 전 채택하지 않으며 작성/열람 노출 이력을 남겼다. 기존360건도 새 독립셋으로 재명명하지 않았다.

최초 자료 표기 [E1]→E1: 및 명시적 evidence 수정1회. v1/첫 실패를 보존했다. 최종 audit는 구조 계약 오류0이지만 실제 검수/노출 범위/최종셋/OS 분리 미충족으로 BLOCKED. freeze와 A~F 비교는 예상 exit2를 기록했고 모델 학습 호출/예산 예약은0이다.

실제 모델 호출은 합성 로컬 앱/인증/제한 부하 검증에 사용했으며 새로운 모델 성능 비교나 A~F 결과로 섞지 않았다. 모델 revision·기존 adapter·greedy/seed0/thinking off는 그대로다. 부하 지연 집계 오류는 같은9개 SQLite 작업에서 재계산했으며 모델을 반복 호출하지 않았다. 실제 원시 결과와 정정 이유는 real-local-load-corrected.json에 있다.

판정: 기존 FT 개인 합성 데모 재사용 유지. 데이터/OS 권한 문제가 남아 새 학습·독립 최종 평가·실제 판례 RAG·파일럿 승격 보류. 다음 입력/절차는 NEXT_PHASE_PROTOCOL.md, 실제 증거는 NEXT_PHASE_REPORT.md.

## 프론트·백엔드 경로 분리

2026-10-20 KST. 소스만 frontend/backend로 구분했다. 기존 데이터·어댑터·평가 결과는 이동/변경하지 않았고 원본14개 해시를 재확인했다. 새 학습0/3, A~F0/6 유지. 경로 회귀 확인용 합성 서비스 분석1건(실제 MLX1호출)은 모델 성능 비교에 포함하지 않는다. 근거: outputs/runs/20261020-folder-split/validation/summary.json, runtime-smoke.json.

## 공개 자료 검수·OS 분리 준비 — 모델 실행 전

892건의 준비 패킷은 공개 개발 진단/학습 후보이며 비공개 독립 최종셋이 아니다. KLUE600건(학습300/검증150/진단150), LBOX 요약30건, KoBLEX QA226건, 에이전트 작성12계열/36공개버전 시나리오다. 자동 검사143건의 표시는 사람 라벨 검수 결과가 아니다. 실제 사람 승인0건, 자료 내용에 대한 새 모델 평가·새 학습 NOT_RUN, 후보 예산 사용0/3, A~F0/6 유지.

별도 암호화 볼륨의 실제 정답7개는 준비했으나 관리자 인증 시간 초과로 서비스/evaluator UID501이 같다. OS 정답 접근 거부는 NOT_RUN/BLOCKED. preflight는 해당 차단과 모델 잠금 점유를 모델 로딩 전에 거부했다. backend66/패킷16개 PASS는 소프트웨어 회귀이며 새 모델 성능이 아니다. native NLI 학습 계약은 main freeze_training_cycle/영속3회 ledger 연결 전 실행하지 않는다. 현재 후보 설정3개는 제안이며 검증셋 모델 선택 동결/실행 결과가 아니다. 근거: outputs/runs/20261020T134803+0900-isolation-review-0385fc/.

14:43 KST 후속: 서비스 계정을 실제 UID499로 전환하고 root 잠금 폴더 권한 오류/중단 상태를 복구했다. 실제 보호 정답7개와 workspace 정답/키4경로 접근 거부, 평가자UID501 읽기/해시, 같은4B/기존56 LoRA/ready=true를 확인했다. 서비스 기동만 했고 새 모델 추론/재평가/학습0이다. backend83 tests PASS는 소프트웨어 회귀다. 사람 검수0건/새 자료 재평가·새 학습 NOT_RUN/후보0/3/A~F0/6은 유지한다. root 결과 isolation run/finish-20261020T144251-f1772e/result.json 및 recovery run 20261020T144223+0900-finish-isolation-d3c15a/post-cutover-verification.json. OS PASS는 검사한 경로와 시점에 한정하며 전체 신규 데이터 승인이나 모델 선택 동결을 대신하지 않는다.


## 14:47 KST — native NLI 연결 준비, 실험 실행과 분리

기존 동결/전역3회 ledger에 native NLI 계약을 연결하고, 완료된 후보의 nli_validation 평가와 조건 일치 비교 경로를 추가했다. 실제 캐시 CPU tokenizer에서450건의 전체 길이/추론 prefix 검사만 수행했으며 새 자료 가중치 로드/재평가/학습은0이다. 실제 미검수450건과 이력 확인 누락을 이유로 동결 출력/후보 예약 없이 거부됐다. 후보 설정은 여전히 제안이고 모델 선택/어댑터 승격은 하지 않았다.

전체88 tests와 봉인16 tests는 소프트웨어 검증이다. UID499 격리 서버의 합성12요청/9완료/3개429/실제9호출은 운영 회귀이며 공개892건 평가 또는 A~F 성능값에 넣지 않는다. 근거: outputs/runs/20261020T143802+0900-next-actions/. 사람 검수0건·새 학습0/3·A~F0/6 유지.


## 격리 서비스 운영 복사본 검증 준비

2026-10-20 KST. 새96 tests와 실제 배포 Python/SQLite 모듈의 UID501 합성 DB 백업·복사본 삭제/복구만 실행했다. 모델 로드/추론/학습은0이며 성능 비교에 넣지 않는다. 실제 UID499/운영 state 검증은 관리자 계정 전환 인증 전 NOT_RUN이다. 준비/검수 도구의 통과를 실제 사람 검수로 계산하지 않는다. 사람 승인0·새 학습0/3·A~F0/6 유지. 근거 outputs/runs/20261020T145215+0900-isolated-operations/.

## 15:03–15:05 KST — 실제 UID499 운영 결과 확인, 새 모델 실험 없음

사용자 로컬 sudo 실행은15:03:11 KST/exit0/PASS이며 UID/EUID499로 운영 DB 읽기 전용 백업·새 합성 복사본 삭제/복구·최신 journal 보존·세션 폐기·무결성/백업 보존을 검증했다. 실제 결과는 operations run의 execution-4df356d4005c442992653e0cfc76fd09/result.json이다. 현재 PID41133/UID499/인증 ready/56 LoRA 및 계획/실행 코드/정책/공유 잠금 대조도 PASS했다. 이 검증의 모델 호출·학습·운영 삭제는0이며 품질 성능에 합산하지 않는다.

사람 검수는 validation1/150(대기149), 전체1/892다. native NLI 감사는 승인449건/노출 이력 확인 누락으로 BLOCKED이며 평가 preflight도 예상 exit2(149건 승인 누락·현재 계정 전환 인증 부재·서버 모델 점유), 모델 로드0이다. 새 학습0/3·A~F0/6/독립 최종셋 미확보 상태를 유지한다. 근거 outputs/runs/20261020T150521+0900-operations-confirmed-6923ae/의 verification.json/native-data-audit.json/validation-preflight.json/preflight-execution.json. 실제 정답/원문/승인 이력을 바꾸지 않았다.

## 2026-10-20T15:05:56.982122+09:00 — 공개 NLI150건의 gold-aware AI 데이터 검토

명시 사용자 승인으로 본 채팅 AI가 검증150건의 전제·가설·제안 라벨을 검토했다. 라벨 지지133/문맥 기준 재확인12/수정 후보5이며 모델 정확도가 아니다. 개인정보·인물 맥락 후보13/문구 품질7도 검수 완료 판정이 아니다. 승인자사용자/수행자AI/human_reviewed=false로 기록하고 기존 직접 승인1건을 보존했다. 개발 품질 검토 노출150건을 기록했으므로 blind 최종 자료로 사용하지 않는다. 원본 라벨/분모150/입력·정답 SHA는 그대로이며 로컬Qwen 모델 평가/학습·후보 예약0이다. 근거 outputs/runs/20261020T150037+0900-ai-semantic-review-4f0bf5/.

## 사용자 요청 AI 후속 검토 — 모델 실험 미실행

기존150건 검토의 source 결합/라벨/근거를 검증하고 쟁점17건만 재검토했다. 갱신 집계134지지/12문맥 판정/4수정 후보는 데이터 검토 분류이며 모델 정확도가 아니다. 기존133건 판단은 유지했다. 원본/라벨/분모150/사람 ledger 해시 동일, 새 사람 승인0, AI 검토 노출17건만 append해534→551기록/chain 검증. 후보 사용/학습/로컬 모델 추론·평가0이다. 결과 outputs/runs/20261020T151035+0900-ai-review-followup-95bc0c/의 summary.json/verification.json/exposure-registration.json. 수정 후보는 확정 오류로 취급하거나 자동 적용하지 않았다.

## 16건 처리 초안 — 새 모델 실험 없음

원본과 공식 라벨을 유지하며 RECASE strict 파생 초안150건을 작성했다. 기존 후보4+문맥7의 라벨 제안11과 사용자 선택의 별도 작성 문장5를 반영했다. 원본 대비 문장5/라벨12 차이이며 출판자 오류 확정이나 모델 정확도 값이 아니다. 사용자 문구 선택0대기, 새 최종 사람 승인0, source family는 그대로라 신규 독립 최종 사례로 계산하지 않는다. 개발 작성 노출5건 append 후556기록/prefix·chain 검증. 실제 새 봉인 패킷 load_packet PASS, actual preflight 예상 exit2(미검수150/새 정답 OS proof 부재/모델 점유)/모델 로드0. 평가·학습·후보 예약0. 근거 outputs/runs/20261020T153504+0900-nli-disposition-draft-f94ac8/의 wording-applied-summary.json/review-packet-verification.json/revised-preflight-execution.json.

## 2026-10-20 — 지속 시험 실패·새 패킷 준비, 새 모델 품질 실험 없음

사전 계획 soak-plan.json: 실제 UID499/PID41133/기존 MLX·LoRA,600초/10초 간격/직렬최대60/작업30초. 첫 자체 합성 요청이30초 내 미완료라32.566초에 exit2/FAIL로 중단했다. 완료0·추가 제출0, 자체 취소HTTP200/최종 상태 미확인이다. 진행 중 모델 호출 총수는 NOT_MEASURED, 원인 UNDETERMINED. 스왑 관측을 인과로 단정하지 않고 생성/재시작 재시도를 반복하지 않았다. live-soak.json/해석 보완 JSON을 모두 보존했다. 장시간 안정성 PASS나 새 자료 모델 정확도 결과가 아니다.

사용자 선택 검증150건을 native600건 패킷에 연결했으나 실제 freeze는 미검수450/이력 누락으로 exit2·주기 생성0·학습0/3이다. Recall/MRR/인용 구간 계산기는 합성 시험으로 검증했으며 실제 승인 판례 성능은 NOT_MEASURED다. 독립 최종/A~F 비교는 NOT_RUN이다. 사용자 사건90일·백업30일은 운영 정책 값이며 모델 실험/사람 라벨 승인으로 해석하지 않았다. 전체 근거 outputs/runs/20261020T155158+0900-remaining-work-b82291/.

## 2026-10-20 — 보존정책 기반 검증, 실제 모델 실험 없음

새 합성 DB의 schema1→2 명시적 backup/migration·종료/보류·90/30일 만료 미리보기·백업 생성/복구 receipt·최신 journal proof를 실제 CLI16개/전체139 tests로 검증했다. 최초 백업 바이트 동일 가정 실패는 원본 불변/논리 내용·스키마 동등/백업 자체 SHA 검사로1회 복구했고 처음 실패를 보존했다. 최신 tombstone1건은 새 복구 사본에만 재적용, 원source/백업/receipt/journal SHA 보존. 실제 UID499 적용/모델 추가 적재·새 요청/학습0, 독립 최종/A~F 미실행. 이전 지연 작업의 전체 호출은 NOT_MEASURED다. run 20261020T161845+0900-retention-lifecycle-10ab30을 따른다.


## 2026-10-20 KST — 공개 NLI 위임 검토, 실제 학습은 관리자 인증 대기

사용자가 공개 NLI450건에 한한 AI 위임 검토 조건을 직접 허용했다. 사람 승인 수를 바꾸지 않고 학습262/검증139를 봉인,49건 격리/원본450 보존/이번 라벨 변경0이다. 공개·gold-aware 개발 검토이며 새 독립 최종셋으로 계산하지 않는다. 원556개 노출 prefix를 보존해 새 열람328개만 append/총884개 chain 확인, 외부·사전학습 노출은 UNKNOWN이다.

최종 실제 데이터 감사와 비변경 실행 계획은 PASS다.153 tests 등은 소프트웨어 검증이며 NLI 정확도가 아니다. 새 실제 정답3개에 대한 계정 전환 인증이 없어 실제 freeze는 OS gate에서 예상 exit2/출력0·모델 로드0·학습0/3이다. 설정은 같은 Qwen3-4B 4-bit revision/기존 선언 최대3후보/같은 scorer·greedy seed0 thinking off다. 원래 어댑터/기존 평가 보존, 새 학습 어댑터의 생성 설정 원본과 가중치를 보존하는 모델 ID 연결만 보완했다.

인증된 사용자 터미널 실행기는 기본 모델 검증→후보c1 한 개 학습→같은139 검증→조건 일치 비교를 준비했으며 실제 결과는 아직 NOT_RUN이다. 이 비교는 공개 NLI용이며 서비스 A~F/실제 미제사건 성능을 대신하지 않는다. 자동 승격0/유료·공개 배포·실제 판결문 외부 전송0. docs/DELEGATED_NLI_REVIEW.md와 해당 run의 명령·시각·exit code를 따른다.


## 2026-10-20 — lifecycle UI·후보 사본 검증, 새 모델 실험 없음

run 20261020T164135+0900-lifecycle-ui-9152c8. backend153/frontend12 tests와 실제 fixture1265×720 브라우저·새115파일 후보 사본의 stdio MCP/SSE/lifecycle를 확인했다. 기존 venv 재사용이며 실제 MLX·UID499 새 배포·새 자료 모델 평가/학습은0이다. 현재 공개 NLI 위임 데이터의262/139·49격리/노출884 상태를 보존했고 사람승인 생성0·전역후보0/3, 독립최종/A~F NOT_RUN이다. 합성 fixture 판단/사용량을 모델 성능·실제 운영 지연 개선으로 계산하지 않는다. 실제 서비스PID41133/UID499/공유잠금은 보존했고 기존 지연 작업 총호출 NOT_MEASURED/원인 미확정이다. 자동90/30일 삭제/스케줄러·백업/키폐기0. 상세명령/시각/종료코드와 과도한 일반화 금지는 RESULT/CURRENT_STATUS/validation-final/candidate-smoke-execution/preservation-verification을 따른다.


## 2026-10-20 — 암호화 백업 검증, 새 모델 실험 없음

run 20261020T170913+0900-encrypted-backups-0d84fb의 새 합성 DB/키/독립 journal만 사용해 CLI13개와 새 v4 정책 미리보기1개, 전체164 tests를 실행했다. AES-GCM 인증 실패/키 부재는 평문 복구 전 거부, 최신 공급 journal/세션 폐기·작업 복구/보류·stale proof·원본/암호문/키 보존을 확인했다. UID501 사본이며 실제 UID499/모델 호출·학습·운영 백업/삭제·키 폐기0. 키 이름 복원은 완전 폐기 증명이 아니고2035시각은 미래 합성 미리보기만이다. NLI262/139·49격리/노출884·후보0/3·독립최종/A~F NOT_RUN을 유지한다. 이전 지연작업 총호출 NOT_MEASURED·원인 미확정. 실제 모델 성능/완전폐기/실제 운영 안정성 결과로 계산하지 않는다. 상세명령·UTC시각·종료코드·최종코드SHA는 해당 run의 validation-final/cli-executions/new-policy-preview-execution을 따른다.


## 2026-10-20 — 이메일·비밀번호 로그인과 인증 구조 정리

- 명시 사용자 요청 범위로 이메일·비밀번호 가입/로그인/로그아웃·계정별 영속 사건 소유권·공통 운영자 role 인증을 구현했다. accounts/auth_api/auth.ts/AuthView/TTY accounts CLI로 책임을 나누고 scrypt·일반 가입 user 고정·세션/CSRF·서버 역할 재확인·시도 제한을 적용했다. 오류 입력이 비밀번호를 반사하지 않는다.
- 기존 접근키 Python/CLI/테스트, 독립 로그인 HTML/CSS/원본CSS/생성기7파일과 활성 Basic/무인증 데모·중복 관리자 인증을 제거했다. 삭제 전 source-before와 파일 SHA 보존. 기존 운영 키/DB/데이터/모델·평가 산출물·실제로 사용하는 Store 합성 운영 fixture는 보존했다. 역사적 문서는 현재 인증 안내를 덧붙이고 당시 검증을 재작성하지 않았다.
- 실제 전체 backend178 tests PASS(09:19:46~09:20:19 UTC), 최종 frontend14/typecheck/build/compileall/pip check/diff exit0. 명령/시각/종료코드는 run/*-verified.json 및 *-delivery.json, 로그에 기록했다. 브라우저는 FixtureModel이며 가입/확인 불일치/잘못된 암호/로그아웃/서버 재시작 후 재로그인 같은 사건·3개 분석 보존/권한 차단·보호 링크 복귀를 확인했다. 실제 공개 증거 v1→v2→v3 분석/인용/비교 E2E PASS. 순수 query 변경 후 로그인 복귀 링크가 남던 결함은 반응형 query와 회귀2 tests로 수정했다. 로그인에서 메인 이동 시 제목 복원도 확인했다.
- 브라우저320/390px의 폼 가로 넘침0·데스크톱 배치 확인/스크린샷 보존. VoiceOver/교차 브라우저/실제 UID499·부하·계정 DB 운영 복구는 NOT_RUN이다. 독립 에이전트 검토는 실행하지 않았다.
- 기존8123 모의 서버의 활성0/대기0/fixture를 읽기 전용 요약으로 확인 후 PID54540만 정상 종료했다. 첫 확인 스크립트는 model.backend를 최상위에서 찾는 오류로 거부됐고 변경0, 진단 기록 후 수정1회로 PASS했다. 최종8123은 새 사건/계정 DB·독립 journal·기본 frontend/dist를 사용한다. 공용 암호/기본 관리자/테스트 계정0이다. 기존 미리보기 DB를 덮어쓰거나 임의 계정에 기록을 자동 이전하지 않았다. 테스트 전용8124는 검증 후 종료한다.
- 기존 데이터/어댑터/평가15개 SHA·원 제공 이미지12개·노출884 SHA/chain·활성 수동 정책·공유 model.lock inode25076574 보존. 실제 UID499 PID41133/worker41754는 변경/중단하지 않았고 추가 MLX 로드/추론/학습0이다. 유료/공개/판결문 외부 전송/운영 삭제0. 계정 DB까지 포함한 운영 이전·암호화 백업/복구·코드 복귀는 별도 통합 검증이며119파일 후보는 현재 인증 배포본이 아니다. LOCAL_VALIDATED 유지.

근거: outputs/runs/20261020T175323+0900-account-login-127a6e/RESULT.txt, backend-verified.json/log, frontend-delivery.json/log, browser-auth-validation.json, browser-case-flow.json, completion-verification.json.


## 2026-10-21 — 계정 통합·암호화 pair, 실제 모델 실험 없음

run 20261021T090314+0900-account-integration-6a7cb0. 최신 backend195/frontend14 및 최종123파일 후보의 TestClient/FixtureModel/실제 stdio MCP/HTTP·SSE·v1/v2·현재 비밀번호/권한/비활성/소유권·최신 삭제 journal/종료/보류·복구 후 로그인/프로세스 재시작/새 기록 유지13항목 PASS. CLI6개 중 의도한 구 접근키/오래된 사건 사본 거부2개 포함이다. 최초193/121 후보·practice 데이터 누락으로 거부된 v2를 보존하고 AEAD receipt 교체 회귀·practice 공개 합성 입력1개를 결합한 v3로 검증했다. 검수 참고 정답은 서비스 묶음에 포함하지 않았다.

이 결과는 소프트웨어·새 합성 사본 검증이며 모델 정확도/실제 사건 성능·운영 UID499·MLX/부하 결과가 아니다. NLI 비변경 계획은 PASS지만 모델 로드·실제 학습0/3, 독립 최종/A~F NOT_RUN·승인 판례/검색 정답 없음이다. 계정 이미지는 암호화 보존만 하며 과거 자격정보 자동 복원·완전 폐기0. 실제 UID499 서비스/DB/원래 잠금·원본15개·노출884/수동 정책 보존, 관리자 읽기 전용 진단은 sudo 인증 대기다. 실제 UID499 복귀 후보·기존 사건 소유권 연결·계정 DB 소실 시 재발급 복구·자동 보존/스케줄러·모든 평문/키 사본 폐기·실제 접근성은 남는다. 실제 모델 추가 요청/유료/공개/원문 외부 전송0, LOCAL_VALIDATED 유지. 상세 근거는 RESULT/CURRENT_STATUS·backend-final-v2/other-validation-v3·rehearsal-v3·preservation-verification-final이다.


## 2026-10-21 — 미제사건 대응 설명과 사용자 테스트 자료 준비

- 사용자 요청으로 현재 가능한 자료 대조/불충분/충돌/검색·형식 실패/반대 증거 수정의 차이, 누락 정보·다음 확인·재검토 조건을 설명했다. NIJ/NIST 공식 일반 문헌만 검색했고 실제 사건 원문·개인정보를 반입/전송하지 않았다. 현재 그래프의 장소/날짜·신원 전제/주장당2자료·검색5건·빈 가설 목록과 고급 추론 미지원도 명시했다.
- 새로운 가상12사건/48증거/36단계 입력과 AI 제안 기준을 분리 작성했다. P01~03만 현재 그래프에 연결, 나머지9개/27단계는 수동 검토용이다. 시간 오차·동명이인·감정 충돌·정정·기록 부재·출처 중복·물품 동일성·문서 지시문·승인 철회를 포함한다. 실제 범인/해결 정답을 만들지 않았으며 모든 사건 상태는 UNRESOLVED다. 사람 검수/학습 적격/독립 최종셋으로 표시하지 않았다.
- practice.py/계정·CSRF POST /api/practice와 UI ‘테스트 사건3개 추가’. 결정적 소유자별 ID로 재호출 중복·기존 증거/분석 초기화를 막고 새 자료는 기존 공개 경계 뒤에 둔다. 입력 원문만 service에 읽히며 reviewer 제안은 모델/브라우저 API에 넣지 않았다. release에는 이 모듈과 입력 JSON을 함께 요구하고 제안 기준 경로는 거부한다. 원래 graph/testing/model은 수정하지 않았다. SPA가 사건 제목을 일반 제목으로 덮던 별도 결함도 제한적으로 수정하고 실제 최종 빌드에서 확인했다.
- 68개 파일의 최종 ZIP을 새 경로 RECASE-test-kit.zip에 만들었다. 사건별12·증거별48파일/36개 snapshot/검토 참고표/빈 결과지·해시/노출 기록을 포함한다. snapshot은 공개된 증거만, 템플릿36단계는 전부 NOT_RUN, 수동 모델 평가27단계는 NOT_RUN이다. 기존 NLI 노출 ledger는 변경하지 않았다. 초안 요약의 조사 오류를 수정한 뒤 최종 입력 SHA를 다시 봉인하고 초안 ZIP은 보존했다.
- 첫 테스트 collection은 tests.account_helpers import를 잘못 적어 exit2로 실패, 실제 서비스/모델 변경0 후1회 수정했다. 다음 기능검사는 P03 v1의 정상 RETRIEVAL_INSUFFICIENT/PARTIAL을 전부 COMPLETED로 가정해 실패했다. 진단 후 P03 v1/v2만 PARTIAL+해당 limitation을 엄격 확인하도록 수정했다. 제안 관계 라벨/증거/모델을 통과 결과에 맞춰 바꾸지 않았다. 실패 로그/진단과 새 명령·시각·exit을 보존했다.
- 최종 전체 backend194 tests PASS(40.36초), frontend14·typecheck/build/compileall/pip check exit0. 고정 fixture9단계는 COMPLETED7/PARTIAL2 포함으로 검증하며 모델 정확도라고 계산하지 않는다. 실제 IAB P01 3단계/공개 경계/인용·변경·유지 비교·P03 부분 완료·반복 seed/재시작 후 이력,320/390px 넘침0·데스크톱 QA PASS. 독립 에이전트 검토는 사이드 대화 제한으로 실행하지 않고 같은 에이전트가 직접 검토했다. VoiceOver/다른 브라우저/실제MLX는 NOT_RUN이다.
- 기존8123 UID501 fixture PID57830·활성0 확인 후 해당 미리보기만 정상 재기동, 같은 사건/계정 DB 관계형 내용 SHA 동일/기본 계정 생성0. 원래 UID499 PID41133/worker41754·공유 model.lock inode25076574/점유·원본15개/이미지12개/노출884 chain·SHA 보존을 확인했다. 실제 서비스·MLX 호출/학습/사람 승인·운영 삭제·유료/공개/실제 원문 전송0이다. 이전 계정 통합 배포 후보는 당시 근거로 보존하며 이번 데이터 의존성 재포함·실제 UID499 검증은 별도다. LOCAL_VALIDATED 유지.

근거: outputs/runs/20261021T090257+0900-user-test-kit-47fdda/RESULT.txt, *-delivery.json/log, kit-export.json, final-input-freeze.json, browser-practice-flow.json, browser-practice-review.json, browser-delivery-build.json, completion-verification.json.


## 2026-10-21 — 계정 소실 복구 CLI, 모델 추론 기능 검증과 구분

run 20261021T091557+0900-account-recovery-110ad4. 최신 backend204 tests·125파일 후보의 CLI/합성 PTY11항목/6명령·FixtureModel/stdio MCP 복구 사본 PASS. WAL 계정 이미지는 known rows로 새 메모리SQLite에 재생성하며 원 헤더 패치/과거 평문 이미지 작성0이다. 새 격리 DB 전 계정 비활성/user/새 verifier·9001→사용자 TTY 소유권/새 암호→보류 유지 확인 seal 후 schema1. 과거 암호/역할 복원·실제 사람 소유권 승인/운영 UID499 적용0이다. 행동 intent/완료·외부 변경/미완료 작업/교체 파일은 보수적으로 거부한다.

원본15개·노출884·수동 정책·실제 PID/공유 잠금 보존, 모델 로드/추가 요청/학습0/3·유료/공개/원문 전송·자동 삭제/키 폐기0. 독립 최종/승인 판례/A~F·실제 UID499 복구/부하/정답 OS는 미실행이다. 사용자 질문으로 일반 추론은 graph.py의 제한된 방문 대조/빈 가설로 아직 NOT_IMPLEMENTED임을 재확인했고 다음 구현 우선순위로 기록했다. 계정 회귀/합성 CLI 성공을 일반 추론/실제 모델 성능으로 일반화하지 않는다. 근거는 RESULT/CURRENT_STATUS, backend-final-v2, rehearsal-v2/cli-rehearsal-commands/result, preservation-verification이다.


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
