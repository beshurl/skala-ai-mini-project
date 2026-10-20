# 기존 프로젝트 감사

2026-10-20 KST. 대상 `/Users/beshu/Downloads/recase_macos_16gb`, 읽기 전용 참고 `/Users/beshu/Downloads/all_total_vue_student`.

## 보존 및 환경

원본 파일 27개를 `outputs/runs/20261020T122029+0900-audit/original_project.tar.gz`와 `original_manifest.json`으로 보존했다. 데이터·기존 평가·어댑터 14개 파일은 작업 후 SHA-256이 모두 일치한다. 프로젝트에 독립 .git이 없어 상위 홈 Git과 분리된 로컬 저장소를 만들었다. 기준 커밋 `35bfb54`, 브랜치 `codex/recase-local`. 참고 프로젝트는 수정하거나 복사하지 않았다.

실측: Apple M5, arm64 네이티브, 16GiB 통합 메모리, macOS 26.5.2, Python 3.11.15. MLX 0.32.4 / MLX-LM 0.32.2 / Transformers 5.20.2. 최초 여유 디스크 478GiB. 모델 캐시 4B/4-bit/group64, revision `4dcb3d101c2a062e5c1d4bb173588c54ea6c4d25`. 네트워크는 공식 문서와 패키지 설치에 사용했고 모델은 오프라인 캐시만 재사용했다. 세부 환경/메모리는 `environment-after.json`.

## 기존 작업 판정

| 대상 | 판정 | 근거와 남은 한계 |
|---|---|---|
| Python/MLX 환경 | 재사용 가능 | 기존 venv와 캐시 정상. app 의존성만 추가, 별도 clean venv 재설치 검증 |
| 360건 합성 데이터 | 제한적 재사용 | train252/val54/test54. 3개 템플릿의 파이프라인 검사용 |
| 독립 평가 분할 | 수정 필요 | 분할 간 공통인 고유 prompt 문자열은 train↔val10, train↔test9, val↔test6개. test54건 중18건의 prompt가 train에 있음. 모든 분할에 정규화 템플릿3개 반복 |
| 4B 학습 | 재사용 가능 | 추가 사용자 로그에서 100/100 완료, 8 layers/rank8, trainable3.670M/4022.468M 확인 |
| 검증 손실 | 참고 기록 확인 | 사용자 로그 iter1=3.108, iter100 표시0.000. 반올림된 값이며 원시 수치/별도 로그 없음 |
| 기존 어댑터 | 로딩 재사용 가능 | safetensors/config 보존, 이번 실행에서 56개 LoRA 모듈과 adapter_loaded=true 확인 |
| 기존 Base/FT 15건 | 역사적 개발 결과 | 추가 로그에서 양쪽 모두 4B 명시. 파일 수치 일치. 당시 revision/생성 sampler/코드 해시 미기록 |
| 기존 평가기 | 수정 필요 | JSON 일부 추출로 label만 인정, citation/ID 검증 부족, 출력 덮어쓰기, 모델 기본값0.6B |
| 기존 비교기 | 수정 필요 | 조건 확인 없이 수치만 비교함. 새 비교기는 모델·데이터·설정 불일치 거부 |
| 학습 재실행 | 보류 | 어댑터가 사용 가능하고 데이터 누수가 발견되어 재학습 이점 없음. 새 학습0회 |
| 참고 Vue/Agent | 패턴 참고 가능 | FastAPI 싱글턴, stdio MCP, Vue/SSE 패턴 확인. 명시 라이선스 미발견으로 코드 복제 없음 |
| 실제 판결문 | 확인 불가/BLOCKED | 입력 자료, 용도별 이용 승인, 개인정보/라벨 사람 검수 없음 |

## 추가 사용자 로그의 지위

추가 첨부 `cb4f560b-…/붙여넣은 텍스트.txt`는 사용자의 명시대로 **참고 기록**이다. 명령을 재실행하지 않았다. source/hash와 확인한 정보만 `supplemental_user_log.json`에 기록했다. 이 기록으로 기존 모델 저장소명과 학습 완료/검증 손실의 확인 상태를 갱신했다. 평가 코드 기본값0.6B 결함은 실제 기존 실행이0.6B였다는 뜻이 아니다.

## 평가셋과 템플릿

기존 test는 이미 결과가 사용자와 개발자에게 노출됐고 템플릿 중복도 있어 개발용 평가셋이다. 최종 블라인드 평가셋이 아니다. 입력에 ground_truth가 노출된 문제와 분할 간 같은 프롬프트가 반복된 문제를 구분한다. 현재 확인한 결함은 후자이며 새 독립 사건/시나리오/문서 계열 분할이 필요하다.

실제 토크나이저 측정 v3: 입력 중앙값140/p95 148, 정답49/p95 54, full training template195/p95 199, max199, 768 초과0/360. 처음 v2 검사는 Transformers5의 BatchEncoding key 개수를 토큰 수로 잘못 세어 INVALIDATED했다. return_dict=False로 수정하고 별도 v3 결과를 남겼다. 관련 회귀 테스트를 추가했다. 역사적 thinking flag/hash는 기록되지 않아 완전한 과거 재현을 보증하지 않는다.

## 재사용 결정

기존 모델·어댑터를 제한된 합성 데모에서 사용한다. 학습을 반복하지 않는다. 기존 원본과 새 평가를 분리하고, 새로운 고정54건 Base/FT 실행을 기록했다. 일반화 학습/최종 비교/공개 배포는 누수 없는 검수 데이터와 운영 검증 확보 후 별도 판정한다.
