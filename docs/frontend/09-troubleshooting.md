# 문제와 해결

## 랜딩 자산 추출의 첫 시도 실패

기존 문제: data:image 정규식이 base64 raster뿐 아니라 percent-encoded SVG도 디코딩하려 했다. 첫 추출 명령 exit1. 수정: base64 전용 패턴으로13개 raster 인스턴스(고유12개)를 추출하고 기존 grain SVG는 CSS 그대로 보존했다. postcss import도 frontend/node_modules의 실제 경로로 해결했다. 원본 HTML 변경0. 최종 asset-manifest의 SHA와 원본 디코딩 바이트를 비교한다.

## Vue 안의 sticky 장면이 위로 사라짐

기존 문제: 원래 body의 overflow-x:hidden을 컴포넌트 root에 그대로 옮기니 새 스크롤 컨테이너가 생겼다. 진단: scrollY1800에서 scene top=-1800, position sticky임에도 고정되지 않음. 수정: landing root의 overflow-x:clip. 이후 실제 브라우저 탐정/문/갤러리 장면 표시 확인. 카드 내부 overflow는 유지. 원래 디자인 수식은 보존했다.

## 운영 상태와 개발 화면이 다름

UID499의 별도 배포는 소스 복사본이다. 개발 화면이나 새 관리자 API가 localhost8100에 자동 적용되지 않는다. 기존 배포의 보안·model.lock·state·최신 삭제 journal을 보존하는 검토된 업데이트 절차가 필요하다. 이 작업에서 원래 make serve를 중복 실행하지 않는다. 개발 UI는 RECASE_API_TARGET으로 명시적 fixture 서버를 선택할 수 있다.

## 실제 MLX 완료 지연과 취소

기존 UID499/PID41133/기존4B·56 LoRA 서버에 새 Vue 작업실을 연결해 합성 분석1건만 요청했다. 15:17:47 모델 시작 이후180초가 지나도 종료 결과가 없었다. 자동 UI 대기 제한 실패 후 실제 진행 상태를 별도 확인했고 같은 분석을 재요청하지 않았다. 검증 작업 JOB-719c4dc7672e4804에 취소1회를 요청했다.

15:28 사후 UI 조회에서 CANCELLED를 확인했다. 15:27:23 /ready200·ready=true, 같은 PID/UID와 Ss 상태도 확인했다. 초기 U 프로세스 상태와 낮은 RSS만으로 GPU/메모리 문제를 확정하지 않는다. 직접 원인은 미확인이다. 서버 재시작/새 모델 로드/어댑터 변경/유료 호출0. 실제 성공 분석·3버전 비교 인수는 여전히 미완료다. 다음 실제 추론은 원인을 확인한 뒤 수행해야 한다.

초기 세션 확인이 기존 raw fetch라 응답 지연 중 시작 화면이 계속 대기하는 문제도 발견했다. 공통15초 timeout/취소 API로 교체하고 세션 없는 정상 입장 상태와 연결 실패를 구분했다. 분석 취소 요청은 실제 종료 전 '취소 요청됨'으로만 표시한다. 취소 종료와 모델 성공 응답을 혼동하지 않는다.

## 화면 크기 검증

IAB viewport 설정은 현재 활성 탭에 적용됐다. 다른 탭을 활성화한 뒤 얻은1280px 캡처는 모바일 근거로 쓰지 않았다. 검증 대상 탭에서390px/scrollWidth375를 확인한 후 다시 캡처했고 임시 override는 reset했다. admin-mobile.png와 fixture-mobile-browser.json이 유효 근거다.
