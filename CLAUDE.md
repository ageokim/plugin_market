# plugin_market

Claude Code plugin을 GitHub organization에서 검색·설치·활성화·관리하는 시스템.

## 규칙

- 설계 기준 문서: **docs/Architecture.md** — 구현 전 반드시 해당 섹션을 확인할 것
- 코드 규정: Google Python Style Guide, SOLID (조립은 `scripts/pm/container.py`에서만)
- **가상환경(venv) 금지** — 실행은 항상 `python -m`, 의존성은 `pip install --user` (§9)
- 변경 가능한 값(GitHub host 등)은 하드코딩 금지 — config 주입 (§2.3)
- 상태는 저장하지 않고 파일시스템에서 실측 도출 (§6.4)
- 토큰은 디스크에 저장하지 않는다 (§11)

## 구조

- `scripts/pm/` — core 패키지 (CLI·UI가 공유). 레이어: Presentation → services → domain → infrastructure
- `scripts/app.py`, `scripts/ui/` — Streamlit (셸 iframe에 임베드)
- `web/` — 정적 셸 (Pages 중앙 배포)
- `plugins/` — 설치된 plugin clone / `.claude-plugin/marketplace.json` — pm이 생성·관리
