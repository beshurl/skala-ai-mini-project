# 실험 기록

## 2026-10-20 KST — 재현 비교 계획

- 변경 원인군: 평가기 신뢰성/조건 식별 및 일관성. 모델·학습 데이터·어댑터는 보존.
- 평가 프로토콜: EVALUATION_PROTOCOL.md v2. 기존 54건 개발 평가 전체.
- 후보: 기존 Base 4B와 기존 100 iteration LoRA. 새 학습 후보 0/3.
- 생성: 동일 snapshot, greedy, thinking off, seed 0, 최대 256 tokens. 원시/복구 결과 구분.
- 호출 전 예상 시간 3~10분. OOM·과도한 메모리 압박·불안정시 중단하고 실패를 보존.
- 기존 15건 로그는 revision·생성 설정이 없어 UNVERIFIED. 기존 점수 재계산과 새 모델 평가는 분리.
