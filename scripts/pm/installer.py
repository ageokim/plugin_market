"""install(git clone) / uninstall / enable / disable / inspect — 파일시스템이 상태의 기준."""
import base64
import os
import shutil
import subprocess

from . import store

AVAILABLE = "Available"
INSTALLED = "Installed"
ENABLED = "Enabled"


def plugin_dir(name: str):
    return store.PLUGINS_DIR / name


def link_path(name: str):
    return store.CLAUDE_PLUGINS_DIR / name


def is_installed(name: str) -> bool:
    return plugin_dir(name).is_dir()


def link_status(name: str) -> str:
    """'valid' | 'broken' | 'none'"""
    p = link_path(name)
    if not p.is_symlink():
        return "none"
    return "valid" if p.exists() else "broken"


def state(name: str) -> str:
    if not is_installed(name):
        return AVAILABLE
    return ENABLED if link_status(name) == "valid" else INSTALLED


def _run_git(args: list[str]):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    r = subprocess.run(["git", *args], capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip() or "git 실행 실패")


def install(name: str, clone_url: str, token: str | None = None):
    """git clone → plugins/{name} → enable (심볼릭 링크 생성)."""
    store.ensure_dirs()
    dest = plugin_dir(name)
    if dest.exists():
        raise RuntimeError(f"이미 설치되어 있습니다: plugins/{name}")
    args = []
    if token:
        # private repo용 — 자격 증명이 .git/config에 남지 않도록 extraHeader 사용
        basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        args += ["-c", f"http.extraHeader=Authorization: Basic {basic}"]
    args += ["clone", clone_url, str(dest)]
    _run_git(args)
    enable(name)


def uninstall(name: str):
    """심볼릭 링크 삭제 → clone 디렉토리 삭제."""
    disable(name)
    dest = plugin_dir(name)
    if dest.exists():
        shutil.rmtree(dest)


def enable(name: str):
    """.claude/plugins/{name} → ../../plugins/{name} 상대경로 심볼릭 링크 생성."""
    if not is_installed(name):
        raise RuntimeError(f"설치되지 않은 플러그인입니다: {name}")
    store.ensure_dirs()
    p = link_path(name)
    if p.is_symlink() or p.exists():
        p.unlink()
    rel_target = os.path.relpath(plugin_dir(name), p.parent)
    p.symlink_to(rel_target, target_is_directory=True)


def disable(name: str):
    p = link_path(name)
    if p.is_symlink():
        p.unlink()


def list_installed() -> list[str]:
    if not store.PLUGINS_DIR.is_dir():
        return []
    return sorted(d.name for d in store.PLUGINS_DIR.iterdir() if d.is_dir())


def inspect_all(names: list[str]) -> list[dict]:
    """스캔 목록 + 로컬 설치본을 합쳐 파일시스템 기준 상태 리포트 생성."""
    all_names = sorted(set(names) | set(list_installed()))
    return [
        {
            "name": n,
            "state": state(n),
            "cloned": is_installed(n),
            "link": link_status(n),
            "in_scan": n in names,
        }
        for n in all_names
    ]
