# 공개 NLI 사용자 위임 검토

**최신 준비:** [MODEL_READINESS](MODEL_READINESS.md)의 v3 재결합 패킷/실제 데이터 감사 PASS. 학습262/검증139·49격리/450 AI 판단/사람 이력을 그대로 계승했다. 기존128토큰 생성 계약·401 입력 프롬프트가 같음을 실제 cached tokenizer로 확인했다. 새 실행 계획은 아직 실행 불가 준비본이며 실제 SQLite CANTOPEN/작업·새 OS 진단이 먼저다. 옛 --execute 명령은 계속 사용 중지한다.

**2026-10-21 현재: 아래 2026-10-20 실행 명령은 사용 중지.** 일반 검토 경로의 model.py 변경으로 execution-plan.json의 bound_files SHA가 달라졌다. 원 계획을 수정하거나 gate를 우회하지 않으며 새 소스 결합 계획/현재 OS·작업 상태 확인 뒤 새 실행 안내를 준비해야 한다. [현재 범위](GENERAL_REASONING.md). 새 학습은0/3이다.

2026-10-20 KST. 사용자는 이 대화에서 **“공개 NLI만 AI 위임 검토 허용”**이라고 명시했다. 해당 질문은 공개 KLUE-NLI 학습300건·검증150건의 AI 검토와 사용자 위임을 별도 학습 조건으로 인정하는 것이었다. 실제 사람 검수는 생성하지 않았고 실제 판결문 승인 범위를 넓히지 않았다.

근거 폴더: `outputs/runs/20261020T161908+0900-authorized-data-validation/`.

## 데이터 결과

| 구분 | 검토 대상 | 통과 | 격리 |
|---|---:|---:|---:|
| 공개 NLI 학습 후보 | 300 | 262 | 38 |
| 공개 NLI 검증 후보 | 150 | 139 | 11 |
| 합계 | 450 | 401 | 49 |

학습300건을 AI가 문장별로 읽고 판단 근거를 작성했다. 검증134건은 이전 AI 검토와 실제 문장·라벨·원 subject SHA가 같은 것을 확인해 근거를 재사용했고 변경16건은 새로 검토했다. 그 과정의 개인정보 맥락 재확인도 별도로 기록했다. 실제 새 열람328건을 노출 ledger에 append해556→884건으로 만들었으며 원556건의 바이트 prefix와 전체 chain을 확인했다.

불확실한 라벨, 시제·인용·수량·배타 조건의 추론 문제, 실명과 민감 사건의 결합, 미성년자 정보, 허구 여부가 확인되지 않은 민감 인물 맥락은 보수적으로 제외했다. 제외는 출판자 라벨 오류의 확정이나 위법 판단이 아니다. 원450건·기존 라벨·이전 수정안·사람 이력을 보존했고 이번 새 라벨 수정은0건이다. 공개 코퍼스의 보조 주석 불일치는 의미적 정답의 증거로 사용하지 않았다.

최종 봉인 패킷은 `final-packet.json`이 가리키는 보호 볼륨의 `delegated-reviewed-training-v2`다. 학습262/검증139와 별도 진단150의 입력·정답을 구분한다. 진단150은 이번 의미 검토·위임 승인·학습 파일 변환 대상에서 제외했다. 기존 프로토콜의 모델·revision·greedy/seed0/thinking off와 최대3개 후보 설정을 유지했다. 정제 후 검증 분모139와 scorer는 모델 결과를 보기 전에 고정한다.

이 자료는 공개 개발용 NLI이며 모델 사전학습·외부 노출은 UNKNOWN이다. 기록된 로컬 노출의 snapshot만 확인했으며 비공개 독립 최종셋으로 계산하지 않는다. 이번 후보 어댑터의 출력 계약은 `{label}` 문장 관계 분류다. 증거 인용·사건 전후 비교를 포함한 서비스 전체 성능, 실제 사건 성능, A~F 비교는 별도 조건이다.

## 승인·보존 통제

- `human_attestation`과 `delegated_ai_review`를 분리한다. 사람 승인 수는0이며 `human_reviewed=false`를 유지한다.
- 사용자 응답·450개 정확한 subject·프로토콜·공개 출처·라이선스 bytes를 결합한 grant와450개 판단 chain을 요구한다. 일반 boolean 승인 파일은 사용하지 않는다.
- 실제 판결문·다른 과제·진단 자료·범위를 벗어난 subject·변경된 라벨/출처/권한·격리 결정은 위임 경로로 통과하지 않는다. 명시적인 사람 반려를 우회하지 않는다.
- grant/AI ledger/노출 snapshot을 동결 주기에 결합한다. 변경 시 주기를 무효화한다. 원본 데이터·기존 어댑터·기존 평가15개 보호 경로의 SHA는 모두 일치했다.
- 새 어댑터에 한해 MLX가 생성한 설정 원본을 별도 보존하고 모델 경로를 실제 동결 모델 ID/revision과 연결한다. 가중치 바이트 불변 receipt를 만든다. 기존 어댑터에는 적용하지 않는다.

## 실행 상태와 관리자 인증

실제 데이터 감사 PASS, 실행 계획의 비변경 점검 PASS. 백엔드153 tests, compileall, pip check, diff check가 exit0이다. 프론트의 서비스 소개는 **증거 기반 AI 미제사건 재수사 지원**으로 반영했고 로컬 fixture 화면을 확인했다. 이미지와 기존 문 열림 연출을 보존했다. 이는 UID499 운영 복사본에 대한 배포 기록이 아니다.

현재 실행 세션에서는 새 실제 정답3경로의 평가자 읽기/해시는 확인했으나 서비스 계정 전환은 관리자 인증 부재로 실행하지 못했다. 이 실패는 파일 접근 거부의 증거가 아니다. 실제 freeze는 OS gate에서 예상 exit2, 출력 bundle 생성0·모델 로드0·새 학습0/3이었다. 이전 OS PASS를 새 정답에 재사용하지 않았다.

아래 명령은 **beshu의 Mac 터미널**에서 실행한다. Python 명령 앞에 sudo를 붙이지 않는다. 관리자 암호는 터미널의 sudo 프롬프트에만 입력한다.

```sh
/Users/beshu/Downloads/recase_macos_16gb/.venv/bin/python /Users/beshu/Downloads/recase_macos_16gb/outputs/runs/20261020T161908+0900-authorized-data-validation/run_authorized_training.py --execute
```

실행기는 고정된 PID41133/UID499와 코드·프로토콜·원래 잠금 inode를 확인한다. 진행 중 작업이 있으면 변경 없이 멈춘다. 인증 후 실제 정답/변환 파일 접근 차단을 확인하고 동결한다. 기존 daemon을 잠시 중지해 모델 잠금 해제를 확인한 뒤 기본 모델 검증→선언 후보c1 한 개 학습→같은 검증셋 평가→조건 일치 비교를 실행하고 동일 plist로 서비스를 재개한다. 장시간 단계 사이와 재개 시 관리자 암호가 다시 필요할 수 있다. root 전용 plist는 권한을 넓히지 않고 인증된 터미널에서 SHA만 확인한다.

실패는 보존하며 자동 재시도·후보 추가·어댑터 자동 교체를 하지 않는다. 결과는 이 run 아래 새 `execution-<uuid>/`에 저장한다. 서비스 재개 실패 시 터미널에 표시된 기존 plist bootstrap 명령으로 로컬 관리자가 복구한다. daemon 재개와 모델 준비 상태의 확인 범위도 구분한다.

## 보존한 실패

구형 외부 감사 도구는 패킷 내부의5개 재작성 출처를 수집 폴더에서 찾다가 실패했다. 원 실패를 보존하고 출처 종류별로 원문·라벨·subject를 대조하는 새 준비 도구로 처리했다. 최초 계획 작성은 root 소유0600 plist 읽기가 거부되어 중단됐고 뒤이은 계획 점검은 파일 부재로 실패했다. 권한 변경 없이 패킷을 보존하고 root 파일 metadata 결합과 인증 후 hash 검증으로 계획을 완성했다. 실패 중 모델 호출·학습·서비스 변경은0이었다.

권위 있는 결과: `delegated-preparation.json`, `final-packet.json`, `final-data-audit.json`, `execution-plan-check.json`, `fresh-isolation-new-packet.json`, `freeze-auth-pending-execution.json`, `backend-tests-final.json`, `post-checks.json`, `exposure-prefix-preservation.json`.
