from __future__ import annotations
import json
from computer import desktop

def computer_screen(parameters: dict, **_) -> str:
    p=parameters or {}; op=str(p.get("operation","list_monitors")).lower()
    if op=="list_monitors":
        monitors=desktop.screen_info(); return json.dumps({"success":True,"monitors":monitors,"backends":["mss"] if monitors else []})
    if op in {"capture","capture_all"}:
        try:
            from mss import mss
            with mss() as sct:
                mons=sct.monitors[1:]; idx=int(p.get("monitor",1)); targets=mons if op=="capture_all" else ([mons[idx-1]] if 0<idx<=len(mons) else [])
                if not targets: return json.dumps({"success":False,"error_category":"monitor_not_found"})
                frames=[]
                for m in targets:
                    shot=sct.grab(m); frames.append({"left":m["left"],"top":m["top"],"width":m["width"],"height":m["height"],"bytes":len(shot.raw)})
                return json.dumps({"success":True,"frames":frames})
        except Exception as exc: return json.dumps({"success":False,"error_category":"screen_capture_failed","error":str(exc)})
    return json.dumps({"success":False,"error_category":"invalid_arguments"})

TOOL={"name":"computer_screen","description":"Cross-platform monitor discovery and screen capture diagnostics.","risk_level":"L0","supports_verification":True,"reversible":True,
"parameters":{"type":"OBJECT","properties":{"operation":{"type":"STRING"},"monitor":{"type":"NUMBER"}},"required":["operation"]},"handler":computer_screen}
