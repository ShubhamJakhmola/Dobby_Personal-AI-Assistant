"""Single execution boundary for Dobby computer/browser/application actions."""
from __future__ import annotations
import json, time
from security.policy import classify
from core import confirm as confirm_gate
from security.audit import record as audit
from memory.experience import record as experience
from computer.state import get_state, update_state, observe_desktop

COMPUTER_PREFIXES=("computer_control","computer_","browser_control","youtube_video","open_app","application_manager","computer_application","computer_window","computer_settings")

class ControlRuntime:
    def __init__(self, registry, confirmation=None, player=None):
        self.registry=registry; self.confirmation=confirmation; self.player=player

    def _state_for_result(self, action, args, result):
        text=str(result)
        update_state(last_action={"action":action,"arguments":dict(args),"result":text[:1000],"timestamp":time.time()})
        if action=="youtube_video":
            op=str(args.get("action","play")).lower()
            media={"play":"playing","resume":"playing","play_pause":"playing","pause":"paused","stop":"stopped"}.get(op)
            if media: update_state(media_state=media)
            if op=="volume_up": update_state(media_volume=min(100,(get_state().media_volume or 50)+int(args.get("amount",1))*5))
            if op=="volume_down": update_state(media_volume=max(0,(get_state().media_volume or 50)-int(args.get("amount",1))*5))
            if op=="skip_ad": update_state(ad_detected=False)
        elif action=="browser_control":
            op=str(args.get("action",""))
            if op in {"go_to","new_tab"}: update_state(active_browser=args.get("browser") or get_state().active_browser, active_url=args.get("url") or get_state().active_url)
            elif op=="search": update_state(active_browser=args.get("browser") or get_state().active_browser, active_url="search:"+str(args.get("query","")))
        return get_state().snapshot()

    def execute(self, action:str, args:dict|None=None, context:dict|None=None, retries:int=1)->dict:
        args=dict(args or {}); context=dict(context or {})
        decision=classify(action,args)
        if decision.requires_confirmation:
            # Use the same human-controlled HUD gate as the rest of Dobby. The
            # model never supplies the confirmation token. The action is parked
            # and only runs if the user presses CONFIRM on the interface.
            if self.confirmation:
                approved = bool(self.confirmation(action, args, decision.reason))
                if not approved:
                    return {"success":False,"status":"waiting_confirmation","error_category":"user_cancelled","error":decision.reason,"action":action,"verified":False}
            else:
                import functools
                def _run_after_confirmation():
                    return self.registry.run(action, args, {})
                pending = confirm_gate.request(
                    f"Allow {action}",
                    f"Dobby wants to perform: {action}",
                    _run_after_confirmation,
                )
                return {"success":False,"status":"waiting_confirmation","error_category":"confirmation_required","error":pending,"action":action,"verified":False}
        if not decision.allowed and not decision.requires_confirmation:
            return {"success":False,"status":"failed","error_category":"policy_denied","error":decision.reason,"action":action,"verified":False}
        task=get_state().task_goal or "interactive computer task"
        last=None
        for attempt in range(retries+1):
            raw=self.registry.run(action,args,context)
            last=raw or "Done."
            # Tool actions frequently return structured JSON.  Do not infer
            # success from the presence/absence of words in JSON; honour the
            # explicit success field first, then fall back to conservative text
            # detection for legacy actions.
            success = None
            if isinstance(last, dict) and "success" in last:
                success = bool(last.get("success"))
            elif isinstance(last, str):
                try:
                    parsed=json.loads(last)
                    if isinstance(parsed, dict) and "success" in parsed:
                        success = bool(parsed.get("success"))
                except Exception:
                    pass
            if success is None:
                failed=isinstance(last,str) and any(x in last.lower() for x in ("failed","error:","not found","unknown action","timed out","unsupported"))
                success=not failed
            state=self._state_for_result(action,args,last)
            experience(task,action,success,last,recovery=attempt>0)
            audit(selected_tool=action, arguments=args, success=success, recovery=attempt>0)
            if success:
                return {"success":True,"status":"completed","action":action,"verified":action in COMPUTER_PREFIXES,"attempts":attempt+1,"result":last,"computer_state":state}
            if attempt<retries:
                observe_desktop()
                time.sleep(0.15)
        return {"success":False,"status":"failed","action":action,"verified":False,"attempts":retries+1,"error":str(last),"computer_state":get_state().snapshot()}
