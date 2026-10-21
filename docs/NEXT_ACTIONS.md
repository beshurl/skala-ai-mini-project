# 다음 작업과 사용자 실행 안내

**현재 우선순위:** [MODEL_READINESS](MODEL_READINESS.md)의 한 줄 진단 명령을 따른다. 기존 /usr/bin/sqlite3가 CANTOPEN14로 실패했고 두 줄 cd 입력은 진단 미실행이었다. 새 protected-volume NLI v3 준비본/257 tests는 PASS지만 실행기는 미제공·학습0/3이다. 실제 작업 상태를 확인하기 전 서비스 중지/모델 추가 실행·이전 실행기 재사용을 하지 않는다.

**2026-10-21 현재 순서:** 계정 개편 완료 후 [최신 통합 검증](ACCOUNT_RECOVERY.md)은 소스/123파일 합성 후보에서 PASS했다. 실제 UID499는 이전 코드 그대로다. [이번 사용자 안내](../outputs/runs/20261021T090314+0900-account-integration-6a7cb0/USER_NEXT_STEPS.txt)의 관리자 읽기 전용 진단으로 기존 지연/취소 상태부터 확인한다. 비밀번호는 로컬 sudo/계정 CLI에만 입력한다. 기존 사건은 사람이 소유권을 확인하기 전 새 계정에 배정하지 않는다. 구 후보 덮어쓰기/예전 --apply 재실행은 하지 않는다. 아래 병행 작업 대기는 이력이다.

**현재 작업 순서:** 계정 인증 개편은 사용자가 다른 작업에서 진행 중이며 **완료 후 통합 검증**하기로 했다. 해당 변경은 보존한다.119파일 후보/174 tests는 개편 전 접근키 스냅샷이므로 현재 계정 서비스 배포본으로 쓰지 않는다. 완료 후 계정 DB/세션·역할·사건 소유권·백업/복구/코드 복귀를 포함해 다시 검증한다. 기존 UID499 운영 작업의 읽기 전용 관리자 진단은 이 병행 변경과 별도로 여전히 필요하다.

**최신 적용 준비:** [119파일 후보·전환 검사](RELEASE_TRANSITION.md)/[실행 결과](../outputs/runs/20261020T173502+0900-release-transition-bcc984/RESULT.txt). 후보 재생성·합성 사본의 schema1→2·새 기록 후 schema2 코드 복귀/구 DB 거부·암호화 백업을 확인했다. 실제 UID499 적용은0이며 현재 먼저 필요한 것은 아래 ADMIN_DIAGNOSTIC의 로컬 관리자 읽기 전용 작업 상태 확인이다. verify_release_database.py는 중지 DB 사본의 기록 보존 검사이며 실제 서비스 중단/배포/복귀를 실행하지 않는다. schema1 운영 코드에 schema2 DB를 연결하거나 새 기록을 과거 DB로 덮어쓰지 않는다. 아래 옛 '후보 재생성 필요'는 이번 후보 갱신으로 대체하되 실제 OS/UID/모델·자동 보존·완전 폐기·데이터 gate는 유지한다.

**최신 백업 보호 준비:** [암호화 백업 사용법/한계](ENCRYPTED_BACKUPS.md). 백업별 새 키·인증·새 사본 복구와90/30일 미리보기를 합성 CLI13개/전체164 tests로 확인했다. 실제 UID499 적용·기존 백업 전환·자동 삭제·키 폐기는 하지 않았다. 새 키 부재 시험은 이름 복원으로 끝냈으며 완전 폐기로 표시하지 않는다. 현재 필요한 관리자 작업은 아래 기존 읽기 전용 상태 진단이다. 앞선115파일 후보는 새 도구를 포함하지 않으므로 적용 전에 재생성한다. NLI 위임 검토/학습의 현재 별도 인증 안내는 DELEGATED_NLI_REVIEW.md를 유지한다.

**최신 UI·운영 준비:** [사건 관리 화면 결과](../outputs/runs/20261020T164135+0900-lifecycle-ui-9152c8/RESULT.txt)/[배포 검토 초안](../outputs/runs/20261020T164135+0900-lifecycle-ui-9152c8/DEPLOYMENT_REVIEW.txt). 종료/재개·보류/해제와 사유·충돌 처리, fixture 브라우저/115파일 배포 후보 사본 검증 완료. 실제 UID499 서비스에는 미배포·자동90/30일 삭제 비활성이다. 적용 전 아래 ADMIN_DIAGNOSTIC의 읽기 전용 상태 확인이 먼저다. 관리자 비밀번호는 로컬 sudo 프롬프트에만 입력한다.

**현재 공개 NLI 절차는 [DELEGATED_NLI_REVIEW](DELEGATED_NLI_REVIEW.md)를 우선한다.** 사용자 위임450건의 AI 검토 통과 학습262/검증139·49격리를 완료했으며 사람 수행으로 기록하지 않았다. 같은 검토를 다시 요구하지 않는다. 준비한 run_authorized_training.py는 미실행이고 실제 정답 OS 검사·서비스 일시 중지에 로컬 관리자 인증이 필요하다. 독립 최종/진단150/실제 판결문의 사람 검수는 별도다. 아래 옛 패킷 승인0·450건 직접 검수/노출556/UI 미연결은 당시 이력이다.

현재 lifecycle/백업 receipt 소스 구현과 합성 CLI 검증을 추가했다. [최신 결과와 적용 범위](../outputs/runs/20261020T161845+0900-retention-lifecycle-10ab30/RESULT.txt)를 먼저 확인한다. **UID499 운영 DB에는 아직 적용하지 않았고 기존 schema1을 새 코드로 바로 기동하지 않는다.** 사용자에게 지금 필요한 관리자 명령은 아래 기존 ADMIN_DIAGNOSTIC의 읽기 전용 상태 집계다. 실제 migration/배포는 그 상태 확인 후 새 계획/백업을 준비한다. 검수 패킷·기간90/30 선택은 그대로이며 같은 입력을 다시 요구하지 않는다.

## 최신 실행 순서 — 세 단계 후속

[현재 결과와 상세 명령](../outputs/runs/20261020T155158+0900-remaining-work-b82291/USER_NEXT_STEPS.txt)을 먼저 따른다. 실제 모델 첫 요청이30초 내 미완료여서 지속 부하를 중단했으므로 우선 같은 run의 ADMIN_DIAGNOSTIC.txt를 사용자 터미널에서 실행해 상태 metadata를 확인한다. 읽기 전용이며 비밀번호는 sudo 프롬프트에만 입력한다. 추가 모델 호출이나 재시작을 반복하지 않는다.

검수는 다음 **현재 native600건 패킷**에서 시작한다. 기존150건 단독 패킷은 보존하고 새 검수를 중복 진행하지 않는다. 사용자 선택 재작성5건/라벨 제안을 모두 포함하며 변경16건이 우선 표시된다. 검증150건 다음 학습 후보300건을 직접 검수한다. 새 패킷은 승인0건이며 AI가 승인하지 않는다.

```bash
cd /Users/beshu/Downloads/recase_macos_16gb
RECASE_NATIVE_PACKET=outputs/runs/20261020T134803+0900-isolation-review-0385fc/protected_mount/revisions/20261020T155158+0900-remaining-work-b82291/native-nli-packet
.venv/bin/python backend/scripts/review_prepared.py status --prepared "$RECASE_NATIVE_PACKET"
.venv/bin/python backend/scripts/review_prepared.py review --prepared "$RECASE_NATIVE_PACKET" --dataset nli_validation --limit 10
# 검증셋 검수 뒤 학습 후보를 실제 확인한다.
.venv/bin/python backend/scripts/review_prepared.py review --prepared "$RECASE_NATIVE_PACKET" --dataset nli_train_candidates --limit 10
```

라이선스/개인정보/라벨/처리·학습 목적과 이력 범위 확인, 새 정답의 실제 OS 격리, 모델 잠금 해제는 별도 조건이다. 같은 가족의 개발 진단을 독립 최종셋으로 바꾸지 않는다. native NLI 동결 연결은 이미 완료했고 실제 미검수450·이력 누락으로 예상 차단/후보0/3임을 확인했다.

사용자 보존기간 입력은 **사건90일·백업30일로 완료**했다. 종료일/백업 생성 receipt를 기준으로 하는 초안·미리보기만 준비했고 현재 수동 정책은 유지한다. 날짜 없는 과거 기록/보류/복구 미검증 백업을 자동 만료시키지 않는다. 실제 삭제·백업/키 폐기·스케줄러 활성화0이다. 아래 이전 안내의 '기간 미정'은 이 선택으로 대체한다.

---

이하 이전 패킷·완료한 운영 검증의 이력이다.

대상은 이 Mac의 로컬 전용이다. 기존 정답의 OS 격리와 실제 UID499 백업·복사본 삭제/복구 검증은 PASS다.16건의 후속 처리안과 사용자 문구 선택 반영은 완료했고, 다음은 아래0.1의 새 버전 최종 검수다. 원본의 직접 사람 승인1/대기149는 유지하며 새 버전은 승인0/대기150이다. 이미 완료한4번의 sudo --apply를 반복하지 않는다. 검수·실행 전 검사를 통과해야 새 자료 추론/학습을 실행한다. 기존 데이터·어댑터·평가·삭제 journal은 보존한다.

## 0. 요청한 AI 검토 결과

기존 공개 NLI150건 AI 검토의 원문 결합을 검증하고 쟁점17건을 추가 검토했다. 갱신 집계는 원라벨 지지134/문맥 판정12/수정 후보4다. [요약 결과](../outputs/runs/20261020T151035+0900-ai-review-followup-95bc0c/RESULT.txt), [우선16건 원문·근거](../outputs/runs/20261020T134803+0900-isolation-review-0385fc/protected_mount/reviews/20261020T151035+0900-ai-review-followup-95bc0c/PRIORITY_REVIEW_16.txt)를 확인할 수 있다. 원문/정답/분모는 바꾸지 않았으며 개인정보 맥락13건·문구 품질7건의 기존 표시도 남아 있다.

AI 검토는 완료했으며 실제 수행자를 AI로 기록했다. 사람 직접 검수·개인정보/라이선스·목적 승인은 별도 이력으로 유지한다. 아래 CLI에서는 AI 보고서를 참고해 실제 확인한 항목을 입력한다. 모호한16건을 자동 반려하거나 평가 분모에서 제외하지 않는다. 수정이 결정되면 원본 대신 새 버전의 자료/프로토콜/검수 subject를 만들어야 한다.

### 0.1. 사용자 선택을 반영한 새 버전 검수

사용자가 의도가 불명확한5건 모두 별도 재작성안 사용을 선택했다. 기존 수정 후보4건+현재 엄격 지침에 따른 문맥7건의 라벨 제안11건, 별도 재작성5건을 새150건 초안에 반영했다. 원본 대비 라벨 차이는12건, 문장 변경5건이며 기존 공식 라벨과 첫 초안은 유지한다. 새 문장5건은 조건을 추가한 AI 작성 진단 예문이며 출판자 원문 교정/독립 최종셋으로 취급하지 않는다. 문구 선택은 모두 끝났으며 같은 선택을 다시 묻지 않는다.

[최신 결과·변경16건 대조표와 명령](../outputs/runs/20261020T153504+0900-nli-disposition-draft-f94ac8/FINAL_HANDOFF.txt), [사용자 문구 선택 기록](../outputs/runs/20261020T153504+0900-nli-disposition-draft-f94ac8/wording-selection.json)을 따른다. 새 검수 패킷은 실제 sealed loader 검증을 통과했고 subject150건/승인0건이다. 이전 승인을 자동 이전하지 않았다. 실제 CLI에서 변경16건을 먼저 표시하도록 순서를 확인했다. 직접 필요한 남은 확인은 최종 라벨·개인정보·라이선스·처리 목적이며 자동 yes 입력은 허용하지 않는다.

```bash
cd /Users/beshu/Downloads/recase_macos_16gb
RECASE_REVISED_PACKET=outputs/runs/20261020T134803+0900-isolation-review-0385fc/protected_mount/revisions/20261020T153504+0900-nli-disposition-draft-f94ac8/review-packet
.venv/bin/python backend/scripts/review_prepared.py review --prepared "$RECASE_REVISED_PACKET" --dataset nli_validation_v2_wording_draft --limit 10
```

검수에는 sudo나 서비스 중단이 필요 없다. 실제 평가 사전검사는 미승인150건·새 정답 SHA에 대한 OS proof 부재·모델 점유로 exit2/모델 로드0이었다. 검수 완료 후 새 실제 정답 경로/해시에 대한 서비스 계정 접근 거부를 검증해야 한다. 기존 isolation 결과를 이 새 정답에 재사용하거나 JSON의 정답 SHA만 바꾸지 않는다. 아래1번은 원본 KLUE 검수 재개 절차이며 새 버전과 별도다.

## 1. 사용자 터미널에서 검수 시작

이미 사용 중인 macOS 터미널에서 아래를 실행한다. 이 문서의 터미널 변수는 같은 창에서 이어서 사용한다.

```bash
cd /Users/beshu/Downloads/recase_macos_16gb
RECASE_REVIEW_RUN=outputs/runs/20261020T134803+0900-isolation-review-0385fc
.venv/bin/python backend/scripts/review_prepared.py status --prepared "$RECASE_REVIEW_RUN/prepared"
.venv/bin/python backend/scripts/review_prepared.py review --prepared "$RECASE_REVIEW_RUN/prepared" --dataset nli_validation --limit 10
```

한 번에10건씩 전제·가설·제안 정답, 개인정보/간접 식별자, 표시된 라이선스 파일과 요청 목적을 직접 확인한다. 실제로 확인한 항목만 yes로 답한다. 승인/반려/보류/종료를 선택할 수 있다. 자동 yes 입력은 허용하지 않는다. 자동 검사에서 표시된 주석 불일치를 우선 표시하지만 오류로 확정하지 않는다.

현재 남은 자료에서 다음10건을 [보호 볼륨의 검수 파일](../outputs/runs/20261020T134803+0900-isolation-review-0385fc/protected_mount/reviews/20261020T150521+0900-operations-confirmed-6923ae/next_10_nli_validation.txt)에0700/0600으로 준비했다. 원문을 채팅에 붙일 필요 없이 이 파일과 실제 CLI에서 검수할 수 있다. 파일을 열어 보는 것만으로는 승인되지 않는다. 기존 승인1건의 근거가 단순 yes여서 해당 판단을 추적할 수 있도록 의미·개인정보·권리 판단 이유를 보완하는 것을 권한다. 실제 판단은 기존 기록을 덮어쓰지 않고 아래 명령으로 새 이력을 남긴다.

```bash
.venv/bin/python backend/scripts/review_prepared.py review --prepared "$RECASE_REVIEW_RUN/prepared" --dataset nli_validation --sample-id klue_nli:klue-nli-v1.1_dev:545 --limit 1
```

보완 여부를 에이전트가 자동 판정하거나 기존 승인을 임의로 바꾸지 않았다. 이 작업의 새 승인 기록은0건이다.

같은 명령을 반복하면 승인/반려한 건을 건너뛴다. 보류한 건은 다시 나온다. 잘못된 정답·문구·권리 문제는 반려 사유에 기록하고 원본을 편집하지 않는다. 특정 건의 재검수/승인 철회는 같은 명령에 `--sample-id 해당ID`를 추가하고 반려 또는 새 판단을 기록한다. 자료 수정은 새 버전으로 진행한다.

검수 순서와 용도:

| --dataset 값 | 건수 | 용도 |
|---|---:|---|
| nli_validation | 150 | 설정·후보 비교용 검증 |
| nli_diagnostic | 150 | 공개 개발 진단; 비공개 최종셋이 아님 |
| nli_train_candidates | 300 | 필요한 경우에만 학습 후보. training 목적 별도 확인 필요 |
| scenario_diagnostic | 36 | 합성12계열/3버전. 시계 검교정3건은 문구·정답 직접 판정 필요 |
| summary_diagnostic | 30 | 요약. 원문 밖 사실/식별자/라이선스 직접 확인 |
| legalqa_benchmark | 226 | 평가 전용. 학습 승인 대상이 아님 |

위 명령의 --dataset 값만 바꾼다. 새 검수 CLI는 각 묶음 전체를 처리하며 기존 패킷의 첫 표본에만 제한되지 않는다. `status`로 승인/반려/대기 건수를 확인한다. 단지 명령을 실행하거나 담당을 수락한 것은 검수 완료가 아니다. 반려가 있으면 그 ID를 임의로 분모에서 빼고 평가하지 않는다.

노출 이력도 실제로 확인한 범위만 기록한다. 아래 명령에서 과거 학습/검증/정답 열람·외부 전송 이력의 누락을 모르면 완료로 확인하지 않는다.

```bash
.venv/bin/python backend/scripts/dataset_control.py attest-history --history outputs/runs/20261020-next-gates/exposures.jsonl
```

## 2. 관리자 격리 단계 — 현재 완료

최신 실제 결과는 `outputs/runs/20261020T134803+0900-isolation-review-0385fc/finish-20261020T144251-f1772e/result.json`이다. status=PASS, 서비스 UID499/평가자 UID501, 실제 정답7개 및 원래 작업 폴더 사본·암호화 키 접근 거부를 확인했다. 이 작업에서 PID41133의 실제 MLX/56개 LoRA readiness도 재확인했다. PID는 재기동하면 바뀐다.

계정 생성/최초 configure 명령을 다시 실행할 필요가 없다. 현재 운영 경로는 `/Users/Shared/RECASE-isolated-0385fc`이며 서비스 DB·최신 삭제 journal은 그곳의 state/에 있다. 원래 runtime/ DB와 자동 동기화되지 않는다. 현재 격리 서버와 별도로 `make serve`를 실행하지 않는다. 기존 접근키는 계속 사용한다. 배포 코드는 복사본이므로 이 작업의 새 학습/평가 도구가 서비스 배포를 자동 수정하지 않는다.

향후 중단된 격리 서비스의 재개가 필요한 경우에만 기존 터미널에서 `finish_local_isolation.py --run "$RECASE_REVIEW_RUN"`의 읽기 전용 계획부터 확인한다. 실제 변경 명령에는 --apply와 sudo가 필요하다. 비밀번호는 sudo의 로컬 프롬프트에만 입력하고 비밀키·비밀번호를 채팅에 보내지 않는다. 계정·실행 파일·잠금 inode·정답 해시가 달라지면 적용하지 않고 오류를 확인한다.

## 3. 확인이 끝나면 이어지는 작업

검수 기록과 위 격리 결과 파일을 에이전트가 확인한다. 원문/정답을 채팅에 붙여 넣을 필요는 없다. 재평가/학습 직전의 실제 다른 계정 probe에 필요한 sudo 인증이 만료됐다면, 사용자 터미널에서 `sudo -v`로만 갱신한다. 전체 평가/검수 프로그램을 sudo로 실행하지 않는다.

1. 실제 서비스 UID/정답 경로·해시·접근 거부를 재확인한다.
2. 격리 서버를 정상 중단하고 공유 model.lock 해제를 확인한 뒤, 검수된 묶음의 Base/기존 FT를 고정 조건으로 순차 재평가한다.
3. 검증셋의 오류 분석이 학습 필요성을 뒷받침할 때만 native NLI의 train/validation을 동결한다. 동결 도구는 사람 검수·이력·중복/계열·실제 OS 접근·토큰 길이를 다시 검사한다. 실패하면 모델을 로드하거나 후보 횟수를 사용하지 않는다.
4. 기존 train_local.py와 전역 runtime/training-attempts.jsonl로 최대3개 후보를 실행한다. 실패·시간초과도 횟수에 포함하며 새 폴더로 초기화하지 않는다. 진단/최종 정답은 학습 파일에 넣지 않는다.
5. 실제 판례 검색은 별도 rag/display 승인과 코퍼스 검수가 필요하다. 공개 진단 결과를 비공개 최종 성능이나 A~F 전체 결과로 바꾸지 않는다.

새 실행 명령의 형태는 아래와 같다. 15:05 KST 실제 사전검사에서는 validation149건 승인 누락·현재 세션의 계정 전환 인증 부재·실행 중 서버의 모델 점유로 exit2였으며 모델은 로드하지 않았다. 기존 OS 격리/운영 PASS와 구분한다. 현재는 검수를 먼저 진행하며 서버를 중단하거나 관리자 명령을 다시 실행할 필요가 없다. NEW-*는 매번 새 목적지명으로 바꾸며 기존 산출물에는 쓰지 않는다. 검수 완료 후 모델을 사용하는 명령은 격리 서버 정상 중단과 공유 model.lock 해제 후 실행한다.

```bash
RECASE_OS_REPORT="$RECASE_REVIEW_RUN/finish-20261020T144251-f1772e/result.json"
.venv/bin/python backend/evaluation/evaluate_prepared.py preflight --prepared "$RECASE_REVIEW_RUN/prepared" --dataset nli_validation --isolation-report "$RECASE_OS_REPORT" --out outputs/runs/NEW-preflight.json
.venv/bin/python backend/evaluation/evaluate_prepared.py evaluate --prepared "$RECASE_REVIEW_RUN/prepared" --dataset nli_validation --isolation-report "$RECASE_OS_REPORT" --variant base --out outputs/runs/NEW-base
.venv/bin/python backend/evaluation/evaluate_prepared.py evaluate --prepared "$RECASE_REVIEW_RUN/prepared" --dataset nli_validation --isolation-report "$RECASE_OS_REPORT" --variant existing_ft --out outputs/runs/NEW-existing-ft
.venv/bin/python backend/evaluation/evaluate_prepared.py compare --metrics outputs/runs/NEW-base/metrics.json outputs/runs/NEW-existing-ft/metrics.json --out outputs/runs/NEW-comparison.json
```

학습 필요성이 확인되고 train/validation 전체 검수가 끝난 뒤 같은3회 제한 이력을 사용한다.

```bash
.venv/bin/python backend/scripts/freeze_training_cycle.py --prepared "$RECASE_REVIEW_RUN/prepared" --history outputs/runs/20261020-next-gates/exposures.jsonl --configs "$RECASE_REVIEW_RUN/prepared/training_candidates.json" --protocol docs/NEXT_PHASE_PROTOCOL.md --isolation "$RECASE_OS_REPORT" --out outputs/runs/NEW-frozen-nli
.venv/bin/python backend/training/train_local.py --cycle outputs/runs/NEW-frozen-nli/cycle.json --candidate native-nli-c1 --out outputs/runs/NEW-nli-c1
.venv/bin/python backend/evaluation/evaluate_prepared.py evaluate --prepared "$RECASE_REVIEW_RUN/prepared" --dataset nli_validation --isolation-report "$RECASE_OS_REPORT" --variant candidate --cycle outputs/runs/NEW-frozen-nli/cycle.json --training-run outputs/runs/NEW-nli-c1 --out outputs/runs/NEW-nli-c1-validation
```

후보 평가는 실제 완료된 학습 ledger와 같은 동결 주기를 요구하며 nli_validation에서만 허용한다. candidate 비교에도 위 compare 명령을 사용한다. 반려/새 검수/권한/라이선스/코드/데이터 변경은 동결 파일을 무효화하므로 새 버전 검증부터 진행한다. 직접 mlx_lm을 호출하거나 예산을 새 파일로 바꿔 우회하지 않는다.

새 NLI 어댑터의 출력은 영어3라벨 JSON이다. 기존 앱의 한국어 라벨·이유·인용 계약과 다르므로 서비스 어댑터로 자동 교체하지 않는다. 선택 후에도 앱 계약·시나리오 품질·인용 검증을 별도로 통과해야 한다.

자동 보존기간·백업 폐기 기간은 아직 확정되지 않았다. 실제 자료를 자동 삭제하도록 활성화하지 않는다. 현재 명시적 사건 삭제·독립 journal·복구 재적용을 유지한다. 유료 호출·공개 배포·원문 외부 전송은 별도 사전 승인 대상이다.

## 4. 격리 서비스 계정의 백업·삭제 후 복구 검증 — 완료

사용자가15:03:11 KST에 plan-final.json --apply를 로컬 터미널에서 실행해 exit0/PASS를 반환했다. **실제 UID/EUID499의 운영 읽기 전용 백업·새 합성 복사본 삭제/복구 검증이 완료됐다.** [실제 결과](../outputs/runs/20261020T145215+0900-isolated-operations/execution-4df356d4005c442992653e0cfc76fd09/result.json)와 [독립 사후 대조](../outputs/runs/20261020T150521+0900-operations-confirmed-6923ae/verification.json)를 보존했다. 같은 --apply 명령을 다시 실행하지 않는다.

실행 계획/worker/배포 모듈/정책 해시, 실제 UID/PID/실행 경로와 전체 검증 항목을 대조했다. 현재 서버도 PID41133/UID499, 인증된 ready=true/기존 모델56 LoRA이며 공유 잠금 inode가 동일하다. 이전 준비 테스트96개의 backend 소스도 변경되지 않았다.

실제 스냅샷80사건/독립 journal1기록 보존, 새 합성 사건의 복사본 삭제·tombstone 재적용·복구 세션 폐기·다른 사건 보존·0600·무결성·백업 바이트 보존이 PASS다. 운영 DB의 사건/운영 journal/기존 백업을 삭제·덮어쓰지 않았다. 모델 호출·새 학습·서비스 중단·운영 삭제0이다. 실제 스냅샷에는 대기 작업이 없어 SERVER_RESTARTED 전환은0건이며 그 경로는 별도 합성 fixture1건에서 통과했다.

백업 내용은 서비스 전용 state/operations-check-4df356d4005c442992653e0cfc76fd09/에 남고 operator에게는 검사 metadata만 반환됐다. 실제 UID499 결과와 앞선 UID501 합성 fixture 결과를 구분한다.

향후 코드/배포/PID 변경 후 운영 검증이 다시 필요할 때는 새 계획과 새 목적지로 실행한다. 기존 계획·결과·백업을 덮어쓰지 않는다.

[로컬 수동 운영 정책](../data/local_operations_policy.json)은 현재 합성 로컬 동작을 문서화한다. 운영자가 명시한 사건만 삭제하고 백업은 명시적 폐기 전까지 보관한다. 자동 기간 삭제/백업 폐기 스케줄은 꺼져 있으며, 이 파일이 새로운 스케줄러를 설치하는 것은 아니다. 실제 자료 파생본/인덱스 정책과 물리적 완전 삭제는 별도 검증 대상이다.
