# -*- coding: utf-8 -*-
"""诊断10：35 页工具条 CSV 导出的响应字节 + 原生菜单导出对比。"""
import base64
import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from acc2_run import Tab, login, launch, new_tab, USERS  # noqa

import websocket

BASE = "http://127.0.0.1:18180"


def main():
    USERS.update({"admin": os.environ["ACC_ADMIN"]})
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9450
    dl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
    os.makedirs(dl, exist_ok=True)
    proc, ver = launch("C:/Program Files/Google/Chrome/Application/chrome.exe", port,
                       os.path.abspath("profile-diag14"), 1500, 950)
    info = new_tab(port)
    bws = websocket.create_connection(
        __import__("acc2_run", fromlist=["http_json"]).http_json(
            "http://127.0.0.1:%d/json/version" % port)["webSocketDebuggerUrl"], timeout=20)
    bws.send(json.dumps({"id": 1, "method": "Browser.setDownloadBehavior",
                         "params": {"behavior": "allow", "downloadPath": dl, "eventsEnabled": True}}))
    time.sleep(0.5)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=40)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Runtime.enable")
    tab.send("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": dl})
    ev_ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=40)
    reqs = {}

    def listen():
        ev_ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
        mid = 10
        while True:
            try:
                raw = ev_ws.recv()
            except Exception:
                return
            try:
                m = json.loads(raw)
            except Exception:
                continue
            if m.get("method") == "Network.requestWillBeSent":
                r = m["params"]["request"]
                if "/api/v1/chart/data" in r.get("url", "") and r.get("method") == "POST":
                    reqs[m["params"]["requestId"]] = {"t": time.time(), "url": r["url"][:90],
                                                      "body": r.get("postData", "")[:2000]}
            elif m.get("method") == "Network.loadingFinished":
                rid = m["params"]["requestId"]
                if rid in reqs:
                    try:
                        b = ev_ws.send(json.dumps({"id": mid, "method": "Network.getResponseBody",
                                                   "params": {"requestId": rid}}))
                        mid += 1
                    except Exception:
                        pass
            elif m.get("method", "").startswith("Browser.download"):
                print("[dl]", m["method"], json.dumps(m.get("params", {}))[:160], flush=True)

    threading.Thread(target=listen, daemon=True).start()
    ok, det = login(tab, "admin")
    print("login:", ok)
    tab.navigate(BASE + "/superset/dashboard/35/")
    tab.wait("!!document.querySelector('.hh-query-toolbar')", timeout=60)
    for i in range(60):
        s = tab.eval("((document.querySelector('.hh-query-toolbar .hh-qt-summary')||{}).textContent||'')")
        if "共返回" in s:
            break
        time.sleep(1)
    print("summary:", s)
    time.sleep(2)
    # 工具条 CSV：console 内 fetch 同构导出（读响应字节，判断服务器行为）
    out = tab.eval(r"""(function(){
var e=document.querySelector('[data-test="grid-content"]');
var k=e&&Object.keys(e).filter(function(k){return k.indexOf('__reactFiber')===0;})[0];
var f=e&&e[k],store=null;while(f){var p=f.memoizedProps,s=p&&(p.store||(p.value&&p.value.store));
if(s&&s.getState){store=s;break;}f=f.return;}
var st=store.getState();
var h=document.querySelector('.dashboard-component-chart-holder[class*="dashboard-chart-id-"]');
var m=(h.className||'').match(/dashboard-chart-id-(\d+)/);var c=st.charts[m[1]];
var info={chartId:m[1],status:c.chartStatus,rowcount:(c.queriesResponse&&c.queriesResponse[0]||{}).rowcount,
sqlRowcount:(c.queriesResponse&&c.queriesResponse[0]||{}).sql_rowcount,
postProc:JSON.stringify(((c.queriesResponse||[{}])[0].query||{}).post_processing||[]),
respResultFormat:(c.queriesResponse||[{}])[0].result_format};
/* 用我们 hook 的缓存直接发 csv —— 通过检查 window.fetch 是否 hooked */
return JSON.stringify(info);})()"""
    )
    print("chart info:", out)
    # 检查 hook 是否存在及缓存条数（间接：window.fetch.toString 含 lastQueryContext?）
    hooked = tab.eval("(window.fetch.toString().indexOf('lastQueryContext')>=0)")
    print("fetch hooked:", hooked)
    # 真实点击 CSV 按钮
    pos = tab.eval("(function(){var b=document.querySelector('button.hh-btn-csv');var r=b.getBoundingClientRect();return JSON.stringify({x:r.left+r.width/2,y:r.top+r.height/2});})()")
    p = json.loads(pos)
    for typ in ("mousePressed", "mouseReleased"):
        tab.send("Input.dispatchMouseEvent", {"type": typ, "x": p["x"], "y": p["y"], "button": "left", "clickCount": 1})
    time.sleep(12)
    files = sorted(os.listdir(dl))
    print("downloads:", files)
    for fn in files:
        fp = os.path.join(dl, fn)
        with open(fp, "rb") as f:
            head = f.read(16)
        print("  %s size=%d head=%r" % (fn, os.path.getsize(fp), head))
    # 网络请求记录
    for rid, r in reqs.items():
        print("REQ", "%.1f" % r["t"], r["url"][:80], "| body head:", r["body"][:120].replace("\n", " "))
    proc.terminate()
    time.sleep(1.5)
    proc.kill()


if __name__ == "__main__":
    main()
