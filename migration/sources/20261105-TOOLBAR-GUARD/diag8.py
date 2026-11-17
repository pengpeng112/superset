# -*- coding: utf-8 -*-
"""诊断8：点击导出按钮后三态判定——handler 是否触发（按钮 busy）、fetch 是否发出（hook 计数）、响应。"""
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
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9420
    which = sys.argv[2] if len(sys.argv) > 2 else "65"
    proc, ver = launch("C:/Program Files/Google/Chrome/Application/chrome.exe", port,
                       os.path.abspath("profile-diag12"), 1500, 950)
    info = new_tab(port)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=40)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Runtime.enable")
    ev_ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=40)
    calls = []

    def listen():
        ev_ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
        while True:
            try:
                raw = ev_ws.recv()
            except Exception:
                return
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            m = msg.get("method")
            if m == "Network.requestWillBeSent":
                r = msg["params"]["request"]
                if "/api/v1/chart/data" in r.get("url", ""):
                    calls.append((time.time(), r["url"][:100], len(r.get("postData", ""))))
            elif m == "Network.loadingFailed":
                calls.append((time.time(), "FAILED " + msg["params"].get("errorText", "")[:80], 0))
            elif m == "Network.responseReceived":
                r = msg["params"]["response"]
                if "chart/data" in r.get("url", ""):
                    calls.append((time.time(), "RESP %s %s" % (r.get("status"), r.get("mimeType", "")), 0))

    threading.Thread(target=listen, daemon=True).start()
    ok, det = login(tab, "admin")
    print("login:", ok)
    tab.navigate(BASE + "/superset/dashboard/%s/" % which)
    tab.wait("!!document.querySelector('.hh-query-toolbar')", timeout=60)
    for i in range(150):
        s = tab.eval("((document.querySelector('.hh-query-toolbar .hh-qt-summary')||{}).textContent||'')")
        if "共返回" in s:
            break
        time.sleep(1)
    print("summary0:", s)
    calls.clear()
    # 真实手势点击 xlsx
    pos = tab.eval(
        "(function(){var b=document.querySelector('button.hh-btn-xlsx');if(!b)return '';"
        "var r=b.getBoundingClientRect();return JSON.stringify({x:r.left+r.width/2,y:r.top+r.height/2,"
        "w:r.width,h:r.height,disabled:b.disabled});})()"
    )
    print("btn pos:", pos)
    p = json.loads(pos)
    for typ in ("mousePressed", "mouseReleased"):
        tab.send("Input.dispatchMouseEvent", {"type": typ, "x": p["x"], "y": p["y"], "button": "left", "clickCount": 1})
    for i in range(75):
        time.sleep(1)
        st = tab.eval(
            "(function(){var b=document.querySelector('button.hh-btn-xlsx');"
            "var s=document.querySelector('.hh-query-toolbar .hh-qt-summary');"
            "return JSON.stringify({txt:b?b.textContent:'',disabled:b?b.disabled:null,note:s?s.textContent:''});})()"
        )
        if i in (1, 2, 3, 5, 10, 15, 20, 24, 30, 40, 50, 60, 70, 74):
            print("t+%02ds" % i, st[:160])
        if "已导出" in st or "失败" in st or "未捕获" in st:
            break
    print("network calls:")
    for t, u, n in calls:
        print("  %.1fs" % (t - calls[0][0] if calls else 0), u, n)
    dl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
    print("downloads:", os.listdir(dl) if os.path.isdir(dl) else [])
    proc.terminate()
    time.sleep(1.5)
    proc.kill()


if __name__ == "__main__":
    main()
