"""설치/삭제/업데이트 use case (Architecture.md §6.2).

install: clone → 규약 검사(부록 A) → marketplace 등록 → 활성화.
어느 단계든 실패하면 부분 산출물(clone·등록)을 되감는다.
"""

from __future__ import annotations

import dataclasses
import logging
from typing import Tuple

from pm.claudeplug.registry import ClaudePluginRegistry, validate_convention
from pm.errors import PmError, RegistryError
from pm.gitops import GitRunner, remove_repo_dir
from pm.models import Plugin
from pm.paths import ProjectPaths

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class InstallResult:
    """설치 결과 — 등록명과 규약 경고(권장 위반)를 담는다."""

    plugin: Plugin
    entry_name: str
    enabled: bool
    warnings: Tuple[str, ...] = ()


class InstallService:
    """§6.2 설치 흐름 담당 (§2.2 ISP — git·registry·paths만 의존).

    Args:
        paths: ProjectPaths.
        git: GitRunner (§11 인증은 구현체 몫).
        registry: ClaudePluginRegistry.
    """

    def __init__(
        self,
        paths: ProjectPaths,
        git: GitRunner,
        registry: ClaudePluginRegistry,
    ) -> None:
        self._paths = paths
        self._git = git
        self._registry = registry

    def install(self, plugin: Plugin, enable: bool = True) -> InstallResult:
        """clone → 규약 검사 → 등록 → (기본) 활성화 (§6.2).

        Raises:
            PmError: 이미 설치됨.
            GitOpsError: clone 실패.
            RegistryError: 규약 위반 — clone은 정리된다.
        """
        dest = self._paths.plugin_clone_dir(plugin.org, plugin.name)
        if dest.exists():
            raise PmError(f"이미 설치됨: {plugin.ref}")
        self._git.clone(plugin.clone_url, dest)
        entry_name = None
        try:
            errors, warnings = validate_convention(dest)
            if errors:
                raise RegistryError(
                    f"규약 위반 — {plugin.ref}: " + " / ".join(errors))
            entry_name = self._registry.register(plugin.org, plugin.name)
            if enable:
                self._registry.set_enabled(entry_name, True)
        except BaseException:
            if entry_name is not None:
                try:
                    self._registry.unregister(entry_name)
                except RegistryError:
                    logger.warning("설치 되감기 중 등록 해제 실패: %s",
                                   entry_name)
            remove_repo_dir(dest)  # 부분 clone 정리 (§6.2)
            raise
        return InstallResult(plugin, entry_name, enable, tuple(warnings))

    def uninstall(self, org: str, name: str) -> None:
        """enabledPlugins 제거 → marketplace 제거 → clone 삭제 (§6.2 순서).

        Raises:
            PmError: 설치돼 있지 않음.
        """
        entry_name = self._registry.entry_for(org, name)
        dest = self._paths.plugin_clone_dir(org, name)
        if entry_name is None and not dest.exists():
            raise PmError(f"설치되지 않음: {org}/{name}")
        if entry_name is not None:
            self._registry.unregister(entry_name)
        remove_repo_dir(dest)

    def update(self, org: str, name: str) -> str:
        """git pull + 멱등 재등록 — enabledPlugins는 보존 (§6.2).

        Returns:
            갱신 후 HEAD 커밋 해시.

        Raises:
            PmError: 설치돼 있지 않음. GitOpsError: pull 실패.
        """
        dest = self._paths.plugin_clone_dir(org, name)
        if not dest.is_dir():
            raise PmError(f"설치되지 않음: {org}/{name}")
        self._git.pull(dest)
        self._registry.register(org, name)  # 멱등 — 활성 상태 불변
        return self._git.head_commit(dest)
