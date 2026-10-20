# RE:CASE 프론트엔드

Vue 3 화면과 브라우저용 자산을 모은 폴더입니다.

- `src/`: Vue 컴포넌트·스타일
- `public/`: 로컬 로그인 HTML/CSS. 백엔드가 같은 자산을 읽어 인증 화면을 제공합니다.
- `scripts/browser_e2e.mjs`: CUA 브라우저 통합 검증
- `vite.config.js`: 로컬 백엔드 프록시

이 폴더에서 실행합니다.

```bash
npm ci
npm run dev
```

백엔드는 프로젝트 루트에서 `make serve`로 먼저 실행합니다. 개발 서버의 `/login`으로 접속해 기존 로컬 접근키로 로그인한 뒤 화면을 사용합니다. `/api`, `/health`, `/ready`, `/login`, `/auth.css`는 127.0.0.1:8100으로 전달됩니다.

```bash
npm run build
```

`dist/`는 기존처럼 백엔드가 제공합니다. 전체 앱의 기본 실행은 프로젝트 루트의 `make serve`이며 접속 주소는 http://localhost:8100 입니다. 백엔드 비밀키·평가 정답·데이터를 이 폴더나 Vite 환경변수에 넣지 않습니다.
