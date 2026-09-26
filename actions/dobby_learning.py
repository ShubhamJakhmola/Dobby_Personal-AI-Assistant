from memory.experience import recent

def dobby_learning(parameters=None, **kwargs):
    params=parameters or {}
    rows=recent(int(params.get("limit",20)))
    if not rows:
        return "No execution experiences recorded yet."
    successes=sum(1 for x in rows if x.get("success"))
    recoveries=sum(1 for x in rows if x.get("recovery"))
    failures=len(rows)-successes
    recent_actions=[f"{x.get('action')}: {'ok' if x.get('success') else 'failed'}" for x in rows[-10:]]
    return {"total":len(rows),"successes":successes,"failures":failures,"recoveries":recoveries,"recent":recent_actions}

TOOL={
    "name":"dobby_learning",
    "description":"Inspect Dobby's locally recorded execution experiences and recovery history. Use this to understand what worked or failed previously; it does not change the computer.",
    "parameters":{"type":"OBJECT","properties":{"limit":{"type":"INTEGER","description":"Number of recent experiences to inspect"}},"required":[]},
    "handler":dobby_learning,
    "risk_level":"L0",
    "supports_verification":True,
}
