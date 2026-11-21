# -*- coding: utf-8 -*-
"""单独重验 chrome-1366x768-admin 的 32 号（首轮会话停滞致 bottom=None），合并进验收 JSON。"""
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
P32 = r"""(function(){
  var hs=document.querySelectorAll('.dashboard-component-chart-holder[class*="dashboard-chart-id-"]');
  var fr=hs.length?hs[0].getBoundingClientRect():null;
  var se=document.scrollingElement||document.documentElement;
  var hm=document.querySelector('#hospital-monthly-report .hm-scroll');
  var hf=document.querySelector('#hospital-monthly-report .hm-footer');
  return JSON.stringify({innerH:window.innerHeight,holdB:fr?Math.round(fr.bottom):null,
    hmB:hm?Math.round(hm.getBoundingClientRect().bottom):null,
    hmFootB:hf?Math.round(hf.getBoundingClientRect().bottom):null,
    ovf:se.scrollHeight-window.innerHeight,ready:!!hm});
})()"""

proc = subprocess.Popen([r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                         "--remote-debugging-port=19565",
                         "--user-data-dir=" + HERE + r"\profile-vdx-p32r",
                         "--no-first-run", "--no-default-browser-check",
                         "--window-size=1366,768", "about:blank"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(40):
    try:
        urllib.request.urlopen("http://127.0.0.1:19565/json/version", timeout=3)
        break
    except Exception:
        time.sleep(0.5)
info = new_tab(19565)
ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=60)
tab = Tab(ws)
tab.send("Page.enable")
tab.send("Runtime.enable")
errs = []
tab.login("admin", os.environ.get("VDX_ADMIN", ""))
tab.send("Page.navigate", {"url": "http://127.0.0.1:18180/superset/dashboard/32/"})
g = None
for _ in range(12):
    time.sleep(4)
    try:
        raw = tab.eval(P32)
        g = json.loads(raw)
        if g.get("ready"):
            break
    except Exception:
        pass
    tab.eval("location.reload()")
time.sleep(3)
g = json.loads(tab.eval(P32))
for ev in tab.drain():
    if ev.get("method") == "Runtime.exceptionThrown":
        errs.append(str(ev)[:100])
ws.close()
proc.terminate()

bottom = g.get("hmFootB") or g.get("hmB") or g.get("holdB")
ok = bottom is not None and bottom <= g["innerH"] + 1
chk = {"name": "chrome-1366x768-admin/A1-p32", "pass": bool(ok),
       "detail": "bottom=%s innerH=%s ovf=%s（首轮会话停滞重验）" % (bottom, g.get("innerH"), g.get("ovf"))}
print(("PASS " if ok else "FAIL "), chk["detail"], flush=True)

outp = os.path.join(HERE, "evidence", "detail_ux_acceptance.json")
d = json.load(open(outp, encoding="utf-8"))
d["checks"] = [c for c in d["checks"] if c["name"] != chk["name"]] + [chk]
if errs:
    d.setdefault("pageerrors", {})["p32-reverify"] = errs[:3]
total = len(d["checks"])
passed = len([c for c in d["checks"] if c["pass"]])
d["summary"] = {"total": total, "passed": passed, "failed": total - passed,
                "result": "PASS" if passed == total else "FAIL"}
json.dump(d, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("SUMMARY:", d["summary"], flush=True)
