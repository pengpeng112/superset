# -*- coding: utf-8 -*-
"""诊断11（35页收口）：点击 CSV 后读服务器响应体与请求 payload 全文对照。"""
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
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9460
    which = sys.argv[2] if len(sys.argv) > 2 else "35"
    proc, ver = launch("C:/Program Files/Google/Chrome/Application/chrome.exe", port,
                       os.path.abspath("profile-diag15"), 1500, 950)
    info = new_tab(port)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=40)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Runtime.enable")
    ev_ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=40)
    pending, done = {}, []

    def listen():
        mid = 100
        ev_ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
        while True:
            try:
                raw = ev_ws.recv()
            except Exception:
                return
            try:
                m = json.loads(raw)
            except Exception:
                continue
            meth = m.get("method")
            if meth == "Network.requestWillBeSent":
                r = m["params"]["request"]
                if "/api/v1/chart/data" in r.get("url", "") and r.get("method") == "POST":
                    pending[m["params"]["requestId"]] = {"t": time.time(), "url": r["url"], "post": r.get("postData", "")}
            elif meth == "Network.loadingFinished":
                rid = m["params"]["requestId"]
                if rid in pending:
                    ev_ws.send(json.dumps({"id": mid, "method": "Network.getResponseBody", "params": {"requestId": rid}}))
                    mid += 1
                    pending[rid]["wait"] = True
            elif m.get("id") and m.get("result") and "body" in m.get("result", {}):
                for rid, p in list(pending.items()):
                    if p.get("wait") and "resp" not in p:
                        p["resp"] = m["result"]
                        done.append(rid)

    threading.Thread(target=listen, daemon=True).start()
    ok, det = login(tab, "admin")
    print("login:", ok)
    tab.navigate(BASE + "/superset/dashboard/%s/" % which)
    tab.wait("!!document.querySelector('.hh-query-toolbar')", timeout=60)
    for i in range(60):
        s = tab.eval("((document.querySelector('.hh-query-toolbar .hh-qt-summary')||{}).textContent||'')")
        if "共返回" in s:
            break
        time.sleep(1)
    print("summary:", s)
    time.sleep(2)
    done.clear()
    pending.clear()
    pos = tab.eval("(function(){var b=document.querySelector('button.hh-btn-csv');var r=b.getBoundingClientRect();return JSON.stringify({x:r.left+r.width/2,y:r.top+r.height/2});})()")
    p = json.loads(pos)
    for typ in ("mousePressed", "mouseReleased"):
        tab.send("Input.dispatchMouseEvent", {"type": typ, "x": p["x"], "y": p["y"], "button": "left", "clickCount": 1})
    time.sleep(15)
    for rid in done:
        d = pending[rid]
        body = d.get("post", "")
        try:
            b = json.loads(body)
            fmt_top = b.get("result_format")
            fmt_fd = (b.get("form_data") or {}).get("result_format")
            q0 = (b.get("queries") or [{}])[0]
            print("REQ nq=%d %s | top.result_format=%s form_data.result_format=%s | q.row_limit=%s filters=%s url_params=%s" % (
                len(b.get("queries") or []), "EXPORT?" if fmt_top in ("csv", "xlsx") else "query", fmt_top, fmt_fd, q0.get("row_limit"),
                json.dumps(q0.get("filters"))[:80], json.dumps(q0.get("url_params"))[:80]))
        except Exception as e:
            print("REQ parse err", e)
        resp = d.get("resp", {})
        rb = resp.get("body", "") or ""
        print("   RESP base64=%s len=%s head=%r" % (resp.get("base64Encoded"), len(rb), rb[:60]))
    proc.terminate()
    time.sleep(1.5)
    proc.kill()


if __name__ == "__main__":
    main()
