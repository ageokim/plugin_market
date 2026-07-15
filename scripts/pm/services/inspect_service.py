"""상태 실측 대조 리포트·교정 (Architecture.md §6.4·§7).

진실은 파일시스템(clone) + marketplace.json + enabledPlugins다.
catalog는 스캔 캐시일 뿐이라 리포트의 근거로 쓰지 않는다.
"""

from __future__ import annotations

import dataclasses
import logging
from typing import Dict, List, Optional, Set, Tuple

from pm.claudeplug.registry import (ClaudePluginRegistry, parse_source,
                                    validate_convention)
from pm.models import PluginState, derive_state
from pm.paths import ProjectPaths
from pm.store.json_store import JsonStore

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class PluginStatus:
    """플러그인 하나의 실측 상태와 발견된 문제."""

    org: str
    name: str
    entry_name: Optional[str]
    state: PluginState
    issues: Tuple[str, ...] = ()


class InspectService:
    """실측 대조(§6.4)·규약 검사(부록 A.4)·드리프트 교정.

    Args:
        paths: ProjectPaths.
        registry: ClaudePluginRegistry.
        orgs_store: orgs.json — '미등록 org' 플래그 판정 (§12.2).
    """

    def __init__(
        self,
        paths: ProjectPaths,
        registry: ClaudePluginRegistry,
        orgs_store: JsonStore,
    ) -> None:
        self._paths = paths
        self._registry = registry
        self._orgs_store = orgs_store

    def report(self) -> List[PluginStatus]:
        """디스크 clone ∪ marketplace 등록의 전 항목을 실측 대조한다."""
        source_to_entry: Dict[Tuple[str, str], str] = {}
        targets: Set[Tuple[str, str]] = set()
        for entry_name, source in self._registry.registered().items():
            parsed = parse_source(source)
            if parsed is None:
                logger.warning("해석 불가한 source 무시: %s", source)
                continue
            source_to_entry[parsed] = entry_name
            targets.add(parsed)
        targets.update(self._disk_clones())
        registered_orgs = self._registered_org_names()
        return [
            self._status_for(org, name, source_to_entry.get((org, name)),
                             registered_orgs)
            for org, name in sorted(targets)
        ]

    def _status_for(
        self,
        org: str,
        name: str,
        entry_name: Optional[str],
        registered_orgs: Set[str],
    ) -> PluginStatus:
        """항목 하나의 실측 상태·문제 목록을 만든다 (§6.4)."""
        clone_dir = self._paths.plugin_clone_dir(org, name)
        cloned = clone_dir.is_dir()
        enabled = (entry_name is not None
                   and self._registry.is_enabled(entry_name))
        state = derive_state(cloned=cloned,
                             registered=entry_name is not None,
                             enabled=enabled)
        issues: List[str] = []
        if cloned and entry_name is None:
            issues.append("드리프트 — clone만 존재, marketplace 미등록")
        if entry_name is not None and not cloned:
            issues.append("드리프트 — 등록만 존재, clone 없음")
        if org not in registered_orgs:
            issues.append("미등록 org — org 재등록 또는 삭제 권장 (§12.2)")
        if cloned:
            errors, warnings = validate_convention(clone_dir)
            issues.extend(f"규약 위반: {error}" for error in errors)
            issues.extend(f"규약 권장: {warning}" for warning in warnings)
        return PluginStatus(org, name, entry_name, state, tuple(issues))

    def repair(self) -> List[str]:
        """드리프트 교정 (§6.4) — 파괴적이지 않은 정리만 수행한다.

        clone 없는 marketplace 등록 제거, 등록 없는 enabledPlugins 키
        정리. clone 삭제는 하지 않는다(uninstall의 몫).

        Returns:
            수행한 조치 설명 목록.
        """
        actions: List[str] = []
        for entry_name, source in list(self._registry.registered().items()):
            parsed = parse_source(source)
            if parsed is None or not self._paths.plugin_clone_dir(
                    *parsed).is_dir():
                self._registry.unregister(entry_name)
                actions.append(f"등록 제거: {entry_name} (clone 없음)")
        actions.extend(f"enabledPlugins 정리: {key}"
                       for key in self._registry.prune_enabled_keys())
        return actions

    # --- 내부 ---

    def _disk_clones(self) -> Set[Tuple[str, str]]:
        found: Set[Tuple[str, str]] = set()
        plugins_dir = self._paths.plugins_dir
        if not plugins_dir.is_dir():
            return found
        for org_dir in plugins_dir.iterdir():
            if not org_dir.is_dir():
                continue
            for plugin_dir in org_dir.iterdir():
                if plugin_dir.is_dir():
                    found.add((org_dir.name, plugin_dir.name))
        return found

    def _registered_org_names(self) -> Set[str]:
        data = self._orgs_store.read()
        entries = data.get("orgs", []) if isinstance(data, dict) else []
        return {entry.get("name") for entry in entries}
