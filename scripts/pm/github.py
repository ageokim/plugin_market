"""GitHub API — 토큰 검증, org/user repo 조회, #plugin #release 필터."""
import requests

from . import store

PLUGIN_TAGS = ("#plugin", "#release")
TIMEOUT = 15


class GitHubError(Exception):
    pass


def _api_base() -> str:
    return store.load_config().get("github_api", "https://api.github.com").rstrip("/")


def _headers(token: str | None) -> dict:
    h = {"Accept": "application/vnd.github+json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _get(path: str, token: str | None, params: dict | None = None) -> requests.Response:
    try:
        return requests.get(f"{_api_base()}{path}", headers=_headers(token), params=params, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise GitHubError(f"GitHub 연결 실패: {e}") from e


def parse_target(text: str) -> str:
    """'ageokim', 'https://github.com/ageokim/repo', 'git@github.com:org/...' 등에서 계정/조직 이름 추출."""
    t = text.strip().rstrip("/")
    if "github.com" in t:
        t = t.split("github.com", 1)[1].lstrip(":/")
    return t.split("/")[0].strip()


def verify_token(token: str) -> str:
    """토큰 유효성 확인. 성공 시 로그인 계정명 반환."""
    r = _get("/user", token)
    if r.status_code == 401:
        raise GitHubError("토큰이 유효하지 않습니다 (401). PAT를 확인하세요.")
    if not r.ok:
        raise GitHubError(f"토큰 검증 실패: HTTP {r.status_code}")
    return r.json().get("login", "")


def resolve_target(name: str, token: str | None) -> str:
    """대상이 organization인지 user인지 판별. 'org' 또는 'user' 반환."""
    if _get(f"/orgs/{name}", token).ok:
        return "org"
    if _get(f"/users/{name}", token).ok:
        return "user"
    raise GitHubError(f"'{name}' organization/사용자를 찾을 수 없습니다.")


def fetch_repos(name: str, kind: str, token: str | None) -> list[dict]:
    """org/user의 전체 repo 목록 조회 (페이지네이션 처리)."""
    if kind == "org":
        path, repo_type = f"/orgs/{name}/repos", "all"
    else:
        # user 조회에서 type=all은 collaborator로 참여한 남의 repo까지 포함하므로 owner로 제한.
        # /users/{name}/repos는 토큰이 있어도 public만 반환하므로,
        # 토큰 소유자 본인 계정이면 private까지 포함되는 /user/repos 사용
        path, repo_type = f"/users/{name}/repos", "owner"
        if token:
            r = _get("/user", token)
            if r.ok and r.json().get("login", "").lower() == name.lower():
                path = "/user/repos"
    repos, page = [], 1
    while True:
        r = _get(path, token, params={"per_page": 100, "page": page, "type": repo_type, "sort": "full_name"})
        if r.status_code == 403 and "rate limit" in r.text.lower():
            raise GitHubError("GitHub API rate limit 초과. PAT를 입력하면 한도가 늘어납니다.")
        if not r.ok:
            raise GitHubError(f"repo 목록 조회 실패: HTTP {r.status_code}")
        batch = r.json()
        repos.extend(batch)
        if 'rel="next"' not in r.headers.get("Link", ""):
            break
        page += 1
    return [
        {
            "name": repo["name"],
            "github_addr": repo["html_url"],
            "clone_url": repo["clone_url"],
            "description": repo.get("description") or "",
            "private": repo.get("private", False),
            "has_tags": has_plugin_tags(repo.get("description")),
        }
        for repo in repos
    ]


def has_plugin_tags(description: str | None) -> bool:
    """description에 #plugin과 #release가 모두 있는지 확인."""
    desc = (description or "").lower()
    return all(tag in desc for tag in PLUGIN_TAGS)
