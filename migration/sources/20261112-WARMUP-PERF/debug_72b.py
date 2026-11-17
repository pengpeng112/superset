# -*- coding: utf-8 -*-
"""深探针：看板 72 全程 60s 采集，完整转储所有 chart/data 请求体与响应体摘要。"""
import json
import sys
import time

sys.path.insert(0, r"F:\python\superset\migration\sources\20261112-WARMUP-PERF")
from wb_run import Tab, launch, new_tab  # noqa: E402
import websocket  # noqa: E402

DID = int(sys.argv[1]) if len(sys.argv) > 1 else 72
port = 19311
proc, ver = launch(r"C:\Program Files\Google\Chrome\Application\chrome.exe", "dbg2", port)
info = new_tab(port)
ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=30)
tab = Tab(ws)
tab.send("Page.enable")
tab.send("Network.enable", {"maxPostDataSize": 2097152})
pending, done = {}, {}
tab.login("admin", "<REDACTED-SUPERSET-ADMIN-PW>")
tab.send("Page.navigate", {"url": "http://127.0.0.1:18180/superset/dashboard/%d/" % DID})
t0 = time.time()
while time.time() - t0 < 60:
    tab.eval("1+1")
    for ev in tab.drain():
        m, p = ev["method"], ev.get("params", {})
        rid = p.get("requestId")
        if m == "Network.requestWillBeSent":
            r = p.get("request", {})
            u = r.get("url", "")
            if "/api/v1/chart/data" in u:
                pending[rid] = {"url": u, "post": r.get("postData", ""), "ts": time.time(), "method": r.get("method")}
        elif m in ("Network.loadingFinished", "Network.loadingFailed") and rid in pending:
            info2 = pending.pop(rid)
            info2["ms"] = int((time.time() - info2["ts"]) * 1000)
            info2["failed"] = m == "Network.loadingFailed"
            if not info2["failed"]:
                try:
                    b = tab.send("Network.getResponseBody", {"requestId": rid}, timeout=25)
                    txt = b.get("body", "")
                    if b.get("base64Encoded"):
                        import base64
                        txt = base64.b64decode(txt).decode("utf-8", "replace")
                    info2["resp_head"] = txt[:400]
                    try:
                        j = json.loads(txt)
                        r0 = (j.get("result") or [{}])[0]
                        info2["resp_keys"] = sorted(r0.keys())
                    except Exception as e:
                        info2["resp_parse_err"] = repr(e)[:100]
                except Exception as e:
                    info2["resp_err"] = repr(e)[:150]
            done[rid] = info2
    time.sleep(1)
print("captured", len(done), "chart/data posts")
for rid, d in done.items():
    print("=" * 70)
    print("url:", d["url"][-40:], "method:", d["method"], "ms:", d["ms"], "failed:", d["failed"], "post_len:", len(d["post"]))
    try:
        j = json.loads(d["post"])
        fd = j.get("form_data") or {}
        print("  slice_id:", fd.get("slice_id"), "| viz:", fd.get("viz_type"), "| datasource:", j.get("datasource"),
              "| queries:", len(j.get("queries", [])), "| result_type:", j.get("result_type"), "| force:", j.get("force"))
    except Exception as e:
        print("  post parse err:", e)
    if "resp_keys" in d:
        print("  resp result[0] keys:", d["resp_keys"])
    print("  resp_head:", (d.get("resp_head") or d.get("resp_err") or d.get("resp_parse_err") or "")[:300].replace("\n", " "))
ws.close()
proc.terminate()
time.sleep(1)
proc.kill()
