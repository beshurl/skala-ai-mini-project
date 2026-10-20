# 후속 실행 보고서

2026-10-20 KST. 목표: 이 Mac의 로컬 전용. 판정은 **LOCAL_VALIDATED(합성·개인 로컬 범위)** 유지이며 파일럿 승격은 BLOCKED다.

## 요청5항목의 실제 상태

| 요청 | 수행한 것 | 남은 조건 |
|---|---|---|
| 독립 데이터와 중복/노출 | 기존360건 노출 등록·신규 독립 분할에서 제외,12건/12계열 검수 대기 v2, 정확/정규화/숫자 템플릿/어휘 유사·계열 연결·노출 감사 | 검수 완료 자료0건, 새 블라인드 최종셋 없음, 노출 범위의 사람 확인 없음 |
| 판결문 목적별 승인/검수 | processing/학습/RAG/표시/재배포 독립 권한, 해시에 묶인 대화형 사람 확인/철회, 보호된 격리 출력 | 실제 판결문/사람 승인0건. 원문 반입·학습·검색 연결 없음 |
| OS 계정·보호 볼륨 | 실제 기존 정답 파일을 현재 서비스 UID로 open하고 evaluator 해시 대조 | 서비스 UID501의 읽기가 성공해 BLOCKED. 다른 계정/보호 볼륨/관리자 인증 필요 |
| 모델 고정·최대3학습·A~F | live 감사/OS 검사 후에만 freeze, 변경 해시 무효화, 실패도 포함한 영속3회 제한, A~F 조건/비용 비교 검사 | 새 학습0/3. 모델 선택 freeze 없음. A~F 모두 NOT_RUN, 승인 코퍼스 없음 |
| 로컬 인증·부하·삭제/복구 | 실제 접근키/브라우저 쿠키 인증, 실제 MLX 제한 부하, 독립 삭제 journal과 복구/기동 재적용 | 실제 자료 운영 보존기간·암호화 백업/물리 삭제·OS 격리 미완료. 공개 운영은 요청 범위 밖 |

검수 대기 자료를 검수 완료 독립셋으로 계산하지 않는다. 글자 유사 탐지는 의미 중복 제거의 완전한 증명이 아니다. 같은 UID의 운영자가 ledger/코드 전체를 다시 쓸 수 있다는 한계도 남는다.

## 검증 근거

산출물 루트: `outputs/runs/20261020-next-gates/`.

- `final-validation-retry1/summary.json`: 고정 clean venv에서57 tests PASS, compileall/pip check/기존 공정 비교 exit0. 원본 데이터·어댑터·기존 평가14개 SHA 모두 일치.
- `candidate-audit-v2.json`: target 계약 오류0, 새 묶음 내부 교차 계열/정확/유사 후보 충돌0. 그러나 검수12건 미완료·candidate 역할12건·이력 확인 미완료로 BLOCKED. 이 탐지 결과가 의미적 독립/라벨 정답 보증은 아니다.
- `gate-command-evidence-v2.json`: audit/freeze/A~F 비교의 예상 exit2 차단을 실제 수행. 학습 출력/예산 예약이 생기지 않음.
- `os-isolation-final.json`, `os-final-command.json`: 실제 서비스PID83039의 UID501 확인, 기존 test.jsonl의 서비스 읽기 성공, 다른 UID/볼륨/보호 권한 미충족. exit2=실제 차단 미충족이지 성공이 아님.
- `real-local-load-corrected.json`, `load-final-command.json`: 실제 MLX/기존56개 LoRA,6세션/동시12요청 중9건202→완료,3건429. 무인증/잘못된 키401, 타인 사건404, CSRF 누락403. 실제 호출9회, 입력1605/출력360 tokens.
- 같은 부하 실행의 큐 포함 작업 지연: p50 6.302s, p95 10.541s, max 11.012s.9개 timestamp를 보존하고 선형 보간 percentile로 집계했다. 짧은 기능 부하이며 지속 처리량/품질 지표가 아니다.
- `personal-browser-e2e-final.json`: 인증 후 실제 모델의 v1보류→v2충돌→v3유지, 인용/비교/미공개 자료 DOM 제외 PASS. 이번 인증 UI는 관측 폭592/607px에서 검증했다. 기존 합성 앱의304/1265px 검증은 이전 단계 기록이며 새 로그인의 모바일 검증으로 전용하지 않는다.
- `login-ui-proof.json`, `login-ui-contrast.json`: 오류 후 input 포커스·aria-invalid/설명 연결,48px 입력/버튼, 관측 폭에서 가로 넘침 없음, 입력 경계≥3:1·텍스트≥4.5:1. 광범위 스크린리더/브라우저 검증은 아님.
- `deletion-recovery/report.json`: 새 합성 DB에서 실제 CLI6명령, journal 없는 복구 exit2, 과거 백업 복구 시 삭제 사건/근거/작업/이벤트 없음·세션 폐기·다른 사건 보존·0600/integrity PASS. 원래 백업 바이트는 보존하며 물리 삭제를 주장하지 않음.
- `frontend-final-command.json`: npm build exit0. `login-detector.json`: 이번 로그인 범위1회 검사[]. 별도 읽기 전용 UI 검토의 경계 대비/오류 연결2개 수정.

## 실패 보존과 수정

1. HTTP Basic API 인증은 통과했으나 내장 브라우저 로그인 창이 동작하지 않아 폼+1시간 메모리 세션을 추가했다. Basic은 로컬 API 점검용으로만 남긴다.
2. 폼의 Origin:null 거부를 헤더 진단으로 확인했다. no-referrer가 비CORS POST의 Origin을 null로 만드는 [Fetch 표준](https://fetch.spec.whatwg.org/#origin-header)을 확인하고 same-origin referrer 정책으로 수정했다. null/교차 출처 요청을 허용해 우회하지 않았다. 진단 print는 최종 코드에서 제거했다.
3. 새 검수 묶음 v1의 [E1] 표기가 기존 평가기 E1: 계약과 달랐다. 이를 잡는57개 중1개 실패를 보존한 뒤 생성기/fixture를 수정해 새 v2를 만들었다. 초기 final-validation은 FAIL로 보존, retry1은57 PASS. 원본 묶음을 덮어쓰지 않았다.
4. 짧은 부하 보고서의 p95를 max로 집계한 오류를 발견했다. 기존 보고서를 보존하고 같은 실행의9개 영속 작업 timestamp·호출·토큰 합을 대조해 corrected 보고서를 생성했다. 추가 모델 호출 없이 집계만 정정했다. 이후 스크립트는 실제 percentile·job ID·원시 지연을 저장한다.

## 다음 입력과 사용

새 학습과 실제 판례 연결에 필요한 것은 실제 검수 담당자/자료/목적별 승인, 개발자가 보지 않은 최종 묶음, 분리된 서비스·평가 OS 사용자와 보호 볼륨이다. 관리자 인증은 비대화식 sudo에서 password required로 확인됐으며 비밀번호를 요청/수집/로그에 저장하지 않았다. 준비 절차와 재현 명령은 NEXT_PHASE_PROTOCOL.md에 있다.

현재 `make serve`로 개인 인증 서버를 유지한다. 주소는 http://localhost:8100 이며 접근키는 `runtime/personal-auth/key.txt`에 보관한다. 키를 채팅/URL/보고서에 붙여 넣지 않는다. 소스·비밀키·실행 결과를 외부에 push/배포하지 않았다.

유료 호출0, 공개 배포0, 실제 판결문 원문 외부 전송0. 새 학습0/3, 실제 A~F0/6. 독립 검수/OS 격리 미완료 때문에 PILOT_READY/PRODUCTION_READY로 승격하지 않는다.
