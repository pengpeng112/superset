# -*- coding: utf-8 -*-
"""诊断9：CDP 下载行为设置回执验证（Browser/Page.setDownloadBehavior）+ 导出落盘。"""
import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from acc2_run import Tab, login, launch, new_tab, USERS, http_json  # noqa

import websocket

BASE = "http://127.0.0.1:18180"


def rpc(wsobj, mid, method, params, timeout=15):
    wsobj.send(json.dumps({"id": mid, "method": method, "params": params}))
    deadline = time.time() + timeout
    while time.time() < deadline:
        wsobj.settimeout(max(0.5, deadline - time.time()))
        try:
            raw = wsobj.recv()
        except Exception:
            continue
        msg = json.loads(raw)
        if msg.get("id") == mid:
            return msg
    return {"error": "timeout"}


def main():
    USERS.update({"admin": os.environ["ACC_ADMIN"]})
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9430
    which = sys.argv[2] if len(sys.argv) > 2 else "65"
    dl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
    os.makedirs(dl, exist_ok=True)
    proc, ver = launch("C:/Program Files/Google/Chrome/Application/chrome.exe", port,
                       os.path.abspath("profile-diag13"), 1500, 950)
    info = new_tab(port)
    # 1) browser 级 setDownloadBehavior —— 读回执
    bws = websocket.create_connection(http_json("http://127.0.0.1:%d/json/version" % port)["webSocketDebuggerUrl"], timeout=20)
    r1 = rpc(bws, 1, "Browser.setDownloadBehavior",
             {"behavior": "allow", "downloadPath": dl, "eventsEnabled": True})
    print("Browser.setDownloadBehavior ->", json.dumps(r1)[:200])
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=40)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Runtime.enable")
    # 2) tab 级 Page.setDownloadBehavior —— 读回执（旧 API）
    r2 = rpc(ws, 990, "Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": dl})
    print("Page.setDownloadBehavior ->", json.dumps(r2)[:200])
    # 3) 下载事件监听（browser ws）
    def listen():
        while True:
            try:
                raw = bws.recv()
            except Exception:
                return
            try:
                m = json.loads(raw)
            except Exception:
                continue
            if m.get("method", "").startswith("Browser.download"):
                print("[dl-event]", m["method"], json.dumps(m.get("params", {}))[:220], flush=True)

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
    pos = tab.eval("(function(){var b=document.querySelector('button.hh-btn-csv');if(!b)return '';var r=b.getBoundingClientRect();return JSON.stringify({x:r.left+r.width/2,y:r.top+r.height/2,disabled:b.disabled});})()")
    print("csv btn:", pos)
    p = json.loads(pos)
    for typ in ("mousePressed", "mouseReleased"):
        tab.send("Input.dispatchMouseEvent", {"type": typ, "x": p["x"], "y": p["y"], "button": "left", "clickCount": 1})
    for i in range(70):
        time.sleep(1)
        st = tab.eval("((document.querySelector('.hh-query-toolbar .hh-qt-summary')||{}).textContent||'')")
        if "已导出" in st or "失败" in st or "未捕获" in st:
            print("t+%02ds note:" % i, st[:120])
            break
        if i in (2, 5, 10, 20, 30):
            print("t+%02ds waiting…" % i)
    time.sleep(5)
    print("downloads:", os.listdir(dl))
    proc.terminate()
    time.sleep(1.5)
    proc.kill()


if __name__ == "__main__":
    main()
