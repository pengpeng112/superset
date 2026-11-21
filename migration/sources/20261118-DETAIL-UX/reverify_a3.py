# -*- coding: utf-8 -*-
"""重跑 A3 交互段（max-padding 补丁后），把结果合并进 detail_ux_acceptance.json。"""
import json
import os
import subprocess
import sys
import time
import urllib.request

import websocket

sys.path.insert(0, r"F:\python\superset\migration\sources\20261112-WARMUP-PERF")
from wb_run import Tab, new_tab  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
GEO_NS = r"""(function(){
  var de=document.documentElement;
  var hs=document.querySelectorAll('.dashboard-component-chart-holder[class*="dashboard-chart-id-"]');
  var first=null;
  for(var i=0;i<hs.length;i++){var r0=hs[i].getBoundingClientRect();if(r0.height>60){first=hs[i];break;}}
  if(!first&&hs.length)first=hs[0];
  var fr=first?first.getBoundingClientRect():null;
  var chart=document.querySelector('.superset-chart-table');
  var tbls=chart?chart.querySelectorAll('table'):[];
  var dataTb=null;
  for(var i=0;i<tbls.length;i++){var b=tbls[i].querySelector('tbody');if(b&&b.rows.length){dataTb=tbls[i];break;}}
  var scr=dataTb?dataTb.parentElement:null;
  return JSON.stringify({innerH:window.innerHeight,holdT:fr?Math.round(fr.top):null,scrH:scr?scr.clientHeight:null});
})()"""

proc = subprocess.Popen([r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                         "--remote-debugging-port=19560",
                         "--user-data-dir=" + HERE + r"\profile-vdx-a3r",
                         "--no-first-run", "--no-default-browser-check",
                         "--window-size=1366,768", "about:blank"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(40):
    try:
        urllib.request.urlopen("http://127.0.0.1:19560/json/version", timeout=3)
        break
    except Exception:
        time.sleep(0.5)
info = new_tab(19560)
ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=60)
tab = Tab(ws)
tab.send("Page.enable")
tab.send("Runtime.enable")
errs = []
tab.login("admin", os.environ.get("VDX_ADMIN", ""))
tab.send("Page.navigate", {"url": "http://127.0.0.1:18180/superset/dashboard/36/"})
for _ in range(12):
    time.sleep(4)
    n = tab.eval("document.querySelectorAll('.dashboard-component-chart-holder[class*=\"dashboard-chart-id-\"]').length")
    if n and int(n) >= 1:
        break
    tab.eval("location.reload()")
time.sleep(5)
checks = []


def rec(name, ok, detail=""):
    checks.append({"name": "chrome-1366x768-admin-A3/" + name, "pass": bool(ok), "detail": str(detail)[:300]})
    print(("PASS " if ok else "FAIL ") + name, detail, flush=True)


g2 = json.loads(tab.eval(GEO_NS))
tab.eval("(function(){var b=document.querySelector('.hh-btn-max-table');if(b){b.click();return 1}return 0})()")
time.sleep(2)
hd = tab.tab = tab.eval("(function(){var h=document.querySelector('header');return h?getComputedStyle(h).display:'none'})()")
g3 = json.loads(tab.eval(GEO_NS))
gain3 = (g3.get("scrH") or 0) - (g2.get("scrH") or 0)
rec("A3-max-header-hidden", hd == "none", "header display=%s" % hd)
rec("A3-max-fill", gain3 >= 100 and (g3.get("holdT") or 999) <= 48,
    "scrollH gain=%spx holderTop %s->%s（顶距含 Superset 原生 emotion 布局层残余 padding，main/dashboard-content/holder 已压 0）" % (gain3, g2.get("holdT"), g3.get("holdT")))
tab.send("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})
tab.send("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})
time.sleep(2)
hd2 = tab.eval("(function(){var h=document.querySelector('header');return h?getComputedStyle(h).display:'block'})()")
rec("A3-esc-restore", hd2 != "none", "header display=%s" % hd2)
for ev in tab.drain():
    if ev.get("method") == "Runtime.exceptionThrown":
        errs.append(str(ev)[:100])
rec("pageerror-A3", len(errs) == 0, "%d errors" % len(errs))
ws.close()
proc.terminate()

outp = os.path.join(HERE, "evidence", "detail_ux_acceptance.json")
d = json.load(open(outp, encoding="utf-8"))
names = {c["name"] for c in checks}
d["checks"] = [c for c in d["checks"] if c["name"] not in names] + checks
d["reverify"] = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                 "note": "max-padding 补丁（html.hh-table-max main padding:0）后单独重跑 A3 全屏段并合并"}
total = len(d["checks"])
passed = len([c for c in d["checks"] if c["pass"]])
d["summary"] = {"total": total, "passed": passed, "failed": total - passed,
                "result": "PASS" if passed == total else "FAIL"}
json.dump(d, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("SUMMARY:", d["summary"], flush=True)
