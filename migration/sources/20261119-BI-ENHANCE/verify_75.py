# -*- coding: utf-8 -*-
"""重验 75 全图渲染 + KPI 数值断言（admin）。port 参数化。"""
import json
import subprocess
import sys
import time
import urllib.request

import websocket

sys.path.insert(0, r"F:\python\superset\migration\sources\20261112-WARMUP-PERF")
from wb_run import Tab, new_tab  # noqa: E402

HERE = r"F:\python\superset\migration\sources\20261119-BI-ENHANCE"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 19576
TAG = sys.argv[2] if len(sys.argv) > 2 else "v75a"

proc = subprocess.Popen([r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                         "--remote-debugging-port=%d" % PORT,
                         "--user-data-dir=" + HERE + r"\\profile-" + TAG,
                         "--no-first-run", "--no-default-browser-check",
                         "--window-size=1366,768", "about:blank"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(40):
    try:
        urllib.request.urlopen("http://127.0.0.1:%d/json/version" % PORT, timeout=3)
        break
    except Exception:
        time.sleep(0.5)
info = new_tab(PORT)
ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=30)
tab = Tab(ws)
tab.send("Page.enable")
tab.login("admin", "<REDACTED-SUPERSET-ADMIN-PW>")
tab.send("Page.navigate", {"url": "http://127.0.0.1:18180/superset/dashboard/75/"})
got = False
for i in range(10):
    time.sleep(3)
    n = tab.eval('document.querySelectorAll(".dashboard-component-chart-holder[class*=dashboard-chart-id-]").length')
    if n and int(n) >= 7:
        got = True
        break
    tab.eval("location.reload()")
time.sleep(4)
r = tab.eval(r"""(function(){
  var hs=document.querySelectorAll('.dashboard-component-chart-holder[class*="dashboard-chart-id-"]');
  var out=[];
  for(var i=0;i<hs.length;i++){
    var h=hs[i];
    var cid=(String(h.className).match(/dashboard-chart-id-(\d+)/)||[])[1];
    var err=(h.querySelector('.ant-alert-error')||{textContent:''}).textContent.slice(0,70);
    var txt=(h.textContent||'').replace(/\s+/g,' ').slice(0,110);
    var rendered=!!h.querySelector('svg,canvas,table,.ant-empty');
    out.push({cid:cid,rendered:rendered,err:err,txt:txt});
  }
  return JSON.stringify({n:hs.length,charts:out});
})()""")
print(r)
ws.close()
proc.terminate()
