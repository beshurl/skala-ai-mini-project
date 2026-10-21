# 최종 구현 기준 코드 중심 5분 발표 진행표

8장, 총 300초. PPT 발표자 노트와 아래 멘트는 같은 원문을 사용한다. 입력 검증과 0토큰 확인은 최신 코드 결과이며, 추가 조사 6건은 입력 검증 도입 전 실제 모델 평가 기록이다.

| 슬라이드 | 시간 | 주제 | 우선 보여줄 코드 |
| --- | --- | --- | --- |
| 1 | 0:00~0:20 | 가설 기반 운영 진단 개선 | [agent/input_validation.py:19](</Users/beshu/Downloads/all_total_vue_student/agent/input_validation.py:19>) |
| 2 | 0:20~1:05 | LLM 호출 전 입력 검증 | [server.py:217](</Users/beshu/Downloads/all_total_vue_student/server.py:217>) |
| 3 | 1:05~1:45 | 입력 거절 5건과 0토큰 확인 | [tests/test_api.py:129](</Users/beshu/Downloads/all_total_vue_student/tests/test_api.py:129>) |
| 4 | 1:45~2:30 | 가설 조사 그래프의 반복 흐름 | [agent/graph.py:174](</Users/beshu/Downloads/all_total_vue_student/agent/graph.py:174>) |
| 5 | 2:30~3:20 | 추가 관측에 따른 가설 수정 | [agent/investigation.py:25](</Users/beshu/Downloads/all_total_vue_student/agent/investigation.py:25>) |
| 6 | 3:20~3:55 | 사실 검증과 별도 Judge 평가 | [agent/validation.py:25](</Users/beshu/Downloads/all_total_vue_student/agent/validation.py:25>) |
| 7 | 3:55~4:30 | 검증 결과와 실행 범위 | [tests/test_api.py:151](</Users/beshu/Downloads/all_total_vue_student/tests/test_api.py:151>) |
| 8 | 4:30~5:00 | 한계와 다음 개선 | [agent/input_validation.py:19](</Users/beshu/Downloads/all_total_vue_student/agent/input_validation.py:19>) |

## 1 가설 기반 운영 진단 개선  0:00~0:20

**발표 멘트**

이번 개선은 두 지점에 집중했습니다. 호출 전에는 불필요한 입력을 로컬 코드로 거절하고, 조사 중에는 최초 설명을 반박할 관측을 추가로 확인합니다. 입력 검증 코드와 가설 조사 흐름, 실제 검증 결과 순서로 설명하겠습니다.

**보여줄 동작**

표지에서 입력 검증과 가설 조사라는 두 변경점을 설명한다.

**코드 위치**

- [agent/input_validation.py:19](</Users/beshu/Downloads/all_total_vue_student/agent/input_validation.py:19>)  19~19행

- [agent/investigation.py:20](</Users/beshu/Downloads/all_total_vue_student/agent/investigation.py:20>)  20~20행

## 2 LLM 호출 전 입력 검증  0:20~1:05

**발표 멘트**

server.py의 execute 함수에서 그래프 실행 전에 validate_input을 호출합니다. 문자 정규화와 반복 입력, 운영 관련성을 로컬 규칙으로 검사하므로 검사 자체에 LLM이나 임베딩을 쓰지 않습니다. 실패하면 거절 응답을 보내고 return해 그래프와 대화 저장으로 진행하지 않습니다. 시스템을 선택해도 잡담은 통과하지 않으며, 시스템명과 맥락이 있는 짧은 답변은 보존합니다.

**보여줄 동작**

server.py 217행의 검사와 227행 return을 짚고, 아래 232행 그래프 호출보다 앞이라는 점을 보여준다. input_validation.py에서 짧은 답변의 맥락 조건을 확인한다.

**코드 위치**

- [server.py:217](</Users/beshu/Downloads/all_total_vue_student/server.py:217>)  217~232행

- [agent/input_validation.py:19](</Users/beshu/Downloads/all_total_vue_student/agent/input_validation.py:19>)  19~41행

## 3 입력 거절 5건과 0토큰 확인  1:05~1:45

**발표 멘트**

실제 Ollama가 연결된 서버에서 자음 입력과 날씨 질문 등 다섯 건을 보냈습니다. JSON과 GET·POST SSE 모두 거절 응답을 반환했습니다. 응답의 0토큰 값에 더해 LangSmith 원격 기록에서 LLM과 MCP 호출이 없는지도 확인했습니다. 거절한 문장은 대화 요약에도 저장하지 않습니다. 이 수치는 검사한 다섯 건의 생성 사용량이며 전체 비용 절감률은 측정하지 않았습니다.

**보여줄 동작**

저장된 실제 화면의 거절 이유와 0토큰을 보여준다. 여유가 있으면 실제 화면에서 payments-service를 선택하고 오늘 날씨 알려줘를 제출한다. 기존 장애 분석을 다시 실행할 필요는 없다.

**코드 위치**

- [tests/test_api.py:129](</Users/beshu/Downloads/all_total_vue_student/tests/test_api.py:129>)  129~155행

## 4 가설 조사 그래프의 반복 흐름  1:45~2:30

**발표 멘트**

입력을 통과하면 대상을 확인하고 지표와 로그를 병렬 조회합니다. RAG는 관측을 포함해 한 번 검색합니다. 이후 계획, 조회, 판정 노드를 반복합니다. 실제 LLM은 아직 수행하지 않은 허용 질문 하나를 선택하고, 코드는 대상과 수치, 동일한 5분 관측 구간을 검증합니다. 두 종류 관측이 한 가설을 지지하고 경쟁 가설이 반증되면 종료하며 최대 네 번까지만 조회합니다.

**보여줄 동작**

graph.py의 investigate_plan, investigate_probe, investigate_test 노드와 조건부 간선을 짚는다. investigation.py에서 허용 질문 enum과 종료 조건을 보여준다.

**코드 위치**

- [agent/graph.py:174](</Users/beshu/Downloads/all_total_vue_student/agent/graph.py:174>)  174~193행

- [agent/investigation.py:154](</Users/beshu/Downloads/all_total_vue_student/agent/investigation.py:154>)  154~170행

- [agent/investigation.py:134](</Users/beshu/Downloads/all_total_vue_student/agent/investigation.py:134>)  134~147행

## 5 추가 관측에 따른 가설 수정  2:30~3:20

**발표 멘트**

이 화면은 실제 모델로 실행해 저장한 요청량 사례입니다. 처음 CPU 91%와 중복 배치 경고는 같습니다. 그러나 배치의 CPU 기여가 5%여서 배치 가설을 반증했습니다. 요청 처리 기여 88%와 요청량 3.2배 증가가 함께 확인돼 요청량 가설을 교차 지지했습니다. 화면은 조사 이유와 사전 조건, 판단 전후를 보여줍니다. 자료가 충돌하면 원인별 조치를 보류하며, 교차 지지가 인과관계 확정을 뜻하지는 않습니다.

**보여줄 동작**

저장 화면에서 배치 반증, 요청량 교차 지지와 조사 이유를 차례로 짚는다. PROBES의 판정 조건과 adjudicate_investigation의 상태 갱신 코드를 연결한다.

**코드 위치**

- [agent/investigation.py:25](</Users/beshu/Downloads/all_total_vue_student/agent/investigation.py:25>)  25~39행

- [agent/investigation.py:285](</Users/beshu/Downloads/all_total_vue_student/agent/investigation.py:285>)  285~294행

## 6 사실 검증과 별도 Judge 평가  3:20~3:55

**발표 멘트**

최종 사실과 수치, 출처, 허용 조치는 코드로 검증합니다. 작성이 세 번 실패하면 모델 가설과 조치를 제외하고 확인 가능한 관측만 안내합니다. Judge는 별도 평가 경로에서 최종 답변과 원본 관측을 대조합니다. 평가자의 원인 모순 판정으로 점수 상한을 적용할 때도 원래 점수를 보존합니다. 매 채팅의 출력 통과 여부는 코드가 담당합니다.

**보여줄 동작**

validation.py의 facts 비교와 judge.py의 overall_scores 보존을 보여준다. 시간이 부족하면 코드 한 곳씩만 짚는다.

**코드 위치**

- [agent/validation.py:25](</Users/beshu/Downloads/all_total_vue_student/agent/validation.py:25>)  25~40행

- [agent/judge.py:85](</Users/beshu/Downloads/all_total_vue_student/agent/judge.py:85>)  85~102행

## 7 검증 결과와 실행 범위  3:55~4:30

**발표 멘트**

현재 코드는 테스트 99개를 통과했습니다. 최신 입력 거절 다섯 건은 생성 0토큰과 원격 호출 부재를 확인했습니다. 이전에 수행한 실제 가설 조사 평가는 기능 여섯 건을 통과했지만 Judge가 릴리스 답변을 잘못 감점해 종합 평가는 다섯 건 통과입니다. 이 점수는 수정하지 않았습니다. 실행 시점과 범위를 구분해 결과를 제시했습니다.

**보여줄 동작**

현재 입력 검증과 이전 추가 조사 평가를 나눈 표를 읽는다. release의 검토 필요 표시와 원격 실행 6건, 점수 30개 재조회 기록을 짚는다.

**코드 위치**

- [tests/test_api.py:151](</Users/beshu/Downloads/all_total_vue_student/tests/test_api.py:151>)  151~155행

- [evaluation/investigation.py:110](</Users/beshu/Downloads/all_total_vue_student/evaluation/investigation.py:110>)  110~112행

## 8 한계와 다음 개선  4:30~5:00

**발표 멘트**

입력 검증은 규칙 기반이므로 표현에 따라 오탐과 미탐이 생길 수 있습니다. 추가 조사는 CPU의 세 가설과 합성 관측을 사용하며 실제 원인을 증명한 것은 아닙니다. 다음에는 운영 데이터를 연결하고 사람 평가로 규칙과 Judge를 보완할 필요가 있습니다. 이번 구현에서는 입력 거절과 결론 보류도 근거를 보여주는 명시적인 동작으로 만들었습니다.

**보여줄 동작**

0토큰의 적용 범위와 실제 운영 데이터 연결 과제를 설명하고 종료한다.

**코드 위치**

- [agent/input_validation.py:19](</Users/beshu/Downloads/all_total_vue_student/agent/input_validation.py:19>)  19~19행

- [agent/investigation.py:20](</Users/beshu/Downloads/all_total_vue_student/agent/investigation.py:20>)  20~24행

## 시연 준비와 전환 순서

1. `bash sh/run_live.sh`로 서버를 켜고 에디터에서 server.py, agent/input_validation.py, agent/graph.py, agent/investigation.py, agent/validation.py, agent/judge.py를 미리 연다.

2. 슬라이드 2에서는 server.py의 입력 검사와 return, 그 아래 그래프 호출 순서를 짚는다. 전체 파일을 스크롤하며 읽지 않는다.

3. 슬라이드 3은 PPT의 저장된 실제 화면으로 설명한다. 실시간 시연을 넣으면 [실행 화면](http://127.0.0.1:8600/)에서 시스템 하나를 선택하고 `오늘 날씨 알려줘`만 제출한다. 0토큰 표시를 확인하고 즉시 PPT로 돌아온다.

4. 슬라이드 5는 저장된 실제 LLM 조사 화면을 사용한다고 말한다. 조사 전체 재실행과 Judge 재평가를 발표 중 실행하지 않는다.

5. 슬라이드 7에서 99개 테스트, 최신 입력 거절 5건, 이전 가설 조사 6건의 실행 범위를 구분한다.

## 질문 대비

- 0토큰은 차단한 요청의 생성 모델 입력·출력 사용량이다. 전체 서비스 비용 절감률과 API 달러 절감액은 측정하지 않았다.

- 거절 입력은 SQLite 대화와 요약에 저장하지 않으며 현재 화면에서 수정할 수 있다. 정상 조사와 원래 질문은 유지한다.

- 실제 검증 모델은 Ollama의 qwen3.5:2b이고 별도 Judge는 qwen3:8b다. OpenAI는 설정으로 지원하지만 이번 실측에 사용하지 않았다.

- 추가 조사는 CPU 80% 이상 인시던트에 적용한다. 상세 합성 관측은 payments-service에 제공하며 세 가설과 네 질문을 미리 정의했다.

- 교차 지지는 인과관계 확정이 아니다. 완료 결과 복원은 실행 중 그래프 체크포인트 재개와 다르다.

- 실제 Judge의 release 오판으로 종합 5/6을 유지했다. 기능 6/6과 구분해 설명한다.
