"""enable/disable use case (Architecture.md §5·§6.4) — registry 위임."""

from __future__ import annotations

from pm.claudeplug.registry import ClaudePluginRegistry
from pm.errors import RegistryError
from pm.models import PluginState, derive_state
from pm.paths import ProjectPaths


class ActivationService:
    """활성 토글과 상태 실측 도출 (§2.2 ISP — registry·paths만 의존).

    Args:
        registry: ClaudePluginRegistry.
        paths: ProjectPaths — clone 존재 실측용.
    """

    def __init__(self, registry: ClaudePluginRegistry,
                 paths: ProjectPaths) -> None:
        self._registry = registry
        self._paths = paths

    def enable(self, org: str, name: str) -> None:
        """Raises RegistryError: 설치되지 않음."""
        self._toggle(org, name, True)

    def disable(self, org: str, name: str) -> None:
        """Raises RegistryError: 설치되지 않음."""
        self._toggle(org, name, False)

    def state(self, org: str, name: str) -> PluginState:
        """§6.4 실측 도출 — clone 존재 ∧ 등록 ∧ enabledPlugins."""
        cloned = self._paths.plugin_clone_dir(org, name).is_dir()
        entry_name = self._registry.entry_for(org, name)
        enabled = (entry_name is not None
                   and self._registry.is_enabled(entry_name))
        return derive_state(cloned=cloned,
                            registered=entry_name is not None,
                            enabled=enabled)

    def _toggle(self, org: str, name: str, value: bool) -> None:
        entry_name = self._registry.entry_for(org, name)
        if entry_name is None:
            raise RegistryError(
                f"설치되지 않음: {org}/{name} — pm install 먼저 (§6.4)")
        self._registry.set_enabled(entry_name, value)
