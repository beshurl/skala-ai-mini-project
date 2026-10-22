# 아키텍처 이미지 출처와 사용 범위

- 전체 구성·배치·연결선·설명 문구: 이 저장소 구현을 바탕으로 직접 제작.
- 이미지 편집 원본: [architecture-overview.svg](architecture-overview.svg)
- 고해상도 PNG: [architecture-overview.png](architecture-overview.png), 4800 × 2701.
- 기술 로고: [Simple Icons](https://github.com/simple-icons/simple-icons), CC0-1.0. Vue.js, FastAPI, Python, LangGraph, Model Context Protocol, NumPy, Ollama, SQLite 아이콘을 사용했다. 각 브랜드의 상표권은 해당 소유자에게 있다.
- LangSmith 옆의 선형 추적 아이콘: 직접 제작한 일반 추적 기호이며 공식 로고로 표시하지 않는다.
- 참조한 사용자 예시는 시각적 배치에만 활용했다. 예시의 AWS·React·Spring·Netlify 등은 우리 프로젝트 기술로 넣지 않았다.

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
