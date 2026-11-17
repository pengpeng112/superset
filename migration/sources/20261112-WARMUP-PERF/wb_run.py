# -*- coding: utf-8 -*-
"""20261112-WARMUP-PERF：预热前后基准测速（bench）与 chart/data QueryContext 模板采集（capture）。

bench：冷态（Redis db1 已清）与热态（run_warmup.sh 已跑）各测一轮，记录每看板
  首屏完整出数耗时 + 每个 /api/v1/chart/data 响应的 is_cached / cache_key / 耗时。
capture：打开目标看板首屏，逐条抄录浏览器真实发出的 /api/v1/chart/data 请求体
  （QueryContext JSON 模板，供热引擎每日原样重放，Cache Key 100% 命中）。

用法：
  ACC_ADMIN=<口令> python -X utf8 wb_run.py --mode bench --phase cold --tag chrome --exe <chrome.exe> --port 19300
  ACC_ADMIN=<口令> python -X utf8 wb_run.py --mode capture --tag chrome --exe <chrome.exe> --port 19301
"""
import argparse
import base64
import json
import os
import subprocess
import time
import urllib.request

import websocket

BASE = os.environ.get("ACC_BASE", "http://127.0.0.1:18180")
HERE = os.path.dirname(os.path.abspath(__file__))

BENCH_IDS = [72, 73, 74, 32, 45, 63]
CAPTURE_IDS = [72, 73, 74, 32, 35, 41, 45, 46, 60, 63]
# 首屏图表数（生产元库 sweep_meta.tsv 2026-11-08 核对）
SLICE_COUNT = {72: 8, 73: 7, 74: 6, 32: 2, 35: 1, 41: 1, 45: 1, 46: 1, 60: 1, 63: 1, 39: 1}
DATA_WAIT = {63: 150, 39: 150}   # 63 冷查 47s+；39 四路 UNION 兜底窗 7 天
DEFAULT_WAIT = 75

PAGE_STATE = """(function(){
  var md=document.querySelector('.dashboard-markdown');
  var table=document.querySelector('.superset-chart-table');
  var mr=document.getElementById('hospital-monthly-report');
  var holders=document.querySelectorAll('.dashboard-component-chart-holder').length;
  var rendered=[].slice.call(document.querySelectorAll('.dashboard-component-chart-holder'))
    .filter(function(h){return h.querySelector('svg,canvas,table,.ant-empty')}).length;
  var err=document.querySelector('.error-page-content');
  var sum=(document.querySelector('.hh-qt-summary')||{}).textContent||'';
  return JSON.stringify({md:!!md,table:!!table,mr:!!mr,holders:holders,rendered:rendered,
    err:!!err,sum:sum.slice(0,60),
    rows:(function(){var t=document.querySelector('.superset-chart-table tbody');return t?t.rows.length:0})()});
})()"""


def http_json(url, method="GET"):
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def new_tab(port):
    for method in ("PUT", "GET"):
        try:
            req = urllib.request.Request("http://127.0.0.1:%d/json/new?about:blank" % port, method=method)
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            continue
    for t in http_json("http://127.0.0.1:%d/json" % port):
        if t.get("type") == "page":
            return t
    raise RuntimeError("no tab")


class Tab:
    """CDP 标签页：send 按 id 收响应；其余消息（Network 事件）压入 self.events。"""

    def __init__(self, ws):
        self.ws = ws
        self.mid = 0
        self.events = []

    def send(self, method, params=None, timeout=60):
        self.mid += 1
        mid = self.mid
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.ws.settimeout(max(0.5, deadline - time.time()))
            try:
                raw = self.ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            msg = json.loads(raw)
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError("%s: %s" % (method, msg["error"]))
                return msg.get("result", {})
            if "method" in msg:
                self.events.append(msg)
        raise TimeoutError(method)

    def drain(self):
        ev, self.events = self.events, []
        return ev

    def eval(self, expr):
        r = self.send("Runtime.evaluate", {"expression": expr, "returnByValue": True})
        if r.get("exceptionDetails"):
            d = r["exceptionDetails"]
            desc = ""
            try:
                desc = (d.get("exception") or {}).get("description", "")[:200]
            except Exception:
                pass
            raise RuntimeError("eval error: %s %s | expr=%s" % (d.get("text"), desc, expr[:100]))
        return r["result"].get("value")

    def login(self, user, pw):
        self.send("Page.navigate", {"url": BASE + "/login/"})
        time.sleep(2.5)
        for _ in range(30):
            if self.eval("document.readyState") == "complete":
                break
            time.sleep(0.5)
        found = False
        for _ in range(15):
            if self.eval("!!document.querySelector('input[id=\"username\"]')"):
                found = True
                break
            time.sleep(1.0)
        if not found:
            # profile 已带会话：/login/ 被重定向走，视为已登录
            return "/login" not in (self.eval("location.pathname") or "")
        self.eval(
            "(function(){var u=document.querySelector('input[id=\"username\"]');var p=document.querySelector('input[id=\"password\"]');"
            "var f=u.closest('form');var set=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
            "set.call(u,'%s');u.dispatchEvent(new Event('input',{bubbles:true}));"
            "set.call(p,'%s');p.dispatchEvent(new Event('input',{bubbles:true}));f.requestSubmit();return 1;})()" % (user, pw))
        for _ in range(30):
            time.sleep(1)
            if "/login" not in (self.eval("location.pathname") or ""):
                return True
        return False


class NetTracker:
    """抽取 /api/v1/chart/data 请求/响应：done[rid] = {url,post,ms,hit,...}。

    注意：看板图表请求 URL 带 ?form_data=…&dashboard_id=N 查询串（服务端
    get_form_data 会合并 args 里的 form_data），采集与重放都必须原样保留完整 URL。
    冷响应不含 is_cached 字段（true 才代表命中，false/缺省=未命中）。
    """

    def __init__(self, tab):
        self.tab = tab
        self.pending = {}   # rid -> {post, ts}
        self.done = {}

    def reset(self):
        self.pending, self.done = {}, {}

    def poll(self):
        for ev in self.tab.drain():
            m, p = ev["method"], ev.get("params", {})
            rid = p.get("requestId")
            if m == "Network.requestWillBeSent":
                r = p.get("request", {})
                if "/api/v1/chart/data" in r.get("url", "") and r.get("method") == "POST":
                    self.pending[rid] = {"url": r.get("url"), "post": r.get("postData", ""), "ts": time.time()}
            elif m in ("Network.loadingFinished", "Network.loadingFailed") and rid in self.pending:
                self._finish(rid, failed=(m == "Network.loadingFailed"))

    def _finish(self, rid, failed=False):
        info = self.pending.pop(rid)
        rec = {"url": info["url"], "post": info["post"], "ms": int((time.time() - info["ts"]) * 1000),
               "failed": failed, "hit": None}
        if not failed:
            try:
                body = self.tab.send("Network.getResponseBody", {"requestId": rid}, timeout=25)
                txt = body.get("body", "")
                if body.get("base64Encoded"):
                    txt = base64.b64decode(txt).decode("utf-8", "replace")
                j = json.loads(txt)
                results = j.get("result") or [{}]
                rec["hit"] = bool(results[0].get("is_cached"))
                rec["is_cached_raw"] = results[0].get("is_cached", "<absent>")
                rec["cache_key"] = (results[0].get("cache_key") or "")[:16]
                rec["cache_timeout"] = results[0].get("cache_timeout")
                rec["rowcount"] = results[0].get("rowcount")
                rec["status"] = results[0].get("status")
                rec["n_results"] = len(results)
                err0 = (j.get("errors") or [{}])[0]
                rec["api_error"] = (err0.get("error") or err0.get("message") or "")[:100] or None
            except Exception as e:
                rec["body_err"] = repr(e)[:90]
        self.done[rid] = rec

    def snapshot(self):
        return {"sent": len(self.done) + len(self.pending), "done": len(self.done),
                "inflight": len(self.pending)}

    def hits(self):
        """命中数/可判定数：仅统计拿到响应体的请求。"""
        judged = [d for d in self.done.values() if d.get("hit") is not None or d.get("failed")]
        return sum(1 for d in judged if d.get("hit")), len(judged)


def settle(tab, tracker, did, want):
    """导航后轮询到首屏完整出数：DOM 出内容 + chart/data 静默（无在途且已收 want 个）。

    want=看板图表数；实际 POST 数通常为 want+1（多一个 filter_time 附加查询），
    静默判定用 sent>=want 且连续 3 拍无新请求、无在途，避免把后续串行请求漏算。
    """
    t0 = time.time()
    tab.send("Page.navigate", {"url": BASE + "/superset/dashboard/%d/" % did})
    time.sleep(2.0)
    for _ in range(60):
        if tab.eval("document.readyState") == "complete":
            break
        time.sleep(0.5)
    first_dom = None
    quiet = 0
    deadline = time.time() + DATA_WAIT.get(did, DEFAULT_WAIT)
    st = {}
    while time.time() < deadline:
        st = json.loads(tab.eval(PAGE_STATE))
        tracker.poll()
        if first_dom is None and (st["mr"] or st["table"] or st["rendered"] or st["md"] or st["err"]):
            first_dom = int((time.time() - t0) * 1000)
        snap = tracker.snapshot()
        dom_ok = bool(st["mr"] or st["table"] or (want and st["rendered"] >= want) or st["err"])
        if dom_ok and first_dom is not None and snap["sent"] >= max(1, want) and snap["inflight"] == 0:
            quiet += 1
            if quiet >= 3:
                st = json.loads(tab.eval(PAGE_STATE))
                break
        else:
            quiet = 0
        time.sleep(1.0)
    return first_dom, int((time.time() - t0) * 1000), st


def launch(exe, tag, port):
    profile = os.path.abspath(os.path.join(HERE, "profile-wb-%s" % tag))
    proc = subprocess.Popen([
        exe, "--remote-debugging-port=%d" % port, "--user-data-dir=%s" % profile,
        "--no-first-run", "--no-default-browser-check", "--disable-session-crashed-bubble",
        "--window-size=1920,1080", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ver = ""
    for _ in range(60):
        try:
            ver = http_json("http://127.0.0.1:%d/json/version" % port).get("Browser", "")
            if ver:
                break
        except Exception:
            time.sleep(0.5)
    return proc, ver


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["bench", "capture"], required=True)
    ap.add_argument("--phase", default="", help="bench: cold|hot（写入结果文件名）")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--exe", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--ids", default="")
    ap.add_argument("--admin", default=os.environ.get("ACC_ADMIN", ""))
    args = ap.parse_args()
    ids = [int(x) for x in args.ids.split(",")] if args.ids else (BENCH_IDS if args.mode == "bench" else CAPTURE_IDS)

    proc, ver = launch(args.exe, args.tag, args.port)
    info = new_tab(args.port)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=30)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Network.enable", {"maxPostDataSize": 524288})
    tracker = NetTracker(tab)
    ok = tab.login("admin", args.admin)
    print("[%s] %s %s mode=%s phase=%s login=%s ids=%s" % (
        time.strftime("%H:%M:%S"), args.tag, ver, args.mode, args.phase, ok, ids), flush=True)

    rows, templates = [], []
    try:
        for did in ids:
            tracker.reset()
            want = SLICE_COUNT.get(did, 1)
            try:
                first_ms, full_ms, st = settle(tab, tracker, did, want)
                recs = list(tracker.done.values())
                hits_n, judged_n = tracker.hits()
                slowest = max([r["ms"] for r in recs] or [0])
                chart_keys = [r.get("cache_key") for r in recs]
                rows.append({"id": did, "first_dom_ms": first_ms, "full_ms": full_ms,
                             "posts": len(recs), "hits": hits_n, "judged": judged_n,
                             "slowest_req_ms": slowest,
                             "rendered": st.get("rendered", 0), "mr": st.get("mr", False),
                             "table": st.get("table", False), "rows": st.get("rows", 0),
                             "err": st.get("err", False), "sum": st.get("sum", ""),
                             "statuses": sorted({str(r.get("status")) for r in recs}),
                             "api_errors": [r.get("api_error") for r in recs if r.get("api_error")]})
                print("%s %3d full=%6dms first_dom=%6dms posts=%d hit=%d/%d slowest=%dms %s %s" % (
                    time.strftime("%H:%M:%S"), did, full_ms, first_ms or -1, len(recs), hits_n,
                    judged_n, slowest,
                    "MR" if st.get("mr") else ("TABLE rows=%d" % st.get("rows", 0) if st.get("table") else "rendered=%d" % st.get("rendered", 0)),
                    st.get("sum", "")[:40]), flush=True)
                if args.mode == "capture":
                    for r in recs:
                        try:
                            body = json.loads(r["post"])
                        except Exception:
                            continue
                        fd = body.get("form_data") or {}
                        sid = fd.get("slice_id") or 0
                        templates.append({"dashboard": did, "slice_id": sid, "viz": fd.get("viz_type"),
                                          "url_path": r["url"].split("18180", 1)[-1],
                                          "body": body,
                                          "ms_at_capture": r["ms"], "hit_at_capture": r.get("hit"),
                                          "cache_key16": r.get("cache_key", ""),
                                          "cache_timeout": r.get("cache_timeout")})
            except Exception as e:
                rows.append({"id": did, "error": repr(e)[:150]})
                print("%s %3d ERROR %s" % (time.strftime("%H:%M:%S"), did, repr(e)[:150]), flush=True)
            time.sleep(2.0)
    finally:
        ws.close()
        proc.terminate()
        time.sleep(1.5)
        proc.kill()

    if args.mode == "bench":
        out = os.path.join(HERE, "bench-%s-%s.json" % (args.tag, args.phase))
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"browser": ver, "phase": args.phase, "rows": rows}, f, ensure_ascii=False, indent=1)
    else:
        out = os.path.join(HERE, "templates-%s.json" % args.tag)
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"browser": ver, "templates": templates}, f, ensure_ascii=False, indent=1)
    print("saved", out, flush=True)


if __name__ == "__main__":
    main()
