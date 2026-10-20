# 데이터 출처·이용·검수

2026-10-20 KST. 실제 판결문 수집 건수0. 자동 생성한 자료를 실제 수집으로 보고하지 않는다. 유료 API/원문 외부 LLM 전송/공개 배포 예산은 승인 전0이다.

## 자료 구분

| 자료 | 목적/상태 | 접근 경계 |
|---|---|---|
| 기존 data/processed, data/mlx | 합성 파이프라인/노출된 개발 평가 | 오프라인 학습·평가기 전용, 원본 해시 보존 |
| 서비스용 합성 사건 | 데모 흐름 검증, 자동 생성 시 synthetic_fixture 명시 | runtime SQLite의 owner 필터와 공개 버전 적용 |
| 실제 판결문/사용자 TXT·HTML·PDF | 승인된 로컬 반입 후 QUARANTINED | 사람 검수 및 이용 목적별 승인 전 학습/검색에 연결하지 않음 |
| 참고 판례 코퍼스 | BLOCKED, 현재 없음 | MCP는 BLOCKED+빈 hits로 보고하며 샘플 판례로 대체하지 않음 |
| 최종 평가 정답 | 현재 독립 최종셋 없음 | 향후 별도 OS 계정/볼륨으로 격리 필요 |

현재 코드의 논리적 경계는 서비스가 평가 파일을 import/검색하지 않고 MCP에 파일/정답 읽기 도구를 제공하지 않는 방식이다. 같은 macOS 사용자 계정이 파일을 읽을 수 없도록 하는 OS 수준 격리는 아직 구현하지 않았다. 실제 자료를 다루는 파일럿 전 필수 과제다.

## 공식 출처 확인

- [법제처 OPEN API 가이드](https://open.law.go.kr/LSO/openApi/guideList.do)는 판례 목록/본문 제공 항목을 안내한다. [OPEN API 신청](https://open.law.go.kr/LSO/openApi/cuAskList.do)은 이번 확인에서 로그인으로 연결되었다. 인증 정보/목적별 이용 조건이 확보되지 않아 실제 수집 어댑터는 실행하지 않았다. 요청/응답 필드는 추측해 구현하지 않았다.
- [법원 판결서 이용안내](https://www.scourt.go.kr/portal/information/finalruling/guide/guide_02.jsp)는 열람 절차를 안내한다. 이 열람 경로를 무제한 학습·재배포 허용으로 해석하지 않는다. 수수료 결제·인증 우회·자동 대량 열람은 실행하지 않았다.
- 모델의 공개 카드 [MLX Qwen3-4B-4bit](https://huggingface.co/mlx-community/Qwen3-4B-4bit), [Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B)는 Apache-2.0으로 표시한다. 실제 사용 revision은 로컬 manifest에 별도로 고정한다. 모델 라이선스와 판결문/학습 데이터 이용 권한은 별개다.
- 참고 학생 프로젝트에 명시 라이선스가 없어 소스 복제/재배포를 하지 않았다. 아키텍처 패턴만 참고했다.

## 로컬 반입 계약

`scripts/ingest_judgments.py`는 TXT/HTML/PDF, 최대8MiB/파일, 한 번에 최대1000건(기본100), dry-run, 명시적 resume, raw/clean SHA-256 중복 방지, 인코딩 UTF-8/CP949 및 NFC, 문단/페이지 단위 정제 위치, 파싱 실패 격리를 지원한다. HTTP 요청과 URL fetch를 하지 않는다. 경로 탈출/심볼릭 링크/알 수 없는 확장자를 거부한다.

`data/rights_manifest.v2.example.json`의 processing/training/rag/display/redistribution은 서로 독립이다. 예시는 모두false. 과거 blanket permission_confirmed만으로 수집이나 학습을 허용하지 않는다. 처리 허용과 권리 근거가 있어도 출력은 항상 QUARANTINED, privacy_review.human_reviewed=false, label_review.human_reviewed=false다.

`approved_for(document,use)`는 목적별 permission, APPROVED_FOR_SPECIFIC_USE 상태, 실제 사람 검수/검수자 필드를 함께 요구한다. 에이전트가 사람 검수 완료를 기록하는 승인 경로는 만들지 않았다. 승인 워크플로와 실제 자료 반입은 담당자의 검수와 정책 입력이 필요하다.

전화/이메일/주민번호 패턴 마스킹은 일부 탐지일 뿐 완전한 비식별화가 아니다. 인명·주소·희귀 사실·사건번호·간접 식별자와 OCR의 숫자/시간/부정 표현은 사람이 확인해야 한다. 스캔 PDF는 자동 OCR하지 않고 저텍스트/OCR 필요 상태로 격리한다. 청크 start/end는 **정제 텍스트**의 위치이며 원문 PDF byte offset이 아니다. 원문 해시와 페이지를 보존한다.

## 보존과 삭제

원본 학습 데이터·어댑터·평가 결과는 감사 백업으로 보존했다. 서비스 DB와 백업은 mode0600이고 runtime은 Git 제외다. 원문이나 세션 자격정보를 외부 로그로 보내지 않는다. SSE/audit에는 ID·상태만 남긴다. 세션은24시간 만료되며 자동 자료 삭제/보존기간 정책은 별도 담당자 결정 전 구현하지 않았다. 새 합성 데모는 이전 DB 자료를 삭제하지 않는다.

실제 문서 삭제 시 원문/정제본/파생학습본/검색 인덱스/캐시를 함께 추적해야 한다. 현재 실제 판례 인덱스·결과 캐시는 비활성이다. 승인 자료를 연결하기 전 삭제·보존 정책과 복구 후 삭제 반영 시험이 필요하다.
