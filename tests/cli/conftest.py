"""CLI 테스트용 fake container — 실제 services 없이 계약만 흉내(§13.3)."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pytest

from pm.models import Org, OrgKind, Plugin, PluginState, Preset, utc_now_iso
from pm.services.inspect_service import PluginStatus
from pm.services.install_service import InstallResult
from pm.services.preset_service import MemberResult, PresetBadge


class FakeCatalogService:

    def __init__(self, plugins: Optional[List[Plugin]] = None) -> None:
        self.plugins = list(plugins or [])
        self.scanned: List[Optional[str]] = []

    def scan(self, org_name=None) -> Dict[str, List[Plugin]]:
        self.scanned.append(org_name)
        return self.cached(org_name, include_all=True)

    def cached(self, org_name=None,
               include_all: bool = False) -> Dict[str, List[Plugin]]:
        result: Dict[str, List[Plugin]] = {}
        for plugin in self.plugins:
            if org_name is not None and plugin.org != org_name:
                continue
            if not include_all and not plugin.has_tags:
                continue
            result.setdefault(plugin.org, []).append(plugin)
        return result

    def find(self, identifier: str) -> List[Plugin]:
        if "/" in identifier:
            org, _, name = identifier.partition("/")
            return [p for p in self.plugins
                    if p.org == org and p.name == name]
        return [p for p in self.plugins if p.name == identifier]


class FakeActivationService:

    def __init__(self) -> None:
        self.states: Dict[Tuple[str, str], PluginState] = {}
        self.calls: List[Tuple[str, str, str]] = []

    def state(self, org: str, name: str) -> PluginState:
        return self.states.get((org, name), PluginState.AVAILABLE)

    def enable(self, org: str, name: str) -> None:
        self.calls.append(("enable", org, name))
        self.states[(org, name)] = PluginState.ENABLED

    def disable(self, org: str, name: str) -> None:
        self.calls.append(("disable", org, name))
        self.states[(org, name)] = PluginState.INSTALLED


class FakeInstallService:

    def __init__(self) -> None:
        self.calls: List[Tuple[str, ...]] = []

    def install(self, plugin: Plugin, enable: bool = True) -> InstallResult:
        self.calls.append(("install", plugin.ref, str(enable)))
        return InstallResult(plugin=plugin, entry_name=plugin.name,
                             enabled=enable)

    def uninstall(self, org: str, name: str) -> None:
        self.calls.append(("uninstall", org, name))

    def update(self, org: str, name: str) -> str:
        self.calls.append(("update", org, name))
        return "abc1234"


class FakeOrgService:

    def __init__(self) -> None:
        self.orgs: List[Org] = []
        self.removed: List[str] = []

    def add(self, url_text: str) -> Org:
        name = url_text.rstrip("/").rsplit("/", 1)[-1]
        org = Org(name=name, url=url_text, host="ghes", kind=OrgKind.ORG,
                  added_at=utc_now_iso())
        self.orgs.append(org)
        return org

    def list_orgs(self) -> List[Org]:
        return list(self.orgs)

    def remove(self, name: str) -> None:
        self.removed.append(name)

    def revalidate_all(self) -> Dict[str, bool]:
        return {org.name: True for org in self.orgs}


class FakeInspectService:

    def __init__(self, statuses: Optional[List[PluginStatus]] = None) -> None:
        self.statuses = list(statuses or [])

    def report(self) -> List[PluginStatus]:
        return list(self.statuses)

    def repair(self) -> List[str]:
        return ["repaired: marketplace 재동기화"]


class FakePresetService:

    def __init__(self) -> None:
        self.presets: Dict[str, Preset] = {}
        self.batch_results: List[MemberResult] = []

    def create(self, name: str) -> Preset:
        preset = Preset(name=name, members=(), created_at=utc_now_iso())
        self.presets[name] = preset
        return preset

    def delete(self, name: str) -> None:
        self.presets.pop(name, None)

    def add_member(self, preset_name: str, ref: str) -> Preset:
        preset = self.presets[preset_name]
        preset = Preset(name=preset.name, members=preset.members + (ref,),
                        created_at=preset.created_at)
        self.presets[preset_name] = preset
        return preset

    def remove_member(self, preset_name: str, ref: str) -> Preset:
        preset = self.presets[preset_name]
        members = tuple(m for m in preset.members if m != ref)
        preset = Preset(name=preset.name, members=members,
                        created_at=preset.created_at)
        self.presets[preset_name] = preset
        return preset

    def list_presets(self) -> List[Preset]:
        return list(self.presets.values())

    def badge(self, name: str) -> PresetBadge:
        return PresetBadge.OFF

    def install(self, name: str) -> List[MemberResult]:
        return list(self.batch_results)

    enable = disable = uninstall = apply = install


class FakeContainer:
    """cli.main(container=...)에 주입되는 최소 조립체."""

    def __init__(self, tmp_paths, config=None) -> None:
        self.paths = tmp_paths
        self.config = config
        self.catalog_service = FakeCatalogService()
        self.activation_service = FakeActivationService()
        self.install_service = FakeInstallService()
        self.org_service = FakeOrgService()
        self.inspect_service = FakeInspectService()
        self.preset_service = FakePresetService()


@pytest.fixture
def container(tmp_paths) -> FakeContainer:
    return FakeContainer(tmp_paths)
