# -*- coding: utf-8 -*-
"""39 号专项探针：实证 pivot_table_v2 渲染 DOM（.superset-chart-table 不适用的选择器问题）。"""
import json
import os
import sys
import time

import websocket

sys.path.insert(0, r"F:\python\superset\migration\sources\20261112-WARMUP-PERF")
from wb_run import Tab, NetTracker, launch, new_tab  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "http://127.0.0.1:18180"
PIVOT_STATE = """(function(){
  var holder=document.querySelector('.dashboard-component-chart-holder');
  var charts=document.querySelectorAll('.dashboard-component-chart-holder');
  var anyTable=null;
  document.querySelectorAll('.dashboard-component-chart-holder table').forEach(function(t){
    var n=t.querySelectorAll('tbody tr').length;
    if(!anyTable||n>anyTable.rows)anyTable={rows:n,cls:t.className.slice(0,60),header:t.querySelectorAll('thead th').length};
  });
  var pt=document.querySelector('.pivot-table');
  var st=document.querySelector('.superset-chart-table');
  var sum=(document.querySelector('.hh-qt-summary')||{}).textContent||'';
  return JSON.stringify({holders:charts.length,rendered:[].slice.call(charts)
      .filter(function(h){return h.querySelector('svg,canvas,table,.ant-empty')}).length,
    pivot:!!pt,pivotRows:pt?pt.querySelectorAll('tbody tr').length:-1,
    supersetChartTable:!!st,anyHolderTable:anyTable,sum:sum.slice(0,50)});
})()"""

port = 19340
proc, ver = launch(r"C:\Program Files\Google\Chrome\Application\chrome.exe", "p39pv", port)
info = new_tab(port)
ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=30)
tab = Tab(ws)
tab.send("Page.enable")
tab.send("Network.enable", {"maxPostDataSize": 65536})
tr = NetTracker(tab)
tab.login("admin", "<REDACTED-SUPERSET-ADMIN-PW>")
tab.send("Page.navigate", {"url": BASE + "/superset/dashboard/39/"})
time.sleep(2)
for _ in range(30):
    if tab.eval("document.readyState") == "complete":
        break
    time.sleep(0.5)
final = None
t0 = time.time()
while time.time() - t0 < 90:
    try:
        st = json.loads(tab.eval(PIVOT_STATE))
        tr.poll()
    except Exception as e:
        print("eval err", repr(e)[:80], flush=True)
        time.sleep(1)
        continue
    if st["holders"] and st["sum"]:
        final = st
        if st["anyHolderTable"]:
            break
    time.sleep(1.5)
try:
    tr.poll()
except Exception:
    pass
snap = tr.snapshot()
hits = sum(1 for d in tr.done.values() if d.get("hit"))
print("FINAL:", json.dumps(final, ensure_ascii=False), flush=True)
print("posts:", snap, "hits:", hits, flush=True)
for rid, rec in tr.done.items():
    print("  post viz=%s slice=%s ms=%s hit=%s rows=%s status=%s" % (
        json.loads(rec["post"]).get("form_data", {}).get("viz_type") if rec.get("post") else "?",
        json.loads(rec["post"]).get("form_data", {}).get("slice_id") if rec.get("post") else "?",
        rec.get("ms"), rec.get("hit"), rec.get("rowcount"), rec.get("status")), flush=True)
out = os.path.join(HERE, "probe39-pivot.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump({"browser": ver, "final": final,
               "posts": [{"ms": r.get("ms"), "hit": r.get("hit"), "rows": r.get("rowcount"),
                          "status": r.get("status")} for r in tr.done.values()]}, f, ensure_ascii=False, indent=1)
print("saved", out, flush=True)
ws.close()
proc.terminate()
time.sleep(1)
proc.kill()
