# Dobby Master JARVIS Build — Release Notes

## Core milestone

This build consolidates Dobby around a single computer-intelligence model:

**reason -> policy -> execute -> observe -> verify -> recover -> learn**

## Important fixes

- Structured tool results with `{"success": false}` are no longer incorrectly treated as successful actions.
- GUI modules no longer disappear from the action registry merely because a headless Linux environment cannot connect to X11.
- Windows/macOS/Linux now share a common OS adapter contract.
- Added `ComputerEngine`, `ComputerState` integration and `DobbyOrchestrator` facade.
- Added world observation helper.

## Testing

Focused JARVIS/computer tests: **46 passed**.

Phases 5–9: **46 passed** individually.

The full historical suite contains long-running tests; Phase 10 exceeded the CI timeout during this build. That is not being reported as a pass.

A real desktop validation is still required for physical mouse/keyboard, browser attachment, screen vision and application-specific behavior.
