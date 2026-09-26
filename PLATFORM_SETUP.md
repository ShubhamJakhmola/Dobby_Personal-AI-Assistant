# Dobby — Windows and macOS setup

Dobby uses one Python codebase with OS-specific adapters and dependencies.

## Windows

Requirements: Windows 10/11 and Python 3.11+.

1. Open PowerShell in the Dobby directory.
2. Run `scripts/windows/setup.ps1`.
3. Start with `scripts/windows/start.ps1 diagnostics` or double-click/use `scripts/windows/start.bat diagnostics`.
4. For Windows UI automation, allow Dobby the required accessibility/elevated permissions when Windows asks.

The setup script creates `.venv`, installs the Windows-only packages (pywinauto, pywin32, pycaw, etc.), and installs Playwright Chromium/Firefox.

## macOS

Requirements: macOS 12+ and Python 3.11+.

1. Run `scripts/macos/setup.command` from Terminal.
2. Start with `scripts/macos/start.command diagnostics`.
3. In **System Settings → Privacy & Security**, grant Dobby/Terminal the Accessibility and Screen Recording permissions required for desktop automation and screenshots.

The macOS setup installs PyObjC accessibility helpers and Playwright Chromium/Firefox. Safari automation additionally requires `python -m playwright install webkit`.

## Safe first validation

Run `diagnostics` first. It is read-only and does not type, click, launch arbitrary applications, or modify the system.
