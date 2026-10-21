# RE:CASE 프론트엔드

계정 개편 후 최신 검증은14 tests·typecheck/build·브라우저 가입/로그인/기록 보존·일반 계정 운영자 차단·320/390px 폼입니다. [현재 인증 안내](../docs/AUTHENTICATION.md). 아래12 tests/이전 모바일 미실행 표시는 그 당시의 lifecycle 범위 이력입니다.

사건 상세의 '사건 관리'에서 종료/재개·보존 보류/해제와 필수 사유를 입력합니다. 증거 버전/revision 충돌·지연 응답·이중 제출을 막고 오류 뒤 사유를 보존합니다. 종료 후 새 분석/증거 공개는 잠그며 기록은 열람합니다. SPA 사건 전환은 제목/H1 focus를 갱신합니다. [검증 근거](../outputs/runs/20261020T164135+0900-lifecycle-ui-9152c8/RESULT.txt): typecheck·12 tests·build·fixture1265×720 실제 키보드/두 탭 충돌·기존 분석/인용/비교 회귀 PASS. 실제 모바일/VoiceOver/확대/다른 브라우저는 NOT_RUN, UID499 운영 배포0입니다.

Vue 3 화면과 브라우저용 자산을 모은 폴더입니다.

- `src/`: Vue 컴포넌트·스타일
- `public/`: 정적 이미지 자산. 로그인/회원가입은 `src/views/AuthView.vue`가 담당합니다.
- `scripts/browser_e2e.mjs`: CUA 브라우저 통합 검증
- `vite.config.js`: 로컬 백엔드 프록시

이 폴더에서 실행합니다.

```bash
npm ci
npm run dev
```

일치하는 새 백엔드가 필요합니다. 현재는 `RECASE_API_TARGET=http://127.0.0.1:8123 npm run dev`로 계정 API를 사용합니다. `/api`, `/health`, `/ready`만 프록시하고 `/login`, `/signup`은 Vue 화면입니다. [계정 사용 안내](../docs/AUTHENTICATION.md)를 따르세요.

현재 이 Mac의 UID499/8100은 계정 개편 전 코드 사본입니다. 새 프론트의 계정 API와 맞지 않으므로 기본 프록시8100 대신 위8123을 명시합니다. 실제 모델 서버를 추가 기동하지 않습니다. 현재 검수/운영 경로는 [사용자 안내](../docs/NEXT_ACTIONS.md)를 따릅니다.

```bash
npm run build
```

`dist/`는 기존처럼 백엔드가 제공합니다. 전체 앱의 기본 실행은 프로젝트 루트의 `make serve`이며 접속 주소는 http://localhost:8100 입니다. 백엔드 비밀키·평가 정답·데이터를 이 폴더나 Vite 환경변수에 넣지 않습니다.

## 랜딩·운영자 화면 추가

`/`는 제공 HTML의 랜딩, `/cases`는 합성 사건 기록실, `/cases/:id`는 해당 사건 검토실, `/history`는 본인 기록, `/settings`는 실행 정보입니다. `/admin` 하위8개 화면은 같은 로그인 계정의 서버 admin 역할이 필요합니다. 일반 가입자는 user이며 서버가 매번 권한을 검사합니다.

```bash
npm run typecheck
npm test
npm run build
```

개발용 API 대상을 명시하려면 `RECASE_API_TARGET=http://127.0.0.1:8123 npm run dev`를 사용합니다. 비밀키가 아닌 서버 프록시 설정이며 브라우저 번들에 넣지 않습니다. 기본은 기존8100입니다. 기존 UID499 서비스는 별도 코드 사본이므로 새 관리자 API/프론트가 자동 반영되지 않습니다. 운영 교체 전 새 MLX 서버를 중복 기동하지 마세요.

이번 실제 MLX 요청은 모델 시작 후180초 초과 응답 지연으로 취소를 요청했고 최종 CANCELLED를 확인했습니다. 성공 응답의 전체 검증은 미완료이며 모의 모델의 사용자/관리자 통합 통과와 구분합니다. 분석·API·측정·보안·남은 작업은 [프론트 문서](../docs/frontend/10-final-report.md), 관리자 설정은 [운영자 안내](../docs/frontend/05-admin-dashboard.md)를 참조하세요.

## 통일 디자인 시스템

차콜·웜 골드·아이보리 토큰은 `src/styles/tokens.css`, 공통 조작 스타일은 `src/styles/system.css`에 있습니다. `BrandMark`와 `SiteHeader`를 랜딩·기록실·이력·실행 정보에 공유하며 운영자 브랜드도 같은 컴포넌트를 사용합니다. 로그인/회원가입도 Vue 화면에서 같은 토큰과 BrandMark를 사용합니다. 별도 HTML/CSS·CSS 결합 생성기와 prebuild/predev는 제거했습니다.

`/cases`에서 검색·선택하고, `/cases/:id`에서 실제 공개 증거·분석·인용·증거 버전 비교를 이어갑니다. 새 데모는 명시적 버튼으로만 만듭니다. 이번 디자인의 모의 모델 미리보기는 http://localhost:8123 입니다. 기존8100 격리 서비스의 배포 사본은 별도입니다. 범위·검증은 [디자인 통합 기록](../docs/frontend/11-design-system.md)을 참조하세요.
