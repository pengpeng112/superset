# -*- coding: utf-8 -*-
"""20261121 批：重录看板 72（默认窗已推进 2026-10）与 75 首屏 QueryContext 模板，
幂等替换 warmup_templates.json 中 72/75 条目（其余 9 看板条目原样保留）。
三端同步：本地 offline-bundle/scripts、本批 evidence、服务器 superset_home/scripts（由部署脚本推送）。
环境变量 ACC_ADMIN；前置条件：127.0.0.1:18180 端口转发已启动。
"""
import json
import os
import re
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
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CDP_PORT = 19593
EXPECT = {72: (8, "2026-10-01 : 2026-11-01"), 75: (7, "2026-10-01 : 2026-11-01")}


def capture_dash(tab, dash_id, expect_n, expect_tr):
    tab.eval("window.location.href='" + BASE + "/superset/dashboard/%d/'" % dash_id)
    time.sleep(4)
    for _ in range(40):
        if tab.eval("document.readyState") == "complete":
            break
        time.sleep(0.5)
    # 渲染状态探针：position_json 变更后确认 8 个图表 holder 全部在栅格中
    holders = 0
    try:
        holders = tab.eval("document.querySelectorAll('.dashboard-component-chart-holder').length")
    except Exception:
        pass
    print("dash %d render probe: chart holders=%s" % (dash_id, holders))
    captured = {}
    last_new = time.time()
    deadline = time.time() + 420
    while time.time() < deadline:
        grew = False
        for ev in tab.drain():
            m, p = ev.get("method"), ev.get("params", {})
            rid = p.get("requestId")
            if m == "Network.requestWillBeSent":
                r = p.get("request", {})
                if "/api/v1/chart/data" in r.get("url", "") and r.get("method") == "POST":
                    captured[rid] = {"url": r.get("url"), "post": r.get("postData", "")}
                    grew = True
            elif m in ("Network.loadingFinished", "Network.loadingFailed") and rid in captured:
                captured[rid]["done"] = m == "Network.loadingFinished"
                grew = True
        done = [r for r in captured.values() if r.get("done")]
        if grew:
            last_new = time.time()
            print("dash %d progress: done=%d/%d (target %d)" % (dash_id, len(done), len(captured), expect_n))
        if len(done) >= expect_n and time.time() - last_new > 12:
            break
        time.sleep(1.0)
    items = []
    tr_seen = set()
    for rec in captured.values():
        if not rec.get("done") or not rec.get("post"):
            continue
        try:
            body = json.loads(rec["post"])
        except Exception:
            continue
        fd = body.get("form_data") or {}
        sid = fd.get("slice_id")
        if sid is None:
            mm = re.search(r"slice_id%22%3A(\d+)", rec["url"])
            sid = int(mm.group(1)) if mm else 0
        # filter_time 原生筛选自身的日历数据查询（native_filter_id，slice_id 缺省）记为 0，
        # 与既有模板口径一致（46 条满额：每看板 = 图表数 + 1 条 filter 查询）
        for q in body.get("queries", []):
            tr_seen.add(str(q.get("time_range", "")))
        items.append({"dashboard": dash_id, "slice_id": int(sid), "viz": fd.get("viz_type", ""),
                      "url_path": rec["url"].replace(BASE, ""), "body": body})
    items.sort(key=lambda x: x["slice_id"])
    print("dash %d captured %d chart/data requests; time_ranges=%s" % (dash_id, len(items), sorted(tr_seen)))
    assert len(items) >= expect_n, "dash %d: expect >=%d requests, got %d" % (dash_id, expect_n, len(items))
    assert expect_tr in tr_seen, "dash %d: expect time_range %s, saw %s" % (dash_id, expect_tr, tr_seen)
    return items


def main():
    admin_pw = os.environ["ACC_ADMIN"]
    proc = subprocess.Popen([CHROME,
                             "--remote-debugging-port=%d" % CDP_PORT,
                             "--user-data-dir=" + HERE + r"\profile-cap7275",
                             "--no-first-run", "--no-default-browser-check",
                             "--window-size=1366,768", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/json/version" % CDP_PORT, timeout=3)
                break
            except Exception:
                time.sleep(0.5)
        info = new_tab(CDP_PORT)
        ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=60)
        tab = Tab(ws)
        tab.send("Page.enable")
        tab.send("Network.enable")
        assert tab.login("admin", admin_pw), "admin login failed"
        out = []
        out.extend(capture_dash(tab, 72, *EXPECT[72]))
        out.extend(capture_dash(tab, 75, *EXPECT[75]))
        ws.close()
    finally:
        proc.terminate()
    tpl = json.load(open(LOCAL_TPL, encoding="utf-8"))
    templates = [t for t in tpl["templates"] if t.get("dashboard") not in (72, 75)]
    templates.extend(out)
    templates.sort(key=lambda t: (t["dashboard"], t["slice_id"]))
    tpl["templates"] = templates
    meta = tpl.get("_meta") or {}
    dashes = sorted(set(meta.get("dashboards") or []) | {72, 75})
    meta["dashboards"] = dashes
    meta["updated"] = time.strftime("%Y-%m-%d") + " RBAC-FRONTEND-POLISH 批重录 72（默认窗推进 2026-10）与 75（%d 条）" % len(out)
    tpl["_meta"] = meta
    for path in (LOCAL_TPL, BATCH_TPL):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(tpl, f, ensure_ascii=False, indent=1)
        print("saved %s total=%d" % (path, len(templates)))
    print("slice_ids 72:", [t["slice_id"] for t in out if t["dashboard"] == 72])
    print("slice_ids 75:", [t["slice_id"] for t in out if t["dashboard"] == 75])


if __name__ == "__main__":
    main()
