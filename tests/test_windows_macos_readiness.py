import platform

from computer import desktop
from computer.os_adapters import WindowsAdapter, MacOSAdapter, LinuxAdapter
from computer.platform_adapter import find_application


def test_all_os_adapters_exist_and_share_contract():
    adapters = [WindowsAdapter(), MacOSAdapter(), LinuxAdapter()]
    for adapter in adapters:
        env = adapter.environment()
        assert "os" in env and "python" in env
        assert callable(adapter.launch)
        assert callable(adapter.open_path)


def test_cross_platform_desktop_surface_is_importable():
    assert callable(desktop.mouse)
    assert callable(desktop.keyboard)
    assert callable(desktop.list_windows)
    assert callable(desktop.active_window)
    assert callable(desktop.focus_window)
    assert callable(desktop.screen_info)


def test_platform_application_resolution_is_safe_for_missing_app():
    result = find_application("__dobby_definitely_missing_application__")
    assert result["found"] is False
    assert "candidates" in result


def test_platform_scripts_exist():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for rel in (
        "scripts/windows/setup.ps1",
        "scripts/windows/start.ps1",
        "scripts/windows/start.bat",
        "scripts/macos/setup.command",
        "scripts/macos/start.command",
        "PLATFORM_SETUP.md",
    ):
        assert (root / rel).exists(), rel
