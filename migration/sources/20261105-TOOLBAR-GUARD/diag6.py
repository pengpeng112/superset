# -*- coding: utf-8 -*-
"""诊断6：a) 61页筛选后图表查询payload的filters；b) console错误收集；c) CDP真实手势点击导出。"""
import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from acc2_run import Tab, login, launch, new_tab, USERS  # noqa

import websocket

BASE = "http://127.0.0.1:18180"

PICK_JS = (
    "(function(a,b){var ps=document.querySelectorAll('.hdt-picker input');"
    "for(var i=0;i<ps.length;i++){if(ps[i]._flatpickr){ps[i]._flatpickr.setDate([a,b],true);return 'picked:'+a+':'+b;}}"
    "return 'no-picker:'+ps.length;})('%s','%s')"
)


def main():
    USERS.update({"admin": os.environ["ACC_ADMIN"]})
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9400
    which = sys.argv[2] if len(sys.argv) > 2 else "61"
    proc, ver = launch("C:/Program Files/Google/Chrome/Application/chrome.exe", port,
                       os.path.abspath("profile-diag10"), 1500, 950)
    info = new_tab(port)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=40)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Runtime.enable")
    ev_ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=40)
    captured, logs = [], []

    def listen():
        ev_ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
        ev_ws.send(json.dumps({"id": 2, "method": "Log.enable"}))
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
                    captured.append({"t": time.time(), "url": r["url"][:120], "postData": r.get("postData", "")})
            elif m == "Runtime.consoleAPICalled":
                logs.append(("console", msg["params"].get("type"), " ".join(str(a.get("value", "")) for a in msg["params"].get("args", []))[:200]))
            elif m == "Runtime.exceptionThrown":
                logs.append(("exception", "", json.dumps(msg["params"].get("exceptionDetails", {}))[:300]))
            elif m == "Log.entryAdded":
                e = msg["params"]["entry"]
                logs.append(("log", e.get("level"), e.get("text", "")[:200]))

    threading.Thread(target=listen, daemon=True).start()
    ok, det = login(tab, "admin")
    print("login:", ok)
    tab.navigate(BASE + "/superset/dashboard/%s/" % which)
    tab.wait("!!document.querySelector('.hh-query-toolbar')", timeout=60)
    tab.wait("document.querySelectorAll('.hdt-picker input').length>=1", timeout=60)
    for i in range(120):
        s = tab.eval("((document.querySelector('.hh-query-toolbar .hh-qt-summary')||{}).textContent||'')")
        if "共返回" in s:
            break
        time.sleep(1)
    print("summary0:", s)
    captured.clear()
    print("pick:", tab.eval(PICK_JS % ("2026-09-01", "2026-09-07")))
    time.sleep(1.5)
    tab.eval("(function(){var b=document.querySelector('[data-test=\"filter-bar__apply-button\"]');if(b)b.click();return 1;})()")
    for i in range(90):
        s = tab.eval("((document.querySelector('.hh-query-toolbar .hh-qt-summary')||{}).textContent||'')")
        if "耗时" in s and "正在查询" not in s:
            break
        time.sleep(1)
    time.sleep(2)
    print("summary1:", s)
    for c in captured:
        try:
            b = json.loads(c["postData"])
        except Exception:
            continue
        if b.get("form_data", {}).get("slice_id") and b.get("result_format") in (None, "json"):
            q = (b.get("queries") or [{}])[0]
            print("CHART QUERY: filters=", json.dumps(q.get("filters"), ensure_ascii=False)[:500])
            print("            extras=", json.dumps(q.get("extras"), ensure_ascii=False)[:200], "| row_limit=", q.get("row_limit"))
            print("            fd.extra_form_data=", json.dumps(b["form_data"].get("extra_form_data"), ensure_ascii=False)[:300])
            print("            fd.time_range=", b["form_data"].get("time_range"))
    # 真实手势点击导出（CDP Input.dispatchMouseEvent）
    def real_click(selector):
        r = tab.eval(
            "(function(){var b=document.querySelector('%s');if(!b)return '';var r=b.getBoundingClientRect();"
            "return JSON.stringify({x:r.left+r.width/2,y:r.top+r.height/2});})()" % selector)
        if not r:
            return "missing"
        p = json.loads(r)
        for typ in ("mousePressed", "mouseReleased"):
            tab.send("Input.dispatchMouseEvent", {"type": typ, "x": p["x"], "y": p["y"], "button": "left", "clickCount": 1})
        return "clicked@%.0f,%.0f" % (p["x"], p["y"])

    print("real click xlsx:", real_click("button.hh-btn-xlsx"))
    for i in range(20):
        time.sleep(1)
        s = tab.eval("((document.querySelector('.hh-query-toolbar .hh-qt-summary')||{}).textContent||'')")
        if "已导出" in s or "失败" in s or "未捕获" in s:
            break
    print("note after xlsx:", s)
    dl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
    os.makedirs(dl, exist_ok=True)
    print("downloads:", os.listdir(dl))
    print("--- console/logs (errors) ---")
    for kind, lvl, text in logs[-25:]:
        if lvl in ("error", "warning") or kind in ("exception",):
            print(kind, lvl, text)
    proc.terminate()
    time.sleep(1.5)
    proc.kill()


if __name__ == "__main__":
    main()
