# -*- coding: utf-8 -*-
"""诊断3：抓取原生「更多操作」菜单 CSV 导出的真实 /api/v1/chart/data 请求 payload。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from acc2_run import Tab, login, launch, new_tab, USERS  # noqa

import websocket

BASE = "http://127.0.0.1:18180"


def main():
    USERS.update({"admin": os.environ["ACC_ADMIN"]})
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9360
    proc, ver = launch("C:/Program Files/Google/Chrome/Application/chrome.exe", port,
                       os.path.abspath("profile-diag7"), 1600, 900)
    info = new_tab(port)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=40)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Runtime.enable")
    net_ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=40)
    captured = []
    import threading

    def listen():
        net_ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
        while True:
            try:
                raw = net_ws.recv()
            except Exception:
                return
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            if msg.get("method") == "Network.requestWillBeSent":
                r = msg["params"]["request"]
                if "/api/v1/chart/data" in r.get("url", ""):
                    captured.append({"url": r["url"], "method": r["method"], "postData": r.get("postData", "")[:4000]})

    th = threading.Thread(target=listen, daemon=True)
    th.start()
    ok, det = login(tab, "admin")
    print("login:", ok)
    tab.navigate(BASE + "/superset/dashboard/65/")
    tab.wait("!!document.querySelector('.hh-query-toolbar')", timeout=40)
    for i in range(40):
        s = tab.eval("((document.querySelector('.hh-query-toolbar .hh-qt-summary')||{}).textContent||'')")
        if "共返回" in s:
            break
        time.sleep(1)
    print("summary:", s)
    # 打开 slice header 的更多操作菜单
    r = tab.eval(
        "(function(){var b=document.querySelector('[data-test=\"slice-header\"] [data-test=\"actions-trigger\"]')"
        "||document.querySelector('[data-test=\"actions-trigger\"]');if(!b)return 'no-trigger';b.click();return 'opened';})()"
    )
    print("menu open:", r)
    time.sleep(1.5)
    items = tab.eval(
        "JSON.stringify([].map.call(document.querySelectorAll('.ant-dropdown a, .ant-dropdown [role=menuitem], .ant-dropdown li, [class*=dropdown] a'),function(n){return (n.textContent||'').trim();}).filter(Boolean))"
    )
    print("menu items:", items[:500])
    # 点击含 CSV/下载 的项
    clicked = tab.eval(
        "(function(){var els=[].slice.call(document.querySelectorAll('.ant-dropdown a, .ant-dropdown [role=menuitem], .ant-dropdown li, [class*=dropdown] a'));"
        "for(var i=0;i<els.length;i++){var t=(els[i].textContent||'').trim();"
        "if(/CSV|csv|下载|导出/.test(t)){els[i].click();return 'clicked:'+t;}}return 'not-found';})()"
    )
    print("click:", clicked)
    time.sleep(6)
    print("captured %d requests:" % len(captured))
    for c in captured:
        print("URL:", c["url"], c["method"])
        try:
            body = json.loads(c["postData"])
            print("PAYLOAD KEYS:", sorted(body.keys()))
            print("PAYLOAD:", json.dumps(body, ensure_ascii=False)[:2500])
        except Exception:
            print("RAW:", c["postData"][:1500])
    proc.terminate()
    time.sleep(1)
    proc.kill()


if __name__ == "__main__":
    main()
