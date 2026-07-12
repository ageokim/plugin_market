# plugin_market

Claude Code에서 사용할 plugin을 GitHub organization에서 검색·설치·활성화·관리하는 도구.

> **현재 상태: 뼈대(폴더 트리)만 구성됨 — 구현 준비 단계.**
> 전체 설계는 [docs/Architecture.md](docs/Architecture.md) 참고.

## 구조

```
plugin_market/
├─ run.sh / run.cmd     # launcher: 셋업 → 환경 체크 → Streamlit + 셸 동시 기동 (§9)
├─ env/                 # OS별 셋업 스크립트 + requirements
├─ scripts/
│  ├─ bin/              #   pm shim (PATH 등록 대상)
│  ├─ pm/               #   core 파이썬 패키지 (§5)
│  │   ├─ github/  store/  claudeplug/  services/  envcheck/  system/
│  └─ ui/               #   Streamlit 화면 (+ scripts/app.py 진입점)
├─ web/                 # 정적 셸 (shell.html) — GitHub Pages 중앙 배포 (§12.4)
├─ plugins/             # 설치된 plugin clone (git 비추적)
├─ .claude/             # local claude 설정
├─ .claude-plugin/      # marketplace.json — pm이 생성·관리 (git 비추적)
├─ data/                # config.json · plugins.json · env.json (git 비추적)
├─ tests/               # fake 주입 단위 테스트
└─ docs/Architecture.md # 설계 기준 문서
```

## 사용법 (구현 후)

```bash
./run.sh          # linux — 셋업부터 UI까지 한 번에
run.cmd           # windows
pm list           # CLI (PATH 등록 후 어디서든)
```
