# 측정 범위

2026-10-20 15:23:38 KST. 이 Mac/UID501, Python httpx 지속 연결 → loopback8123의 명시적 fixture 서버 → 실제 SQLite·stdio MCP. 관측 보관223개 시점. 각 endpoint20회 연속 GET의 **client wall time**이다. 주어진 로컬 검증 표본이며 운영 용량이나 실제 MLX 지연을 뜻하지 않는다.

| 대상 | 표본 | 평균 | P50 | P95 |
|---|---:|---:|---:|---:|
| GET /api/admin/logs 기본50개 | 20 | 2.63ms | 2.48ms | 2.94ms |
| GET /api/admin/summary 기본1시간 | 20 | 2.19ms | 2.00ms | 2.73ms |

명령/시각/모든 원시 표본/계산법은 preview-integration-performance.json과 verify_preview.py. P95는 nearest rank, P50은 Python median이다. 대시보드 자체 집계의 P50은 nearest rank이므로 짝수 표본에서는 정의가 다를 수 있다.

변경 전 같은 조건의 API baseline은 없다: **NOT_MEASURED**. 속도 개선 비율을 주장하지 않는다. 랜딩 LCP/CLS/INP, FPS/프레임 드롭, 실제 사용자 INP, chart rendering 지연, 지속 부하, CPU/메모리 집계는 **NOT_MEASURED**다.

원본13개 raster 인스턴스(고유12개)+inline SVG를 바이트/해시 보존했다. inline base64 중복을 별도 자산 파일로 추출했으며 페이지 체감 속도 개선 수치로 바꾸지 않는다. JavaScript 최초 앱 chunk는 약72.79kB(gzip28.75kB), 랜딩은 별도 lazy chunk 약15.93kB(gzip6.46kB), 최종 빌드 로그를 따른다. 이미지 요청량·디코딩 비용은 남는다.

랜딩은 스크롤/포인터 변화가 정착하면 rAF 재예약을 멈추고, 해제 시 모든 이벤트와 frame을 정리한다. 이는 단위 검증 결과이며 FPS 측정값이 아니다. 기존 UID499 실제 모델 요청은 결과 미반환으로 정상 추론 지연을 산출하지 않았다.
