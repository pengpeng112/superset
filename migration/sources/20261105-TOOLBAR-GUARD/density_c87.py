# -*- coding: utf-8 -*-
"""C87 density 单项复测（等 td 渲染后量行高）。"""
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
    port = int(sys.argv[1])
    exe = sys.argv[2]
    tag = sys.argv[3]
    w, h = int(sys.argv[4]), int(sys.argv[5])
    proc, ver = launch(exe, port, os.path.abspath("profile-density-%s" % tag), w, h)
    info = new_tab(port)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=40)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Runtime.enable")
    ok, _ = login(tab, "admin")
    print("login:", ok)
    tab.navigate(BASE + "/superset/dashboard/65/")
    tab.wait("!!document.querySelector('.hh-query-toolbar')", timeout=60)
    for i in range(150):
        s = tab.eval("((document.querySelector('.hh-query-toolbar .hh-qt-summary')||{}).textContent||'')")
        if "共返回" in s:
            break
        time.sleep(1)
    got = tab.wait("!!document.querySelector('.superset-chart-table tbody td')", timeout=120)
    print("td ready:", got, "| summary:", s[:60])
    r = tab.eval(
        "(function(){var b=document.querySelector('.hh-btn-density');if(!b)return 'missing';"
        "var h0=document.documentElement.classList.contains('hh-density-compact');b.click();"
        "var h1=document.documentElement.classList.contains('hh-density-compact');"
        "var ss=sessionStorage.getItem('hhTableDensity');"
        "var td=document.querySelector('.superset-chart-table td');"
        "var hh=td?Math.round(td.getBoundingClientRect().height):-1;"
        "b.click();var h2=document.documentElement.classList.contains('hh-density-compact');"
        "var ss2=sessionStorage.getItem('hhTableDensity');"
        "var td2=document.querySelector('.superset-chart-table td');"
        "var hh2=td2?Math.round(td2.getBoundingClientRect().height):-1;"
        "return JSON.stringify({h0:h0,h1:h1,ss:ss,hh:hh,h2:h2,ss2:ss2,hh2:hh2});})()"
    )
    d = json.loads(r or "{}")
    ok = (not d.get("h0")) and d.get("h1") and d.get("ss") == "compact" and 26 <= d.get("hh", 0) <= 44 \
         and (not d.get("h2")) and d.get("ss2") == "standard" and d.get("hh2", 0) > d.get("hh", 0)
    print("DENSITY %s %s: %s | compact=%s standard=%s" % (
        tag, "PASS" if ok else "FAIL", json.dumps(d), d.get("hh"), d.get("hh2")))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "density-c87-%s.json" % tag)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"tag": tag, "ok": ok, "data": d}, f, ensure_ascii=False)
    proc.terminate()
    time.sleep(1.5)
    proc.kill()


if __name__ == "__main__":
    main()
