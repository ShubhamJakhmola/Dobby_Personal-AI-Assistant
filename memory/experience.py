"""Small local experience store for Dobby's practical learning."""
from __future__ import annotations
import json, os, threading
from datetime import datetime, timezone
from pathlib import Path

_LOCK=threading.Lock()
def path()->Path:
    root=Path(os.environ.get("DOBBY_DATA_DIR", Path.home()/".dobby")); root.mkdir(parents=True,exist_ok=True); return root/"experiences.jsonl"

def record(task:str, action:str, success:bool, result=None, recovery:bool=False)->None:
    entry={"timestamp":datetime.now(timezone.utc).isoformat(),"task":task,"action":action,"success":bool(success),"recovery":bool(recovery),"result":str(result)[:1000]}
    with _LOCK:
        with path().open("a",encoding="utf-8") as f: f.write(json.dumps(entry,ensure_ascii=True)+"\n")

def recent(limit:int=50)->list[dict]:
    p=path()
    if not p.exists(): return []
    rows=[]
    for line in p.read_text(encoding="utf-8").splitlines()[-max(1,int(limit)):]:
        try: rows.append(json.loads(line))
        except Exception: pass
    return rows
