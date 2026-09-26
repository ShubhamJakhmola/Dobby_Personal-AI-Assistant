# Dobby — JARVIS Computer Intelligence: Completion Plan

## Product definition

Dobby is a cross-platform personal computer agent. The LLM is a replaceable reasoning component. Dobby owns task state, world state, skills, policy, execution, observation, verification, recovery, memory and learning.

The practical target is not fictional consciousness or unlimited access to every third-party service. The target is a **general computer-use agent** that can operate the user's machine and supported services through composable primitives and adapters.

## Core loop

```text
User goal
  -> task context
  -> observe current world
  -> reason / choose next action
  -> policy
  -> execute
  -> observe
  -> verify
  -> recover or continue
  -> learn
```

The same loop must be used for browser, desktop, files, media, system administration and service integrations.

## What is now implemented

### Computer control
- Persistent task/world state.
- Unified computer execution facade.
- Mouse, keyboard, screen and window primitives already present in the project are treated as low-level controls.
- Bounded action retry with fresh observation.
- Structured JSON success/failure is honoured instead of guessing success from text.
- Headless GUI backends degrade cleanly instead of preventing action discovery.

### Browser/media
- Browser capability remains adapter-based.
- Persistent Dobby-controlled browser path is preferred.
- Native browser launch is available explicitly as fallback.
- YouTube/media actions include play, pause/resume, stop, volume, mute, seek, fullscreen and skip-ad primitives.
- Current task state is retained so follow-up commands can refer to the existing environment.

### OS
- Common OS adapter contract for Windows, macOS and Linux.
- Application discovery/launch and path opening use platform-specific implementations behind a common interface.
- Existing Linux desktop adapters remain available.

### System intelligence
- Hardware/system inspection.
- Process/resource inspection.
- Safe explicit-PID process-stop primitive.
- Read-only troubleshooting and remediation planning.
- Diagnostics-first behavior: Dobby should inspect before modifying the system.

### Learning
- Experience log records success/failure and recovery.
- User-taught workflows are persisted as procedures.
- Capability acquisition can inspect external projects and integrate them through adapters rather than changing Dobby's core architecture.

### Security
- Existing risk/policy/confirmation architecture remains authoritative.
- Sensitive, destructive, privileged and external-impact operations must not bypass confirmation/policy.
- Learned workflows are data, not arbitrary executable code.

## Still environment-dependent

The architecture is cross-platform, but a real desktop must provide the relevant backend:

- Windows: GUI automation/accessibility and native application APIs.
- macOS: Accessibility permissions and AppleScript/native APIs where appropriate.
- Linux: X11/Wayland-compatible mouse/keyboard/screen/window backends.
- Browser control: a real controlled browser session or an explicitly attached debugging session.
- Vision: a configured vision-capable model or local vision backend.

A headless CI machine cannot prove physical mouse/keyboard/browser behavior.

## Required acceptance suite on a real user's desktop

1. Open an application.
2. Open a local folder.
3. Find a specified movie.
4. Play it.
5. Pause/resume it.
6. Control volume and mute.
7. Open a browser and YouTube.
8. Search and select a requested video.
9. Continue operating the same page without re-searching.
10. Detect a visible Skip Ad button from the current screen.
11. Click it and verify the state changed.
12. Handle a failed action with a different bounded recovery strategy.
13. Report system specifications.
14. Diagnose high RAM usage without killing processes blindly.
15. Produce a safe remediation plan.
16. Execute a reversible remediation only when policy allows.
17. Verify the remediation.
18. Learn a user-taught workflow and replay it.

## Future extension layers

- Chromium remote-debugging attachment to an already-running browser.
- Accessibility-tree adapters for Windows UI Automation, macOS Accessibility and Linux AT-SPI.
- Local/remote vision model routing.
- More application adapters (Office, media players, IDEs, messaging, etc.).
- Event-driven proactive operation.
- Multi-brain routing across Gemini, OpenRouter and local/specialist models.
- LAN worker registry and capability-aware dispatch.
- Skill acquisition sandbox with stronger package/license/security checks.

These are extensions of the core, not separate execution systems.
