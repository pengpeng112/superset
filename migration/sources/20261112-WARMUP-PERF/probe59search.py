# -*- coding: utf-8 -*-
"""探针2：V2 用搜索过滤选 99（不滚动虚拟列表），监测响应性。"""
import sys
import time

sys.path.insert(0, r"F:\python\superset\migration\sources\20261112-WARMUP-PERF")
from wb_run import Tab, NetTracker, launch, new_tab  # noqa: E402
from guard_test import open_select, pick_option, SET_DATE  # noqa: E402
import websocket  # noqa: E402

port = 19315
proc, ver = launch(r"C:\Program Files\Google\Chrome\Application\chrome.exe", "srch", port)
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
print("type V1:", tab.eval(TYPE_SEARCH % ("NATIVE_FILTER-P59-V1", "1")), flush=True)
time.sleep(0.8)
print("pick V1:", pick_option(tab, "1"), flush=True)
time.sleep(1.2)
print("open V2:", open_select(tab, "NATIVE_FILTER-P59-V2"), flush=True)
time.sleep(1.0)
print("type V2:", tab.eval(TYPE_SEARCH % ("NATIVE_FILTER-P59-V2", "99")), flush=True)
time.sleep(0.8)
print("pick V2:", pick_option(tab, "99"), flush=True)
time.sleep(1.5)
for i in range(6):
    time.sleep(3)
    try:
        tab.eval("1+1")
        st = tab.eval("""(function(){var g=window.hospitalVisitGuard;
          var l=g.draftValue('NATIVE_FILTER-P59-V1'),h=g.draftValue('NATIVE_FILTER-P59-V2');
          return JSON.stringify({l:l&&l.value,h:h&&h.value,span:g.dateSpan(),tip:(document.getElementById('hdt-span-tip')||{}).textContent||null,msg:(document.getElementById('hdt-visit-msg')||{}).textContent||null});})()""")
        print("t+%ds ok %s" % ((i + 1) * 3, st), flush=True)
    except Exception as e:
        print("t+%ds FROZE %s" % ((i + 1) * 3, repr(e)[:80]), flush=True)
        break
ws.close()
proc.terminate()
time.sleep(1)
proc.kill()
