# -*- coding: utf-8 -*-
"""20261108-FINAL-CLOSEOUT 任务3：全量看板双浏览器终验探针（admin 视角）。
覆盖：总目录34 + 8分类目录(25-31,33) + 病案1-2 + 27主报表(32,35-60) + 抗菌办61-70 + BI驾驶舱72-74 = 51 页。
每页记录：渲染状态、首屏耗时(ms)、日历控件、工具条。结果 sweep-<tag>.json；CSV 由 build_final_csv.py 合成。"""
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
SHOT_DIR = os.path.join(HERE, "shots")
os.makedirs(SHOT_DIR, exist_ok=True)

CATALOG_IDS = {25, 26, 27, 28, 29, 30, 31, 33, 34}
QUERY_IDS = set([2] + list(range(35, 61)))  # 2 + 35-60（32 月报单独判）
KYB_IDS = set(range(61, 71))
BI_IDS = {72, 73, 74}
# 必选条件页（20261106-CHINESE-TABLEUI 批登记）：首开不自动出表，需先选科室/门诊住院/就诊次数再查询——
# 首开无表格+无错误 = 设计行为，非缺陷。
REQUIRED_FILTER_IDS = {51, 52, 58, 59}
ALL_IDS = [34, 25, 26, 27, 28, 29, 30, 31, 33, 1, 2, 32] + list(range(35, 61)) + list(range(61, 71)) + [72, 73, 74]
assert len(ALL_IDS) == 51, len(ALL_IDS)

SLICE_COUNT = {}  # id -> expected chart count（从 sweep_meta.tsv 预填）


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
    def __init__(self, ws):
        self.ws = ws
        self.mid = 0

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
        raise TimeoutError(method)

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
        for _ in range(30):
            if self.eval("!!document.querySelector('input[id=\"username\"]')"):
                break
            time.sleep(1.0)
        else:
            # profile 已带会话：/login/ 被重定向走，视为已登录（20261115 补）
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


PAGE_STATE = """(function(){
  var g=document.querySelector('[data-test="grid-content"]');
  var md=document.querySelector('.dashboard-markdown');
  var mdLinks=md?md.querySelectorAll('a[href*="/superset/dashboard/"]').length:0;
  var table=document.querySelector('.superset-chart-table');
  /* 20261115：pivot_table_v2 等图表类型不渲染 .superset-chart-table，补 holder 内任意表格检测（39 号透视表） */
  var htable=document.querySelector('.dashboard-component-chart-holder table');
  var mr=document.getElementById('hospital-monthly-report');
  var holders=document.querySelectorAll('.dashboard-component-chart-holder').length;
  var rendered=[].slice.call(document.querySelectorAll('.dashboard-component-chart-holder'))
    .filter(function(h){return h.querySelector('svg,canvas,table,.ant-empty')}).length;
  var cal=document.querySelectorAll('.hdt-picker[data-filter-id]').length;
  var tb=document.querySelectorAll('.hh-query-toolbar').length;
  var err=document.querySelector('.error-page-content');
  var sum=(document.querySelector('.hh-qt-summary')||{}).textContent||'';
  var tEl=table||htable;
  return JSON.stringify({grid:!!g,md:!!md,mdLinks:mdLinks,table:!!table,tableAny:!!(table||htable),
    tableRows:(function(){var t=(table||htable);if(!t)return 0;var b=t.tagName==='TABLE'?t.querySelector('tbody'):null;return b?b.rows.length:0})(),
    mr:!!mr,holders:holders,rendered:rendered,cal:cal,tb:tb,
    err:!!err,errHidden:err?getComputedStyle(err).display==='none':null,
    deniedCard:!!document.getElementById('hh-denied-card'),sum:sum.slice(0,60)});
})()"""


def probe_page(tab, did, wait_scale=1.0):
    t0 = time.time()
    tab.send("Page.navigate", {"url": BASE + "/superset/dashboard/%d/" % did})
    # 关键：等新文档 readyState complete 后再评估（导航窗口期的密集 evaluate 会让 SPA 挂起，
    # 图表网格饿死——20261108 实测：0.6s 紧轮询导致全部查询页 holders=0）
    time.sleep(2.0)
    for _ in range(60):
        if tab.eval("document.readyState") == "complete":
            break
        time.sleep(0.5)
    first = None
    cal_ready_at = None
    deadline = time.time() + 75
    while time.time() < deadline:
        st = json.loads(tab.eval(PAGE_STATE))
        if first is None and (st["md"] or st["holders"] > 0 or st["mr"] or st["err"] or st["tableAny"]):
            first = int((time.time() - t0) * 1000)
        # 必选条件页提前判定（20261115）：日历就绪 8s 后仍无表格即按“待选条件(设计)”收束，
        # 不再空等 75+60s 整窗（长空等会诱发该浏览器会话后续页面的导航停滞，见最终报告教训）
        if did in REQUIRED_FILTER_IDS and st["cal"] and not st["tableAny"]:
            if cal_ready_at is None:
                cal_ready_at = time.time()
            elif time.time() - cal_ready_at > 8:
                break
        # 终止条件
        if did == 32 and st["mr"]:
            break
        if did in CATALOG_IDS and st["mdLinks"] > 0:
            break
        if did in QUERY_IDS | KYB_IDS and (st["tableAny"] or st["err"] or st["deniedCard"]):
            time.sleep(1.5)  # 稳定一拍读工具条摘要
            st = json.loads(tab.eval(PAGE_STATE))
            break
        if did in BI_IDS and st["holders"] > 0 and st["rendered"] >= SLICE_COUNT.get(did, 1):
            break
        if did == 1 and st["rendered"] >= SLICE_COUNT.get(did, 1):
            break
        time.sleep(1.0)
    ms = first if first is not None else int((time.time() - t0) * 1000)
    # 最多再等 60s×scale 图表数据（查询页/BI/病案汇总；慢页复probe可放大）
    if did in QUERY_IDS | KYB_IDS | BI_IDS or did == 1:
        extra = time.time() + int(60 * wait_scale)
        while time.time() < extra:
            st = json.loads(tab.eval(PAGE_STATE))
            if did in QUERY_IDS | KYB_IDS and (st["tableAny"] or st["err"]):
                break
            if (did in BI_IDS or did == 1) and st["rendered"] >= SLICE_COUNT.get(did, 1):
                break
            time.sleep(1.0)
    # 长探针后的呼吸导航：避免下一页继承停滞的会话状态（20261115 教训）
    if time.time() - t0 > 90:
        try:
            tab.send("Page.navigate", {"url": "about:blank"})
            time.sleep(2.0)
        except Exception:
            pass
    return ms, st


def classify(did, st, ms):
    if did in CATALOG_IDS:
        ok = st["md"] and st["mdLinks"] > 0
        return ok, ("目录正常(%d链接)" % st["mdLinks"]) if ok else "目录未渲染", "不适用", "不适用"
    if did == 32:
        ok = st["mr"]
        return ok, "月报正常" if ok else "月报未渲染", "不适用", "不适用"
    if did in BI_IDS:
        want = SLICE_COUNT.get(did, 0)
        ok = st["rendered"] >= want and want > 0
        cal = "正常(%d)" % st["cal"] if st["cal"] else "无(不适用)"
        return ok, ("图表%d/%d渲染" % (st["rendered"], want)) if ok else "图表渲染不全(%d/%d)" % (st["rendered"], want), cal, "不适用(多图看板)"
    # 查询页（1 除外：病案汇总为图表看板）
    if did == 1:
        ok = st["rendered"] >= SLICE_COUNT.get(did, 1)
        return ok, ("图表%d/%d渲染" % (st["rendered"], SLICE_COUNT.get(did, 0))) if ok else "渲染不全", "不适用", "不适用"
    # 必选条件页：筛选条+日历在、无错误、无表格 → 设计行为（fail-closed，选条件后才出表）
    if did in REQUIRED_FILTER_IDS and not st["tableAny"] and not st["err"] and st["cal"]:
        return True, "必选条件页·待选条件(设计)", "正常(%d)" % st["cal"], "不适用(未查询)"
    ok = st["tableAny"] and not st["err"]
    cal = "正常(%d)" % st["cal"] if st["cal"] else ("无(未渲染)" if not ok else "无(不适用)")
    tb = "正常(%d)" % st["tb"] if st["tb"] else ("无(未渲染)" if not ok else "异常")
    if ok and not st["table"]:
        note = "查询页正常·透视表(pivot_table_v2)"   # 39 号等 pivot_table_v2 页
    else:
        note = "查询页正常" if ok else ("错误页" if st["err"] else "表格未出")
    if ok and "失败" in st["sum"]:
        ok, note = False, "工具条摘要报查询失败"
    return ok, note, cal, tb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--ids", default="", help="逗号分隔的看板号子集（续跑/复probe用）；缺省全量51页")
    ap.add_argument("--wait-scale", type=float, default=1.0, help="数据等待窗口放大倍数（慢页复probe用）")
    args = ap.parse_args()
    # 预填每看板图表数
    with open(os.path.join(HERE, "sweep_meta.tsv"), encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 5 and parts[4].isdigit() is False and parts[4] != "(无)":
                pass
            if len(parts) >= 5:
                did, title, pub, roles, slices = parts[0], parts[1], parts[2], parts[3], parts[4]
                if slices not in ("(无)",):
                    SLICE_COUNT[int(did)] = len([s for s in slices.split(",") if s.strip()])
    rows = []
    ids = ALL_IDS
    if args.ids:
        ids = []
        for part in args.ids.split(","):
            ids.append(int(part))
        ids = sorted(set(ids))
    profile = os.path.abspath(os.path.join(HERE, "profile-sw2-%s" % args.tag))
    ver = ""
    ok_login = False

    def open_session(label):
        proc = subprocess.Popen([
            args.exe, "--remote-debugging-port=%d" % args.port, "--user-data-dir=%s" % profile,
            "--no-first-run", "--no-default-browser-check", "--disable-session-crashed-bubble",
            "--window-size=1920,1080", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        v = ""
        for _ in range(60):
            try:
                v = http_json("http://127.0.0.1:%d/json/version" % args.port).get("Browser", "")
                if v:
                    break
            except Exception:
                time.sleep(0.5)
        info = new_tab(args.port)
        ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=30)
        tab = Tab(ws)
        tab.send("Page.enable")
        okl = tab.login("admin", os.environ["ACC_ADMIN"])
        print("[%s] %s %s %s login=%s slices=%s" % (
            time.strftime("%H:%M:%S"), args.tag, v, label, okl, len(SLICE_COUNT)), flush=True)
        return proc, ws, tab, v, okl

    def close_session(proc, ws):
        try:
            ws.close()
        except Exception:
            pass
        proc.terminate()
        time.sleep(1.5)
        proc.kill()

    # 分片执行：每 CHUNK 页重启浏览器（20261115 教训：单会话连续导航后出现页面壳
    # 60-79s 才挂载的会话级停滞，跨页累积、与具体看板无关；独立探针同刻同页 2.4s 正常。
    # 分片换新会话规避；若分片内仍停滞则重启浏览器后重探（重启被实证可完全复位）。）
    CHUNK = 13
    for ci in range(0, len(ids), CHUNK):
        chunk = ids[ci:ci + CHUNK]
        proc, ws, tab, ver, ok_login = open_session("chunk%d/%d" % (ci // CHUNK + 1, (len(ids) + CHUNK - 1) // CHUNK))
        try:
            for did in chunk:
                try:
                    ms, st = probe_page(tab, did, args.wait_scale)
                    ok, note, cal, tb = classify(did, st, ms)
                    # 停滞自愈（20261115）：首框 >30s 且表格未出 → 重启浏览器后重探一次
                    #（同会话内 about:blank 重探对 C87 无效，重启会话实证可完全复位）
                    if not ok and note == "表格未出" and ms > 30000:
                        print("%s %3d RETRY via browser restart (first=%dms)" % (time.strftime("%H:%M:%S"), did, ms), flush=True)
                        close_session(proc, ws)
                        time.sleep(3.0)
                        proc, ws, tab, ver, ok_login = open_session("retry-%d" % did)
                        ms, st = probe_page(tab, did, args.wait_scale)
                        ok, note, cal, tb = classify(did, st, ms)
                    rows.append({"id": did, "ms": ms, "ok": ok, "note": note, "cal": cal, "tb": tb,
                                 "rows": st.get("tableRows", 0), "rendered": st.get("rendered", 0),
                                 "sum": st.get("sum", "")})
                    print("%s %3d %-6s %5dms %s %s" % (time.strftime("%H:%M:%S"), did, "PASS" if ok else "FAIL", ms, note, cal), flush=True)
                except Exception as e:
                    rows.append({"id": did, "ms": -1, "ok": False, "note": "probe-error:" + repr(e)[:120],
                                 "cal": "-", "tb": "-", "rows": 0, "rendered": 0, "sum": ""})
                    print("%s %3d FAIL probe %s" % (time.strftime("%H:%M:%S"), did, repr(e)[:120]), flush=True)
        finally:
            close_session(proc, ws)
        time.sleep(3.0)  # 分片间隙，让进程与端口完全释放
    out = os.path.join(HERE, "sweep-%s%s.json" % (args.tag, "-resume" if args.ids else ""))
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"browser": ver, "rows": rows}, f, ensure_ascii=False, indent=1)
    npass = sum(1 for r in rows if r["ok"])
    print("saved %s: %d/%d pass" % (out, npass, len(rows)), flush=True)


if __name__ == "__main__":
    main()
