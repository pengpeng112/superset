# -*- coding: utf-8 -*-
"""现场复现：36 星标 → welcome 面板，抓取异常详情。"""
import subprocess
import sys
import time
import urllib.request

import websocket

sys.path.insert(0, r"F:\python\superset\migration\sources\20261112-WARMUP-PERF")
from wb_run import Tab, new_tab  # noqa: E402

HERE = r"F:\python\superset\migration\sources\20261119-BI-ENHANCE"

proc = subprocess.Popen([r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                         "--remote-debugging-port=19650",
                         "--user-data-dir=" + HERE + r"\profile-favdbg",
                         "--no-first-run", "--no-default-browser-check",
                         "--window-size=1366,768", "about:blank"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(40):
    try:
        urllib.request.urlopen("http://127.0.0.1:19650/json/version", timeout=3)
        break
    except Exception:
        time.sleep(0.5)
info = new_tab(19650)
ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=60)
tab = Tab(ws)
tab.send("Page.enable")
tab.send("Runtime.enable")
print("login:", tab.login("admin", "<REDACTED-SUPERSET-ADMIN-PW>"))
tab.send("Page.navigate", {"url": "http://127.0.0.1:18180/superset/dashboard/36/"})
time.sleep(16)
print("star click:", tab.eval('(function(){var b=document.querySelector(".hh-fav-btn");if(b){b.click();return 1}return 0})()'))
time.sleep(2)
tab.send("Page.navigate", {"url": "http://127.0.0.1:18180/superset/welcome/"})
time.sleep(14)
for ev in tab.drain():
    if ev.get("method") == "Runtime.exceptionThrown":
        d = ev["params"].get("exceptionDetails", {})
        print("EXC:", d.get("text"), "|", (d.get("exception") or {}).get("description", "")[:400], "| url:", d.get("url", "")[:100])
print("panel:", tab.eval('(function(){var p=document.getElementById("hh-fav-panel");var m=document.querySelector("main[data-hh-home-content]");return JSON.stringify({panel:!!p,rows:p?p.querySelectorAll(".hh-fav-row").length:0,mainMarked:!!m,favAttr:m?m.getAttribute("data-hh-fav"):null,ver:(window.hospitalHomeUI||{}).version})})()'))
ws.close()
proc.terminate()
