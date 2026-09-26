# Dobby — Computer Intelligence Upgrade

## Purpose

This build changes Dobby from a collection of Gemini tools into a stateful computer-control runtime.
Gemini remains the reasoning/voice brain. Dobby owns execution, policy, current-world state, recovery, and experience recording.

## Core execution model

```text
User
  -> Gemini reasoning
  -> Dobby ControlRuntime
  -> policy / confirmation
  -> tool execution
  -> current-world state update
  -> experience/audit record
  -> verified result + state returned to Gemini
```

## Implemented in this build

- Unified discovered-action execution through `agent/control_runtime.py`.
- Persistent in-memory `computer/state.py` for current application, browser, URL, media state, task goal, last action, and observation.
- `dobby_context` tool for inspecting current Dobby/computer context.
- `dobby_learning` tool for inspecting local execution/recovery history.
- Local `memory/experience.py` JSONL experience store.
- Computer/browser actions record success/failure and recovery attempts.
- Current user turn becomes the active task goal so follow-up commands can resolve `it`, `this`, `that`, pause/resume, etc. against the active context.
- YouTube player controls: play, pause, resume, play/pause, stop, volume, mute/unmute, seek, fullscreen, skip-ad.
- YouTube control path focuses the current browser instead of reopening/searching for player-control commands.
- Visual YouTube Skip Ad path uses the current screen rather than a new web search.
- Browser tool has visual fallback actions and explicit current/observe actions.
- Browser tool descriptions now prioritize continuing the existing page/session.
- Prompt rules now explicitly require stateful multi-step execution, observation, verification, and strategy change after failure.
- Sensitive/destructive operations still use Dobby's human-controlled confirmation gate.

## Existing capabilities retained

- Gemini Live voice interface
- wake word / push-to-talk
- text input
- dynamic action discovery
- browser automation
- mouse/keyboard control
- screenshot and visual element finding
- memory system
- undo
- proactive/background monitoring
- model/provider registry
- autonomous planning/task infrastructure
- development/coding-agent infrastructure
- plugin discovery
- audit and risk policy

## Important limitation

This build cannot be fully end-to-end tested inside a headless Linux container because real mouse/keyboard/screen control requires a graphical desktop. The intended runtime target is the user's interactive Windows/macOS/Linux desktop.

The existing full test suite also contains an unrelated Phase-10 diagnostics/CLI failure and some long-running tests. The new computer-control/state tests and Phase-1 regression tests pass.

## Next integration test on the real desktop

Run Dobby interactively and test exactly:

1. "Open YouTube."
2. "Play [song]."
3. "Pause it."
4. "Play it."
5. "Increase the volume."
6. "Decrease the volume."
7. "Mute it."
8. "Unmute it."
9. "Skip forward."
10. When an ad appears: "Do you see the Skip Ad button?"
11. "Click it."
12. Verify the ad disappears.
13. "Open another tab."
14. "Go back."
15. "Close this tab."

The key acceptance criterion is that follow-up commands operate on the current environment instead of repeatedly searching Google or reopening the task.
