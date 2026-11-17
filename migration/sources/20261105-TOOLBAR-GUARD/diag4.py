# -*- coding: utf-8 -*-
"""诊断4：设置日期筛选（flatpickr 真实路径）→查询→原生导出，抓筛选态 payload 的 filter 展开形态。"""
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
    "(function(a,b){var inp=document.querySelector('.hdt-picker[data-mode=range] input');"
    "if(!inp||!inp._flatpickr)return 'no-picker';"
    "inp._flatpickr.setDate([a,b],true);return 'picked:'+a+'|'+b;})('%s','%s')"
)


def main():
    USERS.update({"admin": os.environ["ACC_ADMIN"]})
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9370
    proc, ver = launch("C:/Program Files/Google/Chrome/Application/chrome.exe", port,
                       os.path.abspath("profile-diag8"), 1600, 900)
    info = new_tab(port)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=40)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Runtime.enable")
    net_ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=40)
    captured = []

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
                    captured.append({"url": r["url"], "postData": r.get("postData", "")})

    threading.Thread(target=listen, daemon=True).start()
    ok, det = login(tab, "admin")
    print("login:", ok)
    tab.navigate(BASE + "/superset/dashboard/65/")
    tab.wait("!!document.querySelector('.hh-query-toolbar')", timeout=40)
    for i in range(40):
        s = tab.eval("((document.querySelector('.hh-query-toolbar .hh-qt-summary')||{}).textContent||'')")
        if "共返回" in s:
            break
        time.sleep(1)
    print("summary0:", s)
    print("pick:", tab.eval(PICK_JS % ("2026-09-16", "2026-09-16")))
    time.sleep(1.5)
    tab.eval("(function(){var b=document.querySelector('[data-test=\"filter-bar__apply-button\"]');if(b)b.click();return 1;})()")
    for i in range(40):
        s = tab.eval("((document.querySelector('.hh-query-toolbar .hh-qt-summary')||{}).textContent||'')")
        if "4,444" in s or ("共返回" in s and "23,641" not in s):
            break
        time.sleep(1)
    print("summary1:", s)
    time.sleep(2)
    # 原生菜单导出
    tab.eval("(function(){var b=document.querySelector('[data-test=\"slice-header\"] [data-test=\"actions-trigger\"]')||document.querySelector('[data-test=\"actions-trigger\"]');if(b)b.click();return 1;})()")
    time.sleep(1.5)
    clicked = tab.eval(
        "(function(){var els=[].slice.call(document.querySelectorAll('.ant-dropdown a, .ant-dropdown [role=menuitem], .ant-dropdown li, [class*=dropdown] a'));"
        "for(var i=0;i<els.length;i++){var t=(els[i].textContent||'').trim();"
        "if(/CSV|csv/.test(t)){els[i].click();return 'clicked:'+t;}}return 'not-found';})()"
    )
    print("click:", clicked)
    time.sleep(6)
    print("captured:", len(captured))
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "diag4-captured.json"), "w", encoding="utf-8") as f:
        json.dump(captured, f, ensure_ascii=False, indent=1)
    for c in captured:
        try:
            body = json.loads(c["postData"])
        except Exception:
            print("URL:", c["url"][:80], "RAW parse fail")
            continue
        is_export = body.get("result_format") in ("csv", "xlsx")
        qs = (body.get("queries") or [{}])[0]
        print("---", "EXPORT" if is_export else "query", "url_tail:", c["url"].split("18180")[1][:90])
        print("    result_format:", body.get("result_format"), "| datasource:", body.get("datasource"))
        print("    q.filters:", json.dumps(qs.get("filters"), ensure_ascii=False)[:400])
        print("    q.extras:", json.dumps(qs.get("extras"), ensure_ascii=False)[:300])
        print("    q.applied_time_extras:", json.dumps(qs.get("applied_time_extras"), ensure_ascii=False)[:300])
        print("    q.url_params:", json.dumps(qs.get("url_params"), ensure_ascii=False)[:200])
        print("    q.row_limit:", qs.get("row_limit"), "granularity:", qs.get("granularity"), "granularity_sqla:", qs.get("granularity_sqla"))
        fd = body.get("form_data") or {}
        print("    fd.url_params:", json.dumps(fd.get("url_params"), ensure_ascii=False)[:200])
        print("    fd.extra_form_data:", json.dumps(fd.get("extra_form_data"), ensure_ascii=False)[:400])
        print("    fd.extra_filters:", json.dumps(fd.get("extra_filters"), ensure_ascii=False)[:200])
        print("    fd.adhoc_filters:", json.dumps(fd.get("adhoc_filters"), ensure_ascii=False)[:300])
        print("    fd.time_range:", fd.get("time_range"))
    proc.terminate()
    time.sleep(1)
    proc.kill()


if __name__ == "__main__":
    main()
