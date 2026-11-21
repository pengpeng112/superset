# -*- coding: utf-8 -*-
"""录制看板 75 首屏全部 /api/v1/chart/data 请求（QueryContext 模板），追加合并 warmup_templates.json。
同步更新：生产 /home/superset/superset_home/scripts/warmup_templates.json、本地 offline-bundle/scripts/。
凭据环境变量 ACC_ADMIN。仅读浏览器网络事件 + 写模板文件（脚本经生产实跑 run_warmup.sh 验证）。
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

import websocket

sys.path.insert(0, r"F:\python\superset\migration\sources\20261112-WARMUP-PERF")
from wb_run import Tab, new_tab  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "http://127.0.0.1:18180"

LOCAL_TPL = r"F:\python\superset\offline-bundle\scripts\warmup_templates.json"
BATCH_TPL = os.path.join(HERE, "evidence", "warmup_templates.json")


def main():
    admin_pw = os.environ["ACC_ADMIN"]
    proc = subprocess.Popen([r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                             "--remote-debugging-port=19590",
                             "--user-data-dir=" + HERE + r"\profile-capture75",
                             "--no-first-run", "--no-default-browser-check",
                             "--window-size=1366,768", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        try:
            urllib.request.urlopen("http://127.0.0.1:19590/json/version", timeout=3)
            break
        except Exception:
            time.sleep(0.5)
    info = new_tab(19590)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=60)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Network.enable")
    login_ok = tab.login("admin", admin_pw)
    assert login_ok, "admin login failed"
    tab.send("Page.navigate", {"url": BASE + "/superset/dashboard/75/"})
    time.sleep(4)
    for _ in range(40):
        if tab.eval("document.readyState") == "complete":
            break
        time.sleep(0.5)
    # 等图表请求全部完成（75 号 7 图，饼图 ~3s）
    captured = {}
    deadline = time.time() + 90
    while time.time() < deadline:
        for ev in tab.drain():
            m, p = ev.get("method"), ev.get("params", {})
            rid = p.get("requestId")
            if m == "Network.requestWillBeSent":
                r = p.get("request", {})
                if "/api/v1/chart/data" in r.get("url", "") and r.get("method") == "POST":
                    captured[rid] = {"url": r.get("url"), "post": r.get("postData", "")}
            elif m in ("Network.loadingFinished", "Network.loadingFailed") and rid in captured:
                rec = captured[rid]
                rec["done"] = m == "Network.loadingFinished"
        done = [r for r in captured.values() if r.get("done")]
        if len(done) >= 7 and time.time() > deadline - 60:
            # 稳定窗口：全部完成后再等 3s 确认无新增
            time.sleep(3)
            if len([r for r in captured.values() if r.get("done")]) == len(done):
                break
        time.sleep(0.5)
    ws.close()
    proc.terminate()
    items = []
    for rid, rec in captured.items():
        if not rec.get("done") or not rec.get("post"):
            continue
        try:
            body = json.loads(rec["post"])
        except Exception:
            continue
        sid = None
        try:
            fd = body.get("form_data") or {}
            sid = fd.get("slice_id")
        except Exception:
            pass
        if not sid:
            import re
            m = re.search(r"slice_id%22%3A(\d+)", rec["url"])
            sid = int(m.group(1)) if m else 0
        if not sid:
            continue
        items.append({"dashboard": 75, "slice_id": int(sid), "viz": (body.get("form_data") or {}).get("viz_type", ""),
                      "url_path": rec["url"].replace(BASE, ""), "body": body})
    items.sort(key=lambda x: x["slice_id"])
    print("captured %d chart/data requests for dash 75" % len(items))
    assert len(items) >= 7, "expect >=7 chart/data requests, got %d" % len(items)

    tpl = json.load(open(LOCAL_TPL, encoding="utf-8"))
    templates = tpl["templates"]
    # 幂等：去掉已存在的 75 项再追加
    templates = [t for t in templates if t.get("dashboard") != 75]
    templates.extend(items)
    tpl["templates"] = templates
    meta = tpl.get("_meta") or (tpl.get("meta") or {})
    dashes = set(meta.get("dashboards") or [])
    dashes.add(75)
    meta["dashboards"] = sorted(dashes)
    meta["updated"] = time.strftime("%Y-%m-%d") + " BI-ENHANCE 批补看板 75（%d 条）" % len(items)
    tpl["_meta"] = meta
    for path in (LOCAL_TPL, BATCH_TPL):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(tpl, f, ensure_ascii=False, indent=1)
        print("saved", path, "total templates=%d" % len(templates))
    print("slice_ids:", [t["slice_id"] for t in items])


if __name__ == "__main__":
    main()
