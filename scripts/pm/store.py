"""data/plugins.json, data/config.json 입출력 및 프로젝트 경로 정의."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # plugin_market/
DATA_DIR = ROOT / "data"
PLUGINS_DIR = ROOT / "plugins"                      # git clone 저장 위치
CLAUDE_PLUGINS_DIR = ROOT / ".claude" / "plugins"   # 심볼릭 링크 등록 지점

CONFIG_PATH = DATA_DIR / "config.json"
PLUGINS_JSON_PATH = DATA_DIR / "plugins.json"

DEFAULT_CONFIG = {
    "github_target": "",
    "github_api": "https://api.github.com",
}


def ensure_dirs():
    for d in (DATA_DIR, PLUGINS_DIR, CLAUDE_PLUGINS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(_load_json(CONFIG_PATH, {}))
    return cfg


def save_config(cfg: dict):
    ensure_dirs()
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def load_plugins() -> dict:
    return _load_json(PLUGINS_JSON_PATH, {"target": "", "kind": "", "updated_at": "", "plugins": []})


def save_plugins(data: dict):
    ensure_dirs()
    PLUGINS_JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
