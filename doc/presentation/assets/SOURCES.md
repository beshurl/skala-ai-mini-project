# 아키텍처 자료 출처

## 최신 핵심 구조

- 전체 구성·배치·연결선·설명 문구는 이 저장소 구현을 바탕으로 직접 제작했다.
- 편집 원본은 [발표 PPT](../운영진단_에이전트_5분발표.pptx)의 **5번 슬라이드**다. 8개 도형과 연결선을 각각 수정할 수 있다.
- [PNG 미리보기](architecture-overview.png)는 같은 전체 구조의 정지 화면이다.
- 최신 PPT는 로고 그림이나 확대 화면을 사용하지 않는다.

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
