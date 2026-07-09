"""plugin_market Streamlit 프로토타입 — 로그인 → 스캔/설치/활성화 → inspect."""
import sys
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pm import github, installer, store  # noqa: E402

st.set_page_config(page_title="Plugin Market", page_icon="🧩", layout="wide")

STATE_BADGE = {
    installer.ENABLED: "🟢 Enabled",
    installer.INSTALLED: "🟡 Installed",
    installer.AVAILABLE: "⚪ Available",
}


def init_session():
    st.session_state.setdefault("authed", False)
    st.session_state.setdefault("target", "")
    st.session_state.setdefault("kind", "")
    st.session_state.setdefault("token", "")
    st.session_state.setdefault("login", "")


def do_action(fn, *args, success: str):
    try:
        fn(*args)
        st.toast(success)
        st.rerun()
    except (RuntimeError, github.GitHubError) as e:
        st.error(str(e))


# ── 로그인 화면 ──────────────────────────────────────────────
def login_screen():
    st.title("🧩 Plugin Market")
    st.caption("GitHub organization/계정의 Claude plugin을 검색·설치·관리합니다.")

    cfg = store.load_config()
    with st.form("login_form"):
        target = st.text_input(
            "GitHub organization 또는 계정 이름 (URL 붙여넣기 가능)",
            value=cfg.get("github_target", ""),
            placeholder="예: ageokim 또는 https://github.com/ageokim",
        )
        token = st.text_input("Personal Access Token (선택 — public repo만이면 비워두세요)", type="password")
        submitted = st.form_submit_button("연결", type="primary")

    if not submitted:
        return
    target = github.parse_target(target)
    if not target:
        st.error("organization 또는 계정 이름을 입력하세요.")
        return
    try:
        with st.spinner("GitHub 권한 확인 중..."):
            login = github.verify_token(token) if token else ""
            kind = github.resolve_target(target, token or None)
    except github.GitHubError as e:
        st.error(str(e))
        return

    cfg["github_target"] = target
    store.save_config(cfg)
    st.session_state.update(authed=True, target=target, kind=kind, token=token, login=login)
    st.rerun()


# ── 메인 화면 ────────────────────────────────────────────────
def scan():
    with st.spinner(f"{st.session_state.target} repo 스캔 중..."):
        repos = github.fetch_repos(st.session_state.target, st.session_state.kind, st.session_state.token or None)
    store.save_plugins({
        "target": st.session_state.target,
        "kind": st.session_state.kind,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "plugins": repos,
    })
    st.toast(f"스캔 완료 — repo {len(repos)}개")


def plugin_row(p: dict):
    name = p["name"]
    state = installer.state(name)
    c_name, c_desc, c_state, c_btn = st.columns([2.2, 4, 1.3, 2.5])
    with c_name:
        st.markdown(f"**[{name}]({p.get('github_addr', '')})**" if p.get("github_addr") else f"**{name}**")
        if p.get("private"):
            st.caption("🔒 private")
    with c_desc:
        st.caption(p.get("description") or "(설명 없음)")
        if not p.get("in_scan", True):
            st.caption("⚠️ 스캔 목록에 없는 로컬 설치본")
    with c_state:
        st.write(STATE_BADGE[state])
    with c_btn:
        b1, b2 = st.columns(2)
        if state == installer.AVAILABLE:
            if p.get("clone_url") and b1.button("Install", key=f"in_{name}", type="primary"):
                with st.spinner(f"{name} 설치 중..."):
                    do_action(installer.install, name, p["clone_url"], st.session_state.token or None,
                              success=f"{name} 설치 완료")
        elif state == installer.INSTALLED:
            if b1.button("Enable", key=f"en_{name}"):
                do_action(installer.enable, name, success=f"{name} 활성화")
            if b2.button("Uninstall", key=f"un_{name}"):
                do_action(installer.uninstall, name, success=f"{name} 제거 완료")
        else:  # ENABLED
            if b1.button("Disable", key=f"di_{name}"):
                do_action(installer.disable, name, success=f"{name} 비활성화")
            if b2.button("Uninstall", key=f"un_{name}"):
                do_action(installer.uninstall, name, success=f"{name} 제거 완료")


def main_screen():
    head, logout = st.columns([8, 1])
    with head:
        st.title("🧩 Plugin Market")
        who = f" (로그인: {st.session_state.login})" if st.session_state.login else ""
        st.caption(f"연결 대상: **{st.session_state.target}** ({st.session_state.kind}){who}")
    with logout:
        if st.button("로그아웃"):
            st.session_state.update(authed=False, token="", login="")
            st.rerun()

    c1, c2 = st.columns([1.5, 5])
    if c1.button("🔄 GitHub 스캔", type="primary"):
        try:
            scan()
        except github.GitHubError as e:
            st.error(str(e))
    apply_filter = c2.checkbox("태그 필터 적용 (#plugin #release)", value=True)

    data = store.load_plugins()
    plugins = data.get("plugins", [])
    if apply_filter:
        plugins = [p for p in plugins if p.get("has_tags")]

    # 스캔 목록에 없는 로컬 설치본도 함께 표시
    scanned = {p["name"] for p in plugins}
    plugins += [{"name": n, "in_scan": False} for n in installer.list_installed() if n not in scanned]

    st.divider()
    if data.get("updated_at"):
        st.caption(f"마지막 스캔: {data['updated_at']} · 표시 {len(plugins)}개")

    if not plugins:
        if data.get("plugins"):
            st.info("태그 필터에 걸리는 repo가 없습니다. repo description에 `#plugin #release`를 추가하거나 필터를 해제해 보세요.")
        else:
            st.info("🔄 **GitHub 스캔** 버튼을 눌러 repo 목록을 불러오세요.")
    for p in plugins:
        plugin_row(p)

    st.divider()
    with st.expander("🔍 Inspect — 파일시스템 기준 상태"):
        report = installer.inspect_all([p["name"] for p in data.get("plugins", [])])
        if report:
            st.dataframe(
                [
                    {
                        "plugin": r["name"],
                        "상태": STATE_BADGE[r["state"]],
                        "clone (plugins/)": "✅" if r["cloned"] else "—",
                        "링크 (.claude/plugins/)": {"valid": "✅", "broken": "⚠️ 끊어짐", "none": "—"}[r["link"]],
                        "스캔 목록": "✅" if r["in_scan"] else "❌",
                    }
                    for r in report
                ],
                width="stretch",
                hide_index=True,
            )
        else:
            st.caption("표시할 플러그인이 없습니다.")


init_session()
store.ensure_dirs()
if st.session_state.authed:
    main_screen()
else:
    login_screen()
