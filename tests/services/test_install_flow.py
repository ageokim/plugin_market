"""설치→활성→비활성→삭제 전 흐름 + 충돌·되감기·보존 (§6.2·§6.4)."""

from __future__ import annotations

import pytest

from pm.errors import GitOpsError, PmError, RegistryError
from pm.models import PluginState


def test_full_lifecycle(env):
    env.login_and_register_org("org-a")
    plugin = env.catalog_plugin("org-a", "plugin-a")

    def state():
        return env.activation_service.state("org-a", "plugin-a")

    assert state() is PluginState.AVAILABLE

    result = env.install_service.install(plugin)
    assert result.entry_name == "plugin-a"
    assert env.paths.plugin_clone_dir("org-a", "plugin-a").is_dir()
    assert state() is PluginState.ENABLED  # install = clone+등록+활성 (§6.2)

    env.activation_service.disable("org-a", "plugin-a")
    assert state() is PluginState.INSTALLED

    env.activation_service.enable("org-a", "plugin-a")
    assert state() is PluginState.ENABLED

    env.install_service.uninstall("org-a", "plugin-a")
    assert state() is PluginState.AVAILABLE
    assert not env.paths.plugin_clone_dir("org-a", "plugin-a").exists()
    assert env.registry.registered() == {}
    assert env.settings_store.read().get("enabledPlugins", {}) == {}


def test_install_no_enable(env):
    env.login_and_register_org("org-a")
    plugin = env.catalog_plugin("org-a", "plugin-a")
    result = env.install_service.install(plugin, enable=False)
    assert result.enabled is False
    assert (env.activation_service.state("org-a", "plugin-a")
            is PluginState.INSTALLED)


def test_install_convention_violation_rolls_back(env):
    env.login_and_register_org("org-a")
    plugin = env.catalog_plugin("org-a", "bad-plugin")
    env.git.valid_plugin = False  # plugin.json 없는 clone
    with pytest.raises(RegistryError):
        env.install_service.install(plugin)
    assert not env.paths.plugin_clone_dir("org-a", "bad-plugin").exists()
    assert env.registry.registered() == {}  # 부분 산출물 없음 (§6.2)


def test_install_clone_failure_propagates(env):
    env.login_and_register_org("org-a")
    plugin = env.catalog_plugin("org-a", "plugin-a")
    env.git.fail_urls.add(plugin.clone_url)
    with pytest.raises(GitOpsError):
        env.install_service.install(plugin)
    assert env.registry.registered() == {}


def test_install_twice_raises(env):
    env.login_and_register_org("org-a")
    plugin = env.catalog_plugin("org-a", "plugin-a")
    env.install_service.install(plugin)
    with pytest.raises(PmError):
        env.install_service.install(plugin)


def test_name_collision_keeps_first_entry(env):
    env.login_and_register_org("org-a")
    env.register_extra_org("org-b")
    first = env.catalog_plugin("org-a", "plugin-a")
    second = env.catalog_plugin("org-b", "plugin-a")

    first_result = env.install_service.install(first)
    second_result = env.install_service.install(second)
    assert first_result.entry_name == "plugin-a"
    assert second_result.entry_name == "org-b-plugin-a"  # 신규만 접두 (§6.2)
    enabled = env.settings_store.read()["enabledPlugins"]
    assert enabled == {
        "plugin-a@plugin-market": True,
        "org-b-plugin-a@plugin-market": True,
    }
    # 첫 항목 삭제해도 둘째는 무관
    env.install_service.uninstall("org-a", "plugin-a")
    assert (env.activation_service.state("org-b", "plugin-a")
            is PluginState.ENABLED)


def test_uninstall_not_installed_raises(env):
    with pytest.raises(PmError):
        env.install_service.uninstall("org-a", "ghost")


def test_update_preserves_disabled_state(env):
    """§6.2 — 꺼진 플러그인은 꺼진 채 새 버전이 된다."""
    env.login_and_register_org("org-a")
    plugin = env.catalog_plugin("org-a", "plugin-a")
    env.install_service.install(plugin)
    env.activation_service.disable("org-a", "plugin-a")

    head = env.install_service.update("org-a", "plugin-a")
    assert head == "abc1234"
    assert ("pull", str(env.paths.plugin_clone_dir("org-a", "plugin-a"))) in (
        env.git.calls)
    assert (env.activation_service.state("org-a", "plugin-a")
            is PluginState.INSTALLED)  # 활성 상태 보존


def test_update_not_installed_raises(env):
    with pytest.raises(PmError):
        env.install_service.update("org-a", "ghost")


def test_enable_not_installed_raises(env):
    with pytest.raises(RegistryError):
        env.activation_service.enable("org-a", "ghost")
