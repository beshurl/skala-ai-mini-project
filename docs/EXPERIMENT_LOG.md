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
