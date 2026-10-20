# 작업 기록

## 2026-10-20 KST — 감사 시작

- 사용자 지시: 개선한 기존 폴더를 이어서 진행. 실행 지침은 요구사항으로 읽되 결과를 가정하지 않음.
- `sw_vers`, `uname -m`, `sysctl -n hw.memsize`, `df -h .`, `vm_stat`: exit 0.
- `.venv/bin/python -m mlx_lm.lora --help`, 함수 signature 검사: exit 0. 설치된 API 옵션을 확인.
- 원본 27개 파일 SHA-256 및 tar.gz 백업: exit 0. 경로 `outputs/runs/20261020T122029+0900-audit/`.
- 참고 프로젝트에는 명시 라이선스가 없음. 원본은 변경하지 않고 싱글턴/stdio/SSE 패턴만 참고한다.
- 기존 평가 모델 기본값 불일치 발견. 모델 다운로드/재학습 없이 로컬 캐시로 검증한다.
