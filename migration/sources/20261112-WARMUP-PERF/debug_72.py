# -*- coding: utf-8 -*-
"""一次性调试：打开看板 45，完整打印 chart/data 请求/响应抓取细节。"""
import json
import sys
import time

sys.path.insert(0, r"F:\python\superset\migration\sources\20261112-WARMUP-PERF")
from wb_run import Tab, NetTracker, launch, new_tab, PAGE_STATE  # noqa: E402
import websocket  # noqa: E402

port = 19310
proc, ver = launch(r"C:\Program Files\Google\Chrome\Application\chrome.exe", "dbg", port)
info = new_tab(port)
ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=30)
tab = Tab(ws)
tab.send("Page.enable")
tab.send("Network.enable", {"maxPostDataSize": 524288})
tr = NetTracker(tab)
tab.login("admin", "<REDACTED-SUPERSET-ADMIN-PW>")
tab.send("Page.navigate", {"url": "http://127.0.0.1:18180/superset/dashboard/72/"})
t0 = time.time()
while time.time() - t0 < 60:
    tab.eval("1+1")
    tr.poll()
    if tr.snapshot()["sent"] >= 1 and tr.snapshot()["inflight"] == 0 and tr.snapshot()["done"] == tr.snapshot()["sent"]:
        time.sleep(2)
        tab.eval("1+1")
        tr.poll()
        break
    time.sleep(1)
for rid, rec in tr.done.items():
    post = rec.get("post", "")
    print("=== rid", rid, "ms", rec.get("ms"), "failed", rec.get("failed"), "body_err", rec.get("body_err"))
    print("post_len", len(post))
    try:
        j = json.loads(post)
        print("post keys:", sorted(j.keys()))
        print("queries:", len(j.get("queries", [])), "result_format", j.get("result_format"), "force", j.get("force"))
        q0 = j.get("queries", [{}])[0]
        print("q0 keys:", sorted(q0.keys())[:20])
        print("slice_id(form_data):", (j.get("form_data") or {}).get("slice_id"))
        print("row_limit:", q0.get("row_limit"), "row_offset:", q0.get("row_offset"), "time_range:", str(q0.get("extras", {}).get("time_range"))[:60])
    except Exception as e:
        print("post parse err", e, post[:200])
    print("is_cached:", rec.get("is_cached"), "cache_key:", rec.get("cache_key"), "rowcount:", rec.get("rowcount"), "api_error:", rec.get("api_error"))
ws.close()
proc.terminate()
time.sleep(1)
proc.kill()
