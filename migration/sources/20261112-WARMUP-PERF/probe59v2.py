# -*- coding: utf-8 -*-
"""探针4：修复节流后，V2 用搜索选 99；被拦点击后转储 POST 明细。"""
import json
import sys
import time

sys.path.insert(0, r"F:\python\superset\migration\sources\20261112-WARMUP-PERF")
from wb_run import Tab, NetTracker, launch, new_tab  # noqa: E402
from guard_test import open_select, pick_option, SET_DATE, click_apply  # noqa: E402
import websocket  # noqa: E402

port = 19317
proc, ver = launch(r"C:\Program Files\Google\Chrome\Application\chrome.exe", "v2p", port)
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

TYPE_SEARCH = """(function(id,q){
  var i=document.getElementById(id);if(!i)return 'no-input';
  i.focus();
  var set=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
  set.call(i,q);
  i.dispatchEvent(new Event('input',{bubbles:true}));
  return 'typed '+q;
})("%s","%s")"""

print(tab.eval(SET_DATE % ("NATIVE_FILTER-P59-DATE", "2026-10-01", "2026-11-13")), flush=True)
time.sleep(1.0)
print("open V1:", open_select(tab, "NATIVE_FILTER-P59-V1"), flush=True)
time.sleep(1.0)
print("pick V1:", pick_option(tab, "1"), flush=True)
time.sleep(1.2)
print("open V2:", open_select(tab, "NATIVE_FILTER-P59-V2"), flush=True)
time.sleep(1.0)
print("type V2:", tab.eval(TYPE_SEARCH % ("NATIVE_FILTER-P59-V2", "99")), flush=True)
time.sleep(0.8)
print("pick V2:", pick_option(tab, "99", tries=8), flush=True)
time.sleep(1.5)
try:
    st = tab.eval("""(function(){var g=window.hospitalVisitGuard;
      return JSON.stringify({l:g.draftValue('NATIVE_FILTER-P59-V1'),h:g.draftValue('NATIVE_FILTER-P59-V2'),
        span:g.dateSpan(),tip:(document.getElementById('hdt-span-tip')||{}).textContent||null,msg:(document.getElementById('hdt-visit-msg')||{}).textContent||null});})()""")
    print("STATE:", st, flush=True)
except Exception as e:
    print("STATE FROZE:", repr(e)[:80], flush=True)

# 被拦点击后的 POST 明细
tab.eval("1+1")
tr.poll()
tr.reset()
print("click:", click_apply(tab), flush=True)
t0 = time.time()
while time.time() - t0 < 5:
    time.sleep(0.5)
    tab.eval("1+1")
    tr.poll()
print("posts after blocked click:", tr.snapshot(), flush=True)
for rid, rec in tr.done.items():
    try:
        j = json.loads(rec.get("post") or "{}")
        fd = j.get("form_data") or {}
        print("POST viz=%s slice=%s ds=%s ms=%s" % (fd.get("viz_type"), fd.get("slice_id"), j.get("datasource"), rec.get("ms")), flush=True)
    except Exception:
        print("POST raw:", str(rec)[:160], flush=True)
print("msg after click:", tab.eval("(document.getElementById('hdt-visit-msg')||{}).textContent"), flush=True)
ws.close()
proc.terminate()
time.sleep(1)
proc.kill()
