# -*- coding: utf-8 -*-
"""观察探针：59 号页 设日期44天 → 选V1=1 → 监测 90s（POST/主线程），再开V2找99。"""
import sys
import time

sys.path.insert(0, r"F:\python\superset\migration\sources\20261112-WARMUP-PERF")
from wb_run import Tab, NetTracker, launch, new_tab  # noqa: E402
from guard_test import open_select, pick_option, SET_DATE  # noqa: E402
import websocket  # noqa: E402

port = 19314
proc, ver = launch(r"C:\Program Files\Google\Chrome\Application\chrome.exe", "frz", port)
info = new_tab(port)
ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=30)
tab = Tab(ws)
tab.send("Page.enable")
tab.send("Network.enable", {"maxPostDataSize": 65536})
tr = NetTracker(tab)
tab.login("admin", "<REDACTED-SUPERSET-ADMIN-PW>")


def responsive(what):
    t0 = time.time()
    try:
        tab.eval("1+1", )
        return "%s eval %dms" % (what, int((time.time() - t0) * 1000))
    except Exception as e:
        return "%s FROZE %s" % (what, repr(e)[:60])


tab.send("Page.navigate", {"url": "http://127.0.0.1:18180/superset/dashboard/59/"})
for _ in range(40):
    time.sleep(1)
    if (tab.eval("(document.querySelectorAll('.hdt-picker[data-filter-id]').length)||0") or 0):
        break
time.sleep(3)
print("page ready", flush=True)

print(tab.eval(SET_DATE % ("NATIVE_FILTER-P59-DATE", "2026-10-01", "2026-11-13")), flush=True)
time.sleep(1.5)
tr.poll()
print("after date posts:", tr.snapshot(), flush=True)

print("open V1:", open_select(tab, "NATIVE_FILTER-P59-V1"), flush=True)
time.sleep(1.2)
print("pick V1:", pick_option(tab, "1"), flush=True)
for i in range(18):
    time.sleep(5)
    try:
        tr.poll()
        snap = tr.snapshot()
        print("t+%02ds posts sent=%d done=%d inflight=%d | %s" % (
            (i + 1) * 5, snap["sent"], snap["done"], snap["inflight"], responsive("tick")), flush=True)
        for rid, rec in list(tr.done.items()):
            if rec.get("ms", 0) > 3000 or rec.get("hit") is False:
                print("   slow post: ms=%s key=%s rows=%s status=%s" % (
                    rec.get("ms"), rec.get("cache_key"), rec.get("rowcount"), rec.get("status")), flush=True)
    except Exception as e:
        print("t+%02ds poll err %s" % ((i + 1) * 5, repr(e)[:80]), flush=True)
ws.close()
proc.terminate()
time.sleep(1)
proc.kill()
