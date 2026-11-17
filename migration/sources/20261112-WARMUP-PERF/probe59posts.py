# -*- coding: utf-8 -*-
"""探针3：只设日期，完整转储随后出现的 4 个 chart/data POST 明细。"""
import json
import sys
import time

sys.path.insert(0, r"F:\python\superset\migration\sources\20261112-WARMUP-PERF")
from wb_run import Tab, NetTracker, launch, new_tab  # noqa: E402
from guard_test import SET_DATE  # noqa: E402
import websocket  # noqa: E402

port = 19316
proc, ver = launch(r"C:\Program Files\Google\Chrome\Application\chrome.exe", "posts", port)
info = new_tab(port)
ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=30)
tab = Tab(ws)
tab.send("Page.enable")
tab.send("Network.enable", {"maxPostDataSize": 65536})
tr = NetTracker(tab)
tab.login("admin", "<REDACTED-SUPERSET-ADMIN-PW>")
tab.send("Page.navigate", {"url": "http://127.0.0.1:18180/superset/dashboard/59/"})
for _ in range(40):
    time.sleep(1)
    if (tab.eval("(document.querySelectorAll('.hdt-picker[data-filter-id]').length)||0") or 0):
        break
time.sleep(3)
tr.poll()
print("baseline posts:", tr.snapshot(), flush=True)
for rid, rec in list(tr.done.items()):
    print("  BASE", rec.get("url", "")[-60:], rec.get("ms"), rec.get("rowcount"), flush=True)

print(tab.eval(SET_DATE % ("NATIVE_FILTER-P59-DATE", "2026-10-01", "2026-11-13")), flush=True)
for i in range(12):
    time.sleep(1)
    tab.eval("1+1")
    tr.poll()
snap = tr.snapshot()
print("after-date posts:", snap, flush=True)
for rid, rec in tr.done.items():
    if rid in ():
        continue
    try:
        j = json.loads(rec.get("post") or "{}")
        fd = j.get("form_data") or {}
        print("POST url=…%s" % rec.get("url", "")[-70:], flush=True)
        print("  viz=%s slice=%s ds=%s queries=%s" % (
            fd.get("viz_type"), fd.get("slice_id"), j.get("datasource"), len(j.get("queries") or [])), flush=True)
        q0 = (j.get("queries") or [{}])[0]
        print("  filters=%s time_range=%s" % (json.dumps(q0.get("filters"))[:160], str(q0.get("extras", {}).get("time_range"))[:60]), flush=True)
        print("  ms=%s hit=%s rows=%s status=%s" % (rec.get("ms"), rec.get("hit"), rec.get("rowcount"), rec.get("status")), flush=True)
    except Exception as e:
        print("  parse:", repr(e)[:80], str(rec)[:200], flush=True)
ws.close()
proc.terminate()
time.sleep(1)
proc.kill()
