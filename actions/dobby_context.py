from computer.state import get_state, observe_desktop

def dobby_context(parameters=None, **kwargs):
    params=parameters or {}
    if str(params.get("mode","state")).lower() == "observe":
        state=observe_desktop()
    else:
        state=get_state().snapshot()
    return state

TOOL={
    "name":"dobby_context",
    "description":"Inspect Dobby's current computer/task context. Use before acting when the user refers to the current screen, current app, current browser, 'this', 'that', or 'it'. This is local state and does not search the web.",
    "parameters":{"type":"OBJECT","properties":{"mode":{"type":"STRING","description":"state or observe (default state)"}},"required":[]},
    "handler":dobby_context,
    "risk_level":"L0",
    "supports_verification":True,
}
