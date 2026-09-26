from __future__ import annotations
import json
from computer import desktop

def computer_window(parameters: dict, **_) -> str:
    p=parameters or {}; op=str(p.get("operation","list")).lower()
    try:
        if op=="list": data=desktop.list_windows()
        elif op=="get_active": data=desktop.active_window()
        elif op=="focus": data=desktop.focus_window(str(p["window_id"]))
        else: return json.dumps({"success":False,"error_category":"invalid_arguments"})
        if isinstance(data,dict) and "success" in data: ok=data["success"]
        else: ok=not (isinstance(data,dict) and data.get("available") is False)
        return json.dumps({"success":ok,"status":"completed" if ok else "failed","data":data,"verified":op in {"get_active","focus"}})
    except Exception as exc: return json.dumps({"success":False,"status":"failed","error_category":"capability_unavailable","error":str(exc)})

TOOL={"name":"computer_window","description":"Cross-platform window discovery and focus.","risk_level":"L1","supports_verification":True,"reversible":True,
"parameters":{"type":"OBJECT","properties":{"operation":{"type":"STRING"},"window_id":{"type":"STRING"}},"required":["operation"]},"handler":computer_window}
