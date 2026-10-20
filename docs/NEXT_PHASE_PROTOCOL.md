# 독립 데이터·로컬 운영 후속 프로토콜

2026-10-20 KST. 사용자가 목표 환경을 **이 Mac의 로컬 전용**으로 지정했다. 공개 배포/유료 호출/원문 외부 전송은 승인 전 금지다. 기존 EVALUATION_PROTOCOL v2와 노출된54건 결과는 역사적 개발 비교로 보존한다.

## 현재 판정

- 기존360건: 과거 학습/검증/개발 평가 이력을 등록했으며 기존 파일을 수정하지 않았다. 세 템플릿 반복과 분할 중복은 해결된 독립 데이터로 승격하지 않는다.
- 새12건/12계열(v2): 서로 다른 날짜 경계, 시계 오차, 최소 이동시간, 경로 미상, 동명이인, 관측 누락, 문서 정정, 한정된 진술, 판례 역할, 출처 충돌, 증거 속 지시문, 시간대 변환을 다루는 **에이전트 작성 검수 대기 자료**다. 정답은 제안이며 사람의 검수 완료가 아니다. 개발 작성 노출 이력을 남겼으므로 블라인드 최종셋으로 사용하지 않는다.
- 검수 완료 독립 학습/검증/최종 자료:0건. 실제 판결문:0건. 사람 승인 기록:0건. 새 학습:0/3. A~F 실제 비교:모두 NOT_RUN.
- OS 실측: 현재 서비스/evaluator 모두beshu(UID501), 같은 볼륨. 실제 기존 정답 파일을 서비스 UID가 읽을 수 있다. **BLOCKED**이며 파일권한 분리를 통과했다고 보고하지 않는다. 관리자 비대화식 실행은 password required로 거부됐다.
- 로컬 접근키 인증, 실제 MLX 제한 부하, 합성 DB 삭제/복구 흐름은 별도 검증한다. 이 결과가 데이터 품질·OS 격리·파일럿 승격을 대신하지 않는다.

## 데이터 기록과 승인

`backend/recase/ledger.py`는 mode0600, 현재 소유자, 심볼릭 링크 거부, 파일 잠금, sequence/이전 해시/현재 해시, fsync를 적용한다. 같은 UID의 악의적인 전체 재작성까지 막는 신뢰 경계는 아니다. 서비스 계정과 검수자 계정을 분리해야 한다.

`dataset_control.py register-legacy`는 원본 파일 해시+행 위치+이용 목적을 키로360건의 노출을 등록한다. 재실행은 중복 등록하지 않는다. 노출 서명은 prompt 원문/정답을 포함하지 않고 해시·해시된 문자3-gram·계열 ID를 보관한다. 서명도 보호 대상 메타데이터다.

감사는 정확/정규화 중복, 숫자 변경 템플릿, 문자3-gram Jaccard≥0.82의 유사 후보를 검사한다. 사건/문서/시나리오/템플릿 계열의 연결 성분을 구하고 분할 간 연결을 차단한다. 학습 노출과 겹친 검증 자료, 과거 어떤 목적에든 노출된 최종 자료를 차단한다. 어휘가 다른 의미 중복 탐지는 보장하지 않으며 사람이 계열·의미·정답을 검수해야 한다. 누락 계열/잘못된 정답 계약/라벨 불일치/불완전 노출 이력도 차단한다.

실제 반입은 processing 권한과 rights_basis가 있어야 하며 출력은 계속 QUARANTINED다. 새 출력 폴더0700/파일0600을 요구한다. 실제 판결문의 processing/training/rag/display/redistribution 권한은 각각 독립이다. 자동 마스킹이 인명·주소·간접 식별자 검수를 대신하지 않는다.

검수는 로컬 대화형 터미널에서 자료 전체를 읽고 `직접 검수 완료`와 목적별 yes, 라벨 검수 여부, 근거를 입력하는 **사람의 확인 절차**다. 에이전트는 이를 실행하지 않았다. 기록은 현재 OS 사용자/UID/시간과 문서·라벨·권한을 포함한 전체 subject 해시에 묶인다. 수정본은 새 해시로 재검수해야 한다. `revoke`는 뒤의 승인 상태를 무효화한다. legacy human_reviewed=true 같은 불리언만으로는 통과하지 않는다. 이 로컬 확인은 공인 전자서명이나 독립 신원 인증이 아니다.

```bash
.venv/bin/python backend/scripts/dataset_control.py register-legacy --history outputs/runs/20261020-next-gates/exposures.jsonl
.venv/bin/python backend/scripts/dataset_control.py audit --candidates outputs/runs/20261020-next-gates/review-packet-v2/candidates.jsonl --history outputs/runs/20261020-next-gates/exposures.jsonl --reviews outputs/runs/20261020-next-gates/human-reviews.jsonl --out outputs/runs/NEW-audit.json
```

아래 명령은 실제 검수 담당자가 직접 수행한다. 코드를 실행하는 에이전트가 사람 검수로 입력하면 안 된다. 검수 후에도 candidate의 역할/계열/내용 변경은 새 자료로 기록하고 다시 검수한다. 최종 자료는 개발 작업자가 열람하지 않은 별도 묶음이 필요하다.

```bash
.venv/bin/python backend/scripts/dataset_control.py review --candidates PATH/candidates.jsonl --sample-id SAMPLE_ID --reviews PRIVATE/human-reviews.jsonl
.venv/bin/python backend/scripts/dataset_control.py attest-history --history PRIVATE/exposures.jsonl
.venv/bin/python backend/scripts/dataset_control.py revoke --subject-sha256 SUBJECT_HASH --reviews PRIVATE/human-reviews.jsonl
```

최초 review-packet은 근거 표기가 [E1]로 기존 E1: 계약과 달라 INVALIDATED했다. v2를 새 폴더에 생성했고 v1과 두 작성 노출을 보존했다. v2의 구조 계약은 통과하지만 사람 검수/이력/역할 게이트는 계속 BLOCKED다.

기존 반입 원본/정제 출력은 변경하거나 자동 승격하지 않는다. RAG는 승인 코퍼스를 실제로 연결하기 전까지 BLOCKED/빈 검색이다. 승인 절차 구현과 실제 데이터 승인 완료는 다르다.

## OS 계정과 보호 볼륨

현재 비대화식 sudo가 허용되지 않아 계정/볼륨 생성과 다른 UID 실행을 완료하지 않았다. 비밀번호를 명령/로그/채팅에 넣지 않는다. 다음 준비는 관리자가 macOS의 사용자 및 그룹·디스크 유틸리티에서 수행해야 한다.

1. 서비스와 평가/검수용 **서로 다른 표준 OS 사용자**를 준비한다. 서비스 사용자를 관리자나 평가 그룹에 넣지 않는다. 이름 예시 recase_service/recase_evaluator는 아직 생성되지 않았다.
2. 별도 암호화 APFS 볼륨을 준비하고 평가 사용자만 접근하게 한다. 실제 최종 정답과 그 복사본/백업은 이 보호 경계에 둔다. 서비스 checkout, DB, RAG, 프론트엔드, 모델 입력, 일반 로그에는 넣지 않는다. 같은 사용자 폴더를0700으로 바꾸는 것만으로 별도 사용자/볼륨 통과로 취급하지 않는다.
3. 모델/공개 입력은 서비스 계정의 별도 경로에 준비한다. Metal 실행과 코드/토크나이저 접근을 그 계정에서 확인한다. 평가 정답을 서비스에 복사해 해결하지 않는다.
4. 아래 verifier를 실행한다. 실제 정답 파일의 내용은 출력하지 않고 evaluator의 해시/실제 open과 서비스의 EACCES/EPERM을 확인한다. sudo 자체 실패, Python 실행 실패, 없는 파일은 접근 거부 PASS가 아니다. probe interpreter는 venv symlink의 실제 경로를 사용한다.

```bash
.venv/bin/python backend/scripts/verify_os_isolation.py --service-user recase_service --evaluator-user recase_evaluator --answers /Volumes/RECASE_EVAL/answers/final.jsonl --protected-root /Volumes/RECASE_EVAL/answers --service-pid SERVICE_PID --out PRIVATE/os-isolation.json
```

보호 루트/정답 소유자·권한, workspace와 다른 device, 다른 비root UID, evaluator 읽기, 실제 서비스 읽기 거부를 함께 확인한다. 파일 한 개/한 시점의 검증이며 관리자·다른 복사본까지 보호한다는 주장은 하지 않는다.

## 학습 설정 고정과3개 제한

`freeze_training_cycle.py`는 직접 감사를 재실행하고, 실제 OS 접근 검사를 재실행하며, 검수된 train/validation의3라벨과 실제 토크나이저 전체 길이≤768을 확인한다. 정답/필수 근거를 자르지 않는다. 통과 후에만 새 MLX train/valid 파일을 만들고 모델 가중치/토크나이저/설정/코드/lock/데이터/검수/이력/프로토콜의 해시를 고정한다. 블라인드 최종 정답은 학습 폴더에 넣지 않는다.

`data/training_candidates.example.json`은 30회/1e-4와60회/5e-5의 **제안 예시**이며 실행하지 않았다. 한 주기 최대3개, rank8/layers8/seq768/batch1/seed0/scale20/dropout0, 전체 검증셋 loss, 외부 report 비활성, 후보당 최대1800초다. 품질 선택은 검증셋만 사용하며 최종 정답을 보고 설정을 바꾸지 않는다. loss 최저값만으로 모델 승격하지 않는다.

```bash
.venv/bin/python backend/scripts/freeze_training_cycle.py --candidates PRIVATE/reviewed-train-valid.jsonl --history PRIVATE/exposures.jsonl --reviews PRIVATE/human-reviews.jsonl --configs data/training_candidates.example.json --protocol docs/NEXT_PHASE_PROTOCOL.md --isolation PRIVATE/os-isolation.json --out PRIVATE/frozen-cycle
.venv/bin/python backend/training/train_local.py --cycle PRIVATE/frozen-cycle/cycle.json --candidate small-30 --out outputs/runs/NEW-small-30
```

현재 자료로 첫 명령은 DATA_GATE_BLOCKED가 정답이다. `approval.json`의 수동 true 플래그 경로는 제거했다. launcher는 고정 파일과 live 검수/이력/OS 접근을 재확인하고 singleton 모델 lock을 확보한 후에만 후보 예산을 예약한다. runtime/training-attempts.jsonl에 실패·시간초과·중단도 사용 횟수로 기록한다. 새 freeze 폴더가 예산을 초기화하지 않으며 자동 reset/네 번째 실행 경로는 없다. 같은 UID가 파일/코드를 직접 고치거나 MLX 명령을 직접 실행하는 것까지 방지하는 OS 보안 장치는 아니다.

## A~F 비교

| 실험 | 구성 | 현재 상태 |
|---|---|---|
| A | Base | NOT_RUN 독립 최종셋 없음 |
| B | FT | NOT_RUN 검증셋 선택/고정 없음 |
| C | Base+RAG | NOT_RUN 승인 참고 코퍼스 없음 |
| D | FT+RAG | NOT_RUN 동일 |
| E | Base+RAG+Agent | NOT_RUN 동일 |
| F | FT+RAG+Agent | NOT_RUN 동일 |

기존 노출54건 A/B는 별도 역사적 개발 비교이며 위 표를 채우지 않는다. 현재 데모의 keyword+MCP+Graph 통합 성공도 A~F 실험값이 아니다.

실험 전에 동일 sample ID/공개 증거 버전·해시/참고 자료 접근 범위/모델ID·revision·양자화·config·tokenizer·chat template/생성/출력·복구/평가기/장비/검증셋 선택 고정 해시/최종셋 해시를 정한다. B/D/F는 같은 실제 어댑터를 사용한다. A/C/E는 어댑터를 로드하지 않는다. A~D는 모델 호출1회, E/F는 최대4회/복구1회이며 추가 호출/토큰/시간을 모두 보고한다. 정보까지 달라지면 순수 에이전트 효과가 아닌 전체 시스템 비교다.

`backend/evaluation/compare_af.py`는 A.json~F.json이 모두 있을 때만 조건과 비용 지표를 확인한다. 누락 행을 채우거나 효과를 추정하지 않는다. 이 비교 검사기가 전체 여섯 실행기를 구현/검증했다는 뜻은 아니다. 실제 독립 자료와 승인 RAG 코퍼스가 확보되면 각 실행 경로의 실제 추론과 인용·검색 Recall/MRR를 먼저 검증해야 한다.

## 로컬 운영 정책과 판정

권장 실행은 `make serve`로 개인 접근키 인증을 켠다. `make serve-demo`는 명시적 무인증 합성 데모다. 로컬 접속만 허용하며 외부 호스트·교차 출처·CSRF·타인 소유권 경계를 유지한다. 실제 법원 자료나 다중 사용자 계정 모델은 연결하지 않는다.

현재 삭제 정책은 **운영자가 명시한 사건만 서버를 중단한 상태에서 삭제**하는 방식이다. 새 삭제 journal은 별도로 보관하며 이전 DB 백업과 함께 되돌리지 않는다. 복구는 새 파일만 생성하고 최신 journal을 먼저 적용하며 과거 bearer 세션을 모두 폐기한다. 자동 기간 삭제/백업 보존기한/암호화 키 폐기/물리적 완전 삭제는 미정·미검증이다. APFS 스냅샷과 다른 백업의 바이트는 남을 수 있다. 원본 데이터·어댑터·기존 평가 자료는 이 시험에서 삭제하지 않았다.

현재 승격 판정은 LOCAL_VALIDATED(합성·개인 로컬 범위) 유지다. PILOT_READY는 검수 자료/OS 격리/운영 보존정책이 없어 BLOCKED다. 공개 운영은 사용자 요청 범위 밖이며 승인하지 않는다.

개인 서버는 독립 deletion journal이 없으면 기동을 거부하며 기동 시 미완료 삭제를 먼저 재적용한다. 복구 경로는 모든 세션을 폐기하고, 일반 기동은 삭제 대상 소유자의 세션을 폐기한다. journal은 이전 DB 백업과 함께 롤백하지 않는다.
