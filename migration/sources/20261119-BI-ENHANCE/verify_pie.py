# -*- coding: utf-8 -*-
"""重验 398 饼图（带 reload 自愈）。"""
import subprocess
import sys
import time
import urllib.request

import websocket

sys.path.insert(0, r"F:\python\superset\migration\sources\20261112-WARMUP-PERF")
from wb_run import Tab, new_tab  # noqa: E402

HERE = r"F:\python\superset\migration\sources\20261119-BI-ENHANCE"

proc = subprocess.Popen([r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                         "--remote-debugging-port=19575",
                         "--user-data-dir=" + HERE + r"\profile-pie4",
                         "--no-first-run", "--no-default-browser-check",
                         "--window-size=1366,768", "about:blank"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(40):
    try:
        urllib.request.urlopen("http://127.0.0.1:19574/json/version", timeout=3)
        break
    except Exception:
        time.sleep(0.5)
info = new_tab(19575)
ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=30)
tab = Tab(ws)
tab.send("Page.enable")
tab.login("admin", "<REDACTED-SUPERSET-ADMIN-PW>")
tab.send("Page.navigate", {"url": "http://127.0.0.1:18180/superset/dashboard/75/"})
got = False
for i in range(8):
    time.sleep(3)
    n = tab.eval('document.querySelectorAll(".dashboard-component-chart-holder[class*=dashboard-chart-id-]").length')
    if n and int(n) >= 7:
        got = True
        break
    tab.eval("location.reload()")
print("holders ready:", got)
r = tab.eval('(function(){var h=document.querySelector(".dashboard-chart-id-398");if(!h)return "noholder";var err=(h.querySelector(".ant-alert-error")||{textContent:""}).textContent.slice(0,90);var svg=!!h.querySelector("svg");var txt=(h.textContent||"").replace(/\\s+/g," ").slice(0,140);return JSON.stringify({err:err,svg:svg,txt:txt})})()')
print("pie:", r)
ws.close()
proc.terminate()
