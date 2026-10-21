# 공개 사건 자료 수집·전처리 — 2026-10-21

사용자 요청으로 인증정보 없이 접근 가능한 공식 자료를 코드 프로젝트 밖의 개인 폴더에 수집했다. [검수 시작 안내](/Users/beshu/RECASE_data_vault/collections/20261021T092855+0900-public-case-collection-438022/START_HERE.md), [최신 집계](/Users/beshu/RECASE_data_vault/collections/20261021T092855+0900-public-case-collection-438022/versions/prepared-v3/audit.json), [실행 결과](../outputs/runs/20261021T092855+0900-public-case-collection-438022/RESULT.txt).

## 확보 범위

| 공식 출처 | 확보한 자료 | 범위/한계 |
|---|---:|---|
| FBI 공개 API | 공고1,266개/64페이지 | 수배·실종·정보 등 전체 반환 목록. 미제사건1,266건이 아님 |
| SafetyDream | 공개 실종 공고10개 | 표시 총계0과 카드10 불일치. 전체/장기 미제 목록으로 계산하지 않음 |
| FBI·DOJ 사건 경과 | 7문서/6계열 | 유죄 판결 보도4계열·체포 보도1계열·피해자 신원 확인1계열. 사람 미검수 |
| DOJ 종결 검토 목록 | 고유128개 사건 페이지 | 제목 정렬11페이지·128 Results 대조 |
| 위 목록의 직접 연결 원문 | PDF58개/748쪽 | 보고서·부록 포함. 텍스트가 적은13쪽은 원문/OCR 검수 필요 |

합계1,469개 공고/문서이며 독립 사건 수가 아니다. 영어 추정1,459/한국어 추정10이며 번역하지 않았다. 정확 중복 사본3개를 보류한 검수 후보1,466개, 유사 중복48쌍을 기록했다. 의미 중복·서로 다른 출처의 같은 사건 계열은 사람 검수 전 독립 자료로 세지 않는다. 새 검수 완료/학습 적격 자료는0건이다.

사건 당시 입력과 결과 참고표를 분리했다. 2016년 공고에2018년 체포 소식이 추가된 페이지, 사후 회고 자료, 게시/생성/수정일 불일치를 검수 표시했다. 판결 전/해결 전 입력 후보2개도 역사적 스냅샷 미확인으로 전부 부적격이다. Seale의 기소→유죄 평결 보도는 동일 계열이며 범인 예측 과제가 아니다. DOJ 행정적 종결·체포·신원 확인을 유죄 확정/사건 해결로 합치지 않는다.

## 저장·검수

원문은 별도 저장소의 raw/, 페이지별 PDF 텍스트는 quarantine/pdf-text/, 최신 정리본은 versions/prepared-v3/에 있다. URL·시각·상태·SHA256·원문 경로를 기록하고 기존 결과를 덮어쓰지 않았다. 초기 루트 정리본과 prepared-v2는 중간 결과로 보존하므로 최신 집계로 사용하지 않는다.

파일0600/폴더0700의 개인 로컬 폴더이며 **별도 암호화 볼륨이 아니다**. 현재 UID499가 신규 정답 파일을 읽지 못하는지에 대한 실제 OS 재검증은 NOT_RUN이다. 일부 연락처 마스킹은 완전 비식별화가 아니므로 서비스 반입/검색/표시/학습 승인을 생성하지 않았다.

최신 review/queue.jsonl에 목적별 권리·개인정보·라벨·사건 계열 검수 양식, review/sparse-pdf-pages.json에13쪽 원문 안내를 준비했다. AI 참고 라벨은 evaluation/reference-proposals.jsonl에 입력과 분리했으며 사람 정답이 아니다. 양식의 boolean/문자열 변경으로 기존 ledger·동결·OS·최대3후보 gate를 대체하지 않는다. 공개 NLI450건의 AI 위임 검토를 신규 실제 사건으로 확대하지 않았다.

NamUs CSV·SafetyDream API·법제처 판례 API는 계정/본인인증/신청키가 없어 미수집이다. 국가기록원은 공개 목록2개만 확보했고 비공개 수사기록 원문을 취득하지 않았다. FBI 옛 아카이브2주소와 Contra Costa1주소는 robots403으로 수집하지 않았다. Seale 자료는 접근 가능한 DOJ 공식 원문으로 별도 확보했다. 인증 우회·가입 대행·유료 호출·공개 배포·미공개 원문 외부 전송은0이다.

## 검증과 상태

[전체 백엔드 검증](../outputs/runs/20261021T092855+0900-public-case-collection-438022/verification.json)은244 tests/compileall/pip check exit0, 후속 자료 처리 변경의 [최종 검증](../outputs/runs/20261021T092855+0900-public-case-collection-438022/verification-final.json)은29 tests/compileall/데이터 감사 exit0이다. [데이터 감사](../outputs/runs/20261021T092855+0900-public-case-collection-438022/data-quality.json)의 원문 해시·이력 chain·고유ID·입력/참고표 분리·격리·파일권한·목록 건수9검사는 PASS다. PDF1쪽을 로컬 렌더링으로 점검했으며 전체748쪽의 내용/가림 처리/레이아웃 검수를 완료한 것은 아니다.

**모델 평가·새 학습 NOT_RUN, 실제 사건 정확도/해결률 NOT_MEASURED**다. 목적별/개인정보/라벨/계열 사람 검수·독립 당시 입력·신규 정답 OS 접근 거부 증명·동결 주기·빈 모델 잠금이 남아 있다. 신규 코퍼스는 기존 학습기의 검수 완료 입력으로 연결하지 않았다. 학습 후보 소비0/3, 서비스 반입0, 사람 승인 생성0이다. 기존 데이터/어댑터/평가15개·NLI 노출884 SHA·UID499 PID41133/41754·공유 model.lock inode25076574 보존은 [별도 확인](../outputs/runs/20261021T092855+0900-public-case-collection-438022/preservation.json)했다.

추가 도구는 backend/scripts/collect_public_cases.py, collect_closing_documents.py, prepare_public_cases.py, audit_public_cases.py다. 앱 API·프론트·운영 DB·실제 모델 프로세스를 변경하지 않았다. 기존 수집본에 다시 쓰는 실행은 거부하며 새 수집은 새 디렉터리에 저장한다.

공식 출처: [FBI API](https://www.fbi.gov/wanted/api), [FBI 이용 정책](https://www.fbi.gov/privacy-policy), [DOJ 종결 검토 목록](https://www.justice.gov/crt/civil-rights-division-emmett-till-act-cold-case-closing-memoranda), [NamUs FAQ](https://namus.nij.ojp.gov/frequently-asked-questions), [SafetyDream 공개 목록](https://www.safe182.go.kr/home/lcm/lcmMssList.do), [법제처 API 안내](https://open.law.go.kr/LSO/openApi/guideList.do).
