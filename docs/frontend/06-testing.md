# 검증 결과

근거 run: `outputs/runs/20261020T150415+0900-frontend-admin/`. 명령·시각·종료코드는 JSON, 원시 출력은 log에 보존한다. 성공과 실제 MLX 미완료를 분리한다.

가장 최신 최종 검증은 seal-checks.json/seal-*.log다. backend104(8.43초), Node5, typecheck/build/compileall/pip check/diff check 전부 exit0, 원본14개 SHA 보존. 아래 과정별 결과는 당시 실행 이력으로 유지한다. MCP 도구별 count/success/mean/P95의 실제 집계와0호출의 null 성공률도 테스트했다.

최종 빌드의 브라우저 재검증은 seal-browser.json: 전체 fixture 흐름과 과거 v1 기록 선택 PASS. seal-mcp-ui.txt에는 get_public_case/search_case_evidence 각10회 실측, read_evidence/참고 판례 도구0회·성공 데이터 없음·평균 미측정을 확인한 화면 텍스트를 보존했다. 최종 desktop/mobile 캡처는 같은 최신 빌드다.

| 검증 | 결과 | 근거 |
|---|---|---|
| 백엔드 전체 회귀 | PASS 104개 | final-backend-validation/T01.log, summary.json; 마지막 취소 집계 수정 후 v2 별도 실행 |
| compileall / pip check / 기존54건 비교 | PASS exit0 | 같은 validation T02~T04. 새 모델 평가 아님 |
| 기존 데이터·어댑터·평가14개 SHA | PASS 전부 일치 | validation summary original_artifacts_preserved |
| vue-tsc | PASS exit0 | final-frontend-checks.json / typecheck.log |
| Node API·랜딩 단위 | PASS 5개 | final-frontend-tests.log. 취소/timeout/무자동재시도, 오류, reduced-motion/수명주기/탭순서 |
| Vite production build | PASS | final-frontend-build.log; notice CSS 조정 후 build-after-notice-style.log |
| 사용자 전체 desktop | PASS, fixture 한정 | fixture-browser.json. 실제 HTTP/SQLite/stdio MCP, v1보류→v2충돌→v3유지, 원문/비교 |
| 사용자 전체390px | PASS, fixture 한정 | fixture-mobile-browser.json; document width375/scrollWidth375 |
| 랜딩 | LOCAL_VALIDATED | 원본 문/탐정/배경/보드/갤러리/모달/ESC/CTA를 CUA로 확인. landing-mobile.png, 최종 screenshots |
| 관리자 역할·CSRF·실측 로그 | PASS | test_admin.py 8개 및 preview-integration-performance.json: 사용자403, 별도 admin 로그인, HTTP/LLM/RAG/MCP/system 같은 요청·분석 ID |
| 관리자 UI | LOCAL_VALIDATED | 로그인/모델/검색 상세4문서·점수/분석 흐름6기록/도구 목록/오류코드/검색 빈 결과/페이지26–50/시스템. 390px 가로 넘침 없음 |
| 실제 기존 UID499 MLX 신규 UI 전체 | INCOMPLETE | live-mlx-observed.json, live-mlx-pending.png. model_started 이후180초 초과 미종료; 취소1회 요청. 자동 분석 재시도0 |
| 현재 OS 정답 접근 거부 재검사 | NOT_RUN | 현재 작업은 프론트·관측. 기존 격리 경계/운영 파일 변경0 |
| 실제 운영 사본 반영 | NOT_RUN | 8100의 별도 코드 사본/credential/launchd 교체0 |

`browser_e2e.mjs`는 기본 backend=mlx를 유지하며 실제 어댑터를 UI로 확인한다. fixture는 명시적 인자로만 실행한다. CUA locator의 대기 제한 때문에 실제 모델 완료 대기 자동 검증이 먼저 종료됐지만, 이후 관측에서도 모델 작업은 종료되지 않았다. 도구 대기 실패를 모델 성공으로 해석하지 않았다.

브라우저 reduced-motion 시각 에뮬레이션은 NOT_RUN이다. Node의 독립 DOM stand-in에서 해당 분기의 콘텐츠/inert/무이동/정리를 검증했고 실제 desktop/mobile의 기본 연출을 별도 확인했다. 프레임률·보조공학·다른 브라우저 광범위 검증은 NOT_RUN이다.

실제 MLX의 최종 관측은 live-mlx-final-observed.json/live-mlx-final.png다. 15:28 CANCELLED를 확인했고 live-final-health.json의 /ready200 및 같은 UID499/PID41133도 확인했다. 실제 성공 분석은 검증하지 못했지만 실행 중인 검증 작업을 취소 요청 상태로 방치하지는 않았다. 마지막 UI 수정은 초기 세션 확인도 공통15초 timeout을 사용하도록 한 것이다.

사이드 대화의 에이전트 제한에 따라 별도 리뷰어를 호출하지 않고, 구현을 마친 뒤 렌더·권한·집계 정의를 별도 순서로 재검토했다. 디자인 검출의 유일한 경고(상태 안내 왼쪽 두꺼운 테두리)는 일반 경계선으로 수정했다. 검출 결과 파일은 당시 그대로 보존하고 반복 실행하지 않았다.
