# 발표 자료 출처

## 전체 아키텍처

- 저장소 구현을 바탕으로 구성·배치·연결선·문구를 직접 제작했다.
- [발표 PPT](../운영진단_에이전트_5분발표.pptx)의 **3번 슬라이드**가 편집 원본이다. 8개 도형과 연결선을 각각 수정할 수 있다.
- [PNG 미리보기](architecture-overview.png)는 동일한 전체 구조이며 확대 없이 한 장으로 제시한다.

## 실제 실행 화면과 기록

- 표지는 [Ollama 진단 화면](../../../artifacts/screenshots/live-diagnosis-desktop.png)을 사용했다.
- 5번은 [실제 조사 화면](../../../artifacts/screenshots/investigation-traffic-desktop.png)의 결과 영역을 발췌했다. 배치 반증과 요청량 교차 지지를 그대로 보여준다.
- 6번 비교는 [실행 결과 발췌](execution-evidence.json)와 [고정 관측 데이터](../../../data/investigation_cases.json)의 batch·traffic 사례다.
- 9번은 [2026-10-22 프론트 원본 PNG](live-validation-20261022.png)의 보고서 검증 영역을 사용했다. [동일 실행 로그](live-validation-20261022.json)의 작성 2회·재작성 1회·검증 통과와 일치한다. 1차 불합격 사유는 저장된 이벤트 근거이며 화면은 최종 상태다.
- 10~11번의 Judge·LangSmith 결과는 [2026-10-21 평가 원본](../../../artifacts/investigation_evaluation.json)을 사용했다. 9번의 재실행에서 Judge·추적 재검증을 했다고 설명하지 않는다.
- [기능별 실행 안내](../EXECUTION_EXAMPLES.md)에 입력·처리·출력과 원본 출처를 정리했다.

## 기술 설명과 해석 범위

- 4번의 CPU 작업 기여 70% 기준은 [조사 정책](../../../agent/investigation.py)의 사전 조건이다.
- 3·7~8번은 [전문 서브그래프](../../../agent/specialists.py), [MCP](../../../mcp_server.py), [벡터 인덱스](../../../agent/retrieval.py), [의존성 주입](../../../agent/deps.py)의 실제 역할을 반영했다.
- 자료는 12장·330초 구성이다. 이번 페이지 확장에서 모델 평가나 테스트를 새로 실행하지 않았다. 지표·로그·추가 관측은 교육용 합성 데이터이며 교차 지지는 인과 확정과 구분한다.

## 이전 상세 시안

[기존 SVG](architecture-overview.svg)는 기술 로고를 포함한 이전 상세 시안이며 최신 발표 구조와 구분한다. 해당 시안의 브랜드 로고는 [Simple Icons](https://github.com/simple-icons/simple-icons), CC0-1.0에서 가져왔고 상표권은 각 소유자에게 있다. LangSmith 옆 추적 아이콘은 직접 제작했다.

## 저장소 구현과 대응

| 영역 | 근거 코드 |
| --- | --- |
| Vue 화면과 SSE | [app.js](../../../frontend/app.js), [웹 프록시](../../../web_demo_server.py) |
| FastAPI와 공통 입력 검사 | [server.py](../../../server.py), [input_validation.py](../../../agent/input_validation.py) |
| LangGraph·전문 조회·가설 조사 | [graph.py](../../../agent/graph.py), [specialists.py](../../../agent/specialists.py), [investigation.py](../../../agent/investigation.py) |
| MCP와 RAG | [mcp_server.py](../../../mcp_server.py), [retrieval.py](../../../agent/retrieval.py) |
| LLM·품질 평가·추적 | [llm_runtime.py](../../../agent/llm_runtime.py), [judge.py](../../../agent/judge.py), [observability.py](../../../agent/observability.py) |
| SQLite 완료 결과·맥락 | [session_store.py](../../../agent/session_store.py) |

관측은 교육용 합성 데이터다. 실제 계획·작성과 별도 Judge는 Ollama로 측정했다. OpenAI는 연결 지원 사항이며 보존 실측 결과에 사용하지 않았다. 완료 기록과 후속 맥락을 복원하며 실행 중 그래프 재개는 지원하지 않는다.
