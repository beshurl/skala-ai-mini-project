# 아키텍처 자료 출처

## 최신 핵심 구조

- 전체 구성·배치·연결선·설명 문구는 이 저장소 구현을 바탕으로 직접 제작했다.
- 편집 원본은 [발표 PPT](../운영진단_에이전트_5분발표.pptx)의 **5번 슬라이드**다. 8개 도형과 연결선을 각각 수정할 수 있다.
- [PNG 미리보기](architecture-overview.png)는 같은 전체 구조의 정지 화면이다.
- 최신 PPT의 아키텍처는 확대 없이 한 장에 제시한다.
- 표지와 4번은 [Ollama 진단](../../../artifacts/screenshots/live-diagnosis-desktop.png), [가설 조사](../../../artifacts/screenshots/investigation-traffic-desktop.png)의 저장된 실행 화면이다.
- 3번의 비교 수치는 [고정 관측 데이터](../../../data/investigation_cases.json)와 [실제 LLM 평가 기록](../../../artifacts/investigation_evaluation.json)의 batch·traffic 사례를 사용했다. 관측은 교육용 합성 데이터이며 모델 선택·작성·평가는 실제 Ollama 실행이다.

## 실행 결과 발췌

- 3번의 질문·답변과 이전 재작성 사례의 이벤트는 [실행 결과 발췌 JSON](execution-evidence.json)의 실제 LLM 기록이다. 이벤트 요약은 원래 판정과 재작성 횟수를 보존했다.
- 7번 개별 Judge 점수와 원격 추적 확인은 [가설 조사 평가 원본](../../../artifacts/investigation_evaluation.json)을 사용했다. 다른 시기의 12건 평가 화면과 혼합하지 않았다.
- [기능별 실행 결과 안내](../EXECUTION_EXAMPLES.md)에 입력·처리·출력과 원본 출처를 정리했다.

## 6번 실제 프론트 캡처

- [프론트 원본 PNG](live-validation-20261022.png)는 2026-10-22 실제 Ollama qwen3.5:2b로 질문을 보내고 완료된 화면을 캡처했다. PPT에는 보고서 검증 영역을 확대 배치했다.
- [같은 실행의 검증 로그](live-validation-20261022.json)에 질문·기록 ID·모델 사용·1차 불합격 사유·2차 통과를 보존했다.
- 화면의 여섯 검사 항목과 작성 2회·재작성 1회가 SQLite 결과와 일치한다. 7번의 이전 Judge 평가와 구분하며, 이번 캡처에서 Judge 재평가나 원격 추적 재조회는 하지 않았다.

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
