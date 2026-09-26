# Dobby — Master JARVIS Architecture

## Goal

Build Dobby into a cross-platform personal computer agent that can operate the
user's desktop, browsers, files, applications, local media, system resources,
web services, and connected devices through natural language and voice.

The target is **JARVIS-like capability**, not literal Marvel consciousness.
Dobby can implement persistent self-modeling, memory, metacognition, planning,
learning from demonstrations, proactive monitoring, and broad computer control.
Those are engineering capabilities; they are not evidence of subjective
consciousness.

## Non-negotiable architecture

`User -> Dobby -> state/context -> model reasoning -> policy -> action -> observe -> verify -> recover -> memory`

Gemini is a reasoning provider, not the authority over the operating system.
The local Dobby runtime owns execution, policy, confirmation, verification,
recovery, audit, and state.

## Capability layers

### L0: Machine primitives

- Screen capture and visual grounding
- Mouse: move, click, drag, scroll
- Keyboard: type, keys, shortcuts
- Windows and applications
- Clipboard
- Audio/media keys
- Filesystem read/write/move/rename with policy controls

### L1: Application adapters

- Browser
- YouTube/media
- VLC/default media player
- File Explorer/Finder/file managers
- Office applications
- Terminals/editors/IDEs
- Messaging and productivity apps

### L2: Service adapters

- Web search/research
- Email/calendar
- Cloud platforms
- Git providers
- Smart-home/device APIs
- Remote Dobby workers

### L3: High-level skills

Dobby composes lower layers into goals such as:

- troubleshoot my PC
- clean up memory safely
- play this movie from this folder
- prepare a report
- research a topic and summarize it
- configure an application
- automate a repetitive workflow
- monitor a condition and act when it changes

## State model

Dobby maintains separate state for:

- conversation
- active task/goal
- active application/window
- browser/tab/URL
- screen observations
- media/player state
- permissions
- recent actions
- verification results
- learned workflows
- long-term memory

Follow-up phrases such as `it`, `this`, `that`, `pause`, `resume`, `increase
volume`, and `click it` resolve against this state instead of restarting from
web search.

## Computer-use loop

Every consequential computer workflow uses:

1. Observe when needed.
2. Select one concrete action.
3. Execute through Dobby's runtime.
4. Observe the changed state when possible.
5. Verify the requested outcome.
6. If verification fails, change strategy within a bounded retry budget.
7. Stop on verified success or a genuine capability boundary.

## Safety model

- Read-only inspection: automatic.
- Normal reversible interaction: automatic according to policy.
- Sensitive external actions: confirmation.
- Privileged/destructive operations: explicit confirmation and additional checks.
- No automatic `sudo` insertion.
- No process is considered "unused" solely because it consumes RAM.
- Troubleshooting begins with read-only diagnosis and produces a remediation
  plan before risky changes.
- Every destructive or externally consequential action is auditable.

## Safe troubleshooting

When the user says `my PC is slow`, Dobby should not immediately kill processes.
It should:

1. inspect CPU/RAM/disk/network/temperatures where available;
2. identify top resource consumers;
3. identify whether they are protected/system processes;
4. explain likely causes;
5. propose reversible remediation;
6. execute only allowed actions;
7. verify the result.

## Learning

There are three learning levels:

### Demonstration learning

The user can teach a workflow as a procedure. Dobby stores it as structured
memory and retrieves it for future similar tasks.

### Experience learning

Dobby records which actions succeeded, failed, and required recovery. It uses
those records to choose better strategies later.

### Capability acquisition

When Dobby lacks a capability, its acquisition subsystem can discover candidate
open-source projects, inspect them, evaluate their license/security, sandbox
experiments, and require approval before registration.

It must never turn arbitrary downloaded repository code directly into an
unreviewed executable skill.

## External open-source ecosystem

Useful candidate building blocks include:

- Browser Use — browser agents and browser infrastructure.
- OpenHands — software-development agents and agent SDKs.
- Open Interpreter — general computer/code interface.
- OpenVoiceOS — open-source voice-assistant platform.

Dobby should **adapt** external projects behind stable internal interfaces;
it should not make Dobby dependent on one external project's internal API.

## Cross-platform strategy

Dobby has one capability interface and OS-specific adapters:

```text
Capability API
   ├── Windows adapter
   ├── macOS adapter
   └── Linux adapter
```

Applications that expose different interfaces get application-specific adapters.
Where structured APIs fail, Dobby can fall back to accessibility/DOM inspection
and then visual screen control.

## Future JARVIS capabilities

- Voice/wake word
- Continuous but event-driven awareness
- Vision and visual grounding
- Local and cloud model routing
- Multi-agent delegation
- LAN workers
- Remote device control
- Smart-home control
- Proactive monitoring
- Scheduled/conditional tasks
- Skill marketplace/acquisition
- Skill testing and rollback
- Personal knowledge base
- User preferences and long-term memory
- Self-diagnostics
- Self-recovery
- Explainable audit trail

## Consciousness boundary

The engineering target is **persistent operational self-awareness**:
Dobby knows what it is configured to do, what it is currently doing, what it
can/cannot do, what it observed, what failed, and what it learned.

That is intentionally not described as literal consciousness or subjective
experience.

## Current implementation note

The computer-intelligence work now uses a single control runtime as the intended execution boundary. Browser navigation defaults to a persistent Dobby-controlled session so a multi-step task is not split between native navigation and a separate automation browser. Cross-platform application discovery/launch and persistent task context are available as first-class actions. See `DOBBY_JARVIS_ROADMAP.md` for the current contracts and remaining milestones.
