# -*- coding: utf-8 -*-
"""20261105-TOOLBAR-GUARD 双浏览器真实验收驱动（Chrome 最新版 + Chromium 87）。

经本机 127.0.0.1:18180 端口转发访问生产 Superset，CDP 驱动真实浏览器窗口：
VP1 查询页 35/45/50/61/65 工具条渲染、行数/耗时摘要、行高切换；
VP2 真实点击「导出 Excel/CSV」并校验下载文件（BOM/中文表头/行数与页面一致）；
VP3 65 页 30 天跨度拦截（守卫+无慢请求）与 15 天放行 + 5 万行截断横幅；
VP4 61 页首开耗时 <20s 与手选 7 天出数。
凭据经环境变量注入（ACC_ADMIN）。结果落 acc2-<tag>-<vp>.json，脱敏截图 shots/。
"""
import argparse
import base64
import glob
import json
import re
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

import websocket

BASE = os.environ.get("ACC_BASE", "http://127.0.0.1:18180")
HERE = os.path.dirname(os.path.abspath(__file__))
SHOT_DIR = os.path.join(HERE, "shots")
DL_DIR = os.path.join(HERE, "downloads")
RESULTS = []
VP_TAG = ""
USERS = {}


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def record(browser, ver, vp, check, result, detail=""):
    RESULTS.append(
        {
            "browser": browser,
            "browser_version": ver,
            "user": "admin",
            "viewport": VP_TAG,
            "check": check,
            "verify_point": vp,
            "result": "PASS" if result else "FAIL",
            "detail": detail,
        }
    )
    log(("PASS " if result else "FAIL ") + check + " | " + detail[:170])


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

    def eval(self, expr, await_promise=False):
        last_err = None
        for attempt in range(4):
            try:
                r = self.send(
                    "Runtime.evaluate",
                    {"expression": expr, "returnByValue": True, "awaitPromise": await_promise},
                )
                break
            except RuntimeError as e:
                # "Inspected target navigated" 瞬态：导航中 eval 被拒，退避重试
                if "navigated" in str(e) and attempt < 3:
                    last_err = e
                    time.sleep(1.0)
                    continue
                raise
        else:
            raise last_err
        if r.get("exceptionDetails"):
            d = r["exceptionDetails"]
            desc = ""
            try:
                desc = (d.get("exception") or {}).get("description", "")[:300]
            except Exception:
                pass
            raise RuntimeError("eval error: %s %s | expr=%s" % (d.get("text"), desc, expr[:120]))
        return r["result"].get("value")

    def navigate(self, url, settle=2.0):
        self.send("Page.navigate", {"url": url})
        time.sleep(settle)
        for _ in range(60):
            st = self.eval("document.readyState")
            if st == "complete":
                break
            time.sleep(0.5)
        time.sleep(0.8)

    def wait(self, expr, timeout=25, poll=0.5):
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            last = self.eval(expr)
            if last:
                return last
            time.sleep(poll)
        return last

    def shot(self, name):
        self.eval(dedesens_js())
        time.sleep(0.3)
        r = self.send("Page.captureScreenshot", {"format": "png"})
        path = os.path.join(SHOT_DIR, name + ".png")
        with open(path, "wb") as f:
            f.write(base64.b64decode(r["data"]))
        return path


def dedesens_js():
    return (
        "(function(){var s=document.getElementById('hh-acc-mask');if(!s){s=document.createElement('style');"
        "s.id='hh-acc-mask';s.textContent='tbody{visibility:hidden!important}';document.head.appendChild(s);}"
        "return true;})()"
    )


def http_json(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def new_tab(port):
    for method in ("PUT", "GET"):
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:%d/json/new?about:blank" % port, method=method
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            continue
    for t in http_json("http://127.0.0.1:%d/json" % port):
        if t.get("type") == "page":
            return t
    raise RuntimeError("no tab")


def launch(exe, port, profile, w, h):
    args = [
        exe,
        "--remote-debugging-port=%d" % port,
        "--user-data-dir=%s" % profile,
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-session-crashed-bubble",
        "--hide-crash-restore-bubble",
        "--window-size=%d,%d" % (w, h),
        "--window-position=40,30",
        "about:blank",
    ]
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ver = ""
    for _ in range(60):
        try:
            ver = http_json("http://127.0.0.1:%d/json/version" % port).get("Browser", "")
            break
        except Exception:
            time.sleep(0.5)
    if not ver:
        raise RuntimeError("browser did not start: %s" % exe)
    return proc, ver


LOGIN_JS_TMPL = (
    "(function(){try{"
    "var u=document.querySelector('input[id=\"username\"],input[name=\"username\"]');"
    "var p=document.querySelector('input[id=\"password\"],input[name=\"password\"]');"
    "if(!u||!p)return 'no-form';"
    "var f=u.closest('form');if(!f||!f.isConnected)return 'no-form';"
    "var set=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
    "set.call(u,'%s');u.dispatchEvent(new Event('input',{bubbles:true}));"
    "set.call(p,'%s');p.dispatchEvent(new Event('input',{bubbles:true}));"
    "var b=f.querySelector('button[type=\"submit\"]')||f.querySelector('button');"
    "if(f.isConnected&&f.requestSubmit){f.requestSubmit(b||undefined);return 'submitted';}"
    "if(b&&b.isConnected){b.click();return 'submitted';}"
    "return 'no-btn';}catch(e){return 'js-err:'+e;}})()"
)


def login(tab, user):
    tab.navigate(BASE + "/login/")
    if "login" not in (tab.eval("location.pathname") or ""):
        tab.navigate(BASE + "/logout/")
        tab.navigate(BASE + "/login/")
    tab.wait(
        "(document.querySelectorAll('input[id=\"username\"]').length>=1"
        "&&document.querySelectorAll('input[id=\"password\"]').length>=1)",
        timeout=60,
    )
    r = None
    for _ in range(5):
        r = tab.eval(LOGIN_JS_TMPL % (user, USERS[user]))
        if r == "submitted":
            break
        time.sleep(4)
    ok = tab.wait("(location.pathname.indexOf('/login')<0)", timeout=25)
    if not ok:
        return False, "login stuck: %s" % r
    who = tab.wait(
        "(function(){try{var b=document.getElementById('app');"
        "return b?(JSON.parse(b.getAttribute('data-bootstrap')).user||{}).username||'':''}catch(e){return ''}})()",
        timeout=20,
    )
    return who == user, "logged in as %s" % who


# ---------- 页面侧探针 ----------

TOOLBAR_STATE = (
    "(function(){var b=document.querySelector('.hh-query-toolbar');"
    "if(!b)return JSON.stringify({toolbar:false});"
    "var s=b.querySelector('.hh-qt-summary');"
    "return JSON.stringify({toolbar:true,chart:b.getAttribute('data-hh-chart'),"
    "summary:s?s.textContent:'',"
    "xlsx:!!b.querySelector('.hh-btn-xlsx'),csv:!!b.querySelector('.hh-btn-csv'),density:!!b.querySelector('.hh-btn-density'),"
    "xlsxDisabled:b.querySelector('.hh-btn-xlsx')?b.querySelector('.hh-btn-xlsx').disabled:null,"
    "csvDisabled:b.querySelector('.hh-btn-csv')?b.querySelector('.hh-btn-csv').disabled:null,"
    "banner:!!document.querySelector('.hh-truncation-banner'),"
    "bannerText:(document.querySelector('.hh-truncation-banner')||{}).textContent||'',"
    "guard:window.hospitalVisitGuard?window.hospitalVisitGuard.version:'',"
    "ui:window.hospitalReportUI?window.hospitalReportUI.version:'',"
    "datesUI:window.hospitalDateUI?window.hospitalDateUI.version:'',"
    "overflow:document.documentElement.scrollWidth>window.innerWidth+2});})()"
)

CHART_READY = (
    "(function(){var h=document.querySelector('.dashboard-component-chart-holder[class*=\"dashboard-chart-id-\"]');"
    "if(!h)return 'no-holder';var m=(h.className||'').match(/dashboard-chart-id-(\\d+)/);if(!m)return 'no-id';"
    "var e=document.querySelector('[data-test=grid-content]');"
    "var k=e&&Object.keys(e).find(function(k){return k.indexOf('__reactFiber')===0;});"
    "var f=e&&e[k],store=null;while(f){var p=f.memoizedProps,s=p&&(p.store||(p.value&&p.value.store));"
    "if(s&&s.getState){store=s;break;}f=f.return;}"
    "var c=store&&store.getState().charts[m[1]];if(!c)return 'no-chart';"
    "if(c.chartStatus==='loading')return 'loading';"
    "if(c.chartStatus!=='rendered'&&c.chartStatus!=='success')return c.chartStatus||'?';"
    "var r=c.queriesResponse&&c.queriesResponse[0];"
    "if(!r)return 'nore';"
    "var rows=typeof r.rowcount==='number'?r.rowcount:(r.data||[]).length;"
    "return 'ok:'+rows+':'+((c.latestQueryFormData||{}).row_limit||0);})()"
)

SET_DRAFT = (
    "(function(a,b){var ps=document.querySelectorAll('.hdt-picker input');"
    "for(var i=0;i<ps.length;i++){if(ps[i]._flatpickr){ps[i]._flatpickr.setDate([a,b],true);return 'picked:'+a+':'+b;}}"
    "return 'no-picker:'+ps.length;})('%s','%s')"
)

CLICK_APPLY = (
    "(function(){var b=document.querySelector('[data-test=\"filter-bar__apply-button\"]');"
    "if(!b)return 'no-btn';b.click();return 'clicked';})()"
)

GUARD_STATE = (
    "(function(){var g=window.hospitalVisitGuard;if(!g)return JSON.stringify({guard:false});"
    "var m=document.getElementById('hdt-visit-msg');"
    "return JSON.stringify({guard:true,lastBlock:g.lastBlock||'',msg:m?m.textContent:'',"
    "span:g.dateSpan?JSON.stringify(g.dateSpan()):'',"
    "check:JSON.stringify(g.currentCheck())});})()"
)


def set_draft(tab, a, b):
    """经 flatpickr 实例真实选日期（等价用户点日历，触发 emit→onChange）。"""
    tab.wait("document.querySelectorAll('.hdt-picker input').length>=1", timeout=40)
    for _ in range(8):
        r = tab.eval(SET_DRAFT % (a, b))
        if r.startswith("picked"):
            return r
        time.sleep(1.5)
    return r


def wait_chart(tab, chart_js_timeout=150):
    """轮询 CHART_READY 直到 ok:n:limit / failed / 超时，返回 (state, seconds)。"""
    t0 = time.time()
    deadline = t0 + chart_js_timeout
    state = ""
    while time.time() < deadline:
        state = tab.eval(CHART_READY)
        if state.startswith("ok:") or state == "failed":
            return state, round(time.time() - t0, 1)
        time.sleep(1.0)
    return state, round(time.time() - t0, 1)


def chart_id_of(tab):
    cid = tab.eval(
        "(function(){var h=document.querySelector('.dashboard-component-chart-holder');"
        "var m=h&&(h.className||'').match(/dashboard-chart-id-(\\d+)/);return m?m[1]:'';})()"
    )
    return cid or "0"


def real_click(tab, selector):
    """CDP Input.dispatchMouseEvent 真实点击（带 user activation，下载类操作必需）。"""
    pos = tab.eval(
        "(function(){var b=document.querySelector('%s');if(!b)return '';var r=b.getBoundingClientRect();"
        "return JSON.stringify({x:r.left+r.width/2,y:r.top+r.height/2,disabled:b?b.disabled:false});})()" % selector
    )
    if not pos:
        return "missing"
    p = json.loads(pos)
    if p.get("disabled"):
        return "disabled"
    for typ in ("mousePressed", "mouseReleased"):
        tab.send("Input.dispatchMouseEvent", {"type": typ, "x": p["x"], "y": p["y"], "button": "left", "clickCount": 1})
    return "clicked@%.0f,%.0f" % (p["x"], p["y"])


def check_exports(tag, tab, browser, ver, expect_rows, label):
    """点击工具条导出按钮并校验下载文件（csv BOM/中文表头/行数、xlsx 合法与行数）"""
    for fmt, btn, ext in (("xlsx", "button.hh-btn-xlsx", ".xlsx"), ("csv", "button.hh-btn-csv", ".csv")):
        before = set(glob.glob(os.path.join(DL_DIR, "*")))
        r = real_click(tab, ".hh-query-toolbar %s" % btn)
        if not r.startswith("clicked"):
            record(browser, ver, "VP2", "%s-%s-click" % (label, fmt), False, "button %s" % r)
            continue
        # 先快速读一次工具条摘要（fetch 立即失败时 30s 内可见）
        time.sleep(2.5)
        note_early = tab.eval(
            "((document.querySelector('.hh-query-toolbar .hh-qt-summary')||{}).textContent||'')"
        )
        file_ok, fname = wait_download(before)
        note = tab.eval(
            "((document.querySelector('.hh-query-toolbar .hh-qt-summary')||{}).textContent||'')"
        )
        note_show = note if ("已导出" in note or "导出失败" in note or "未捕获" in note) else note_early
        if not file_ok:
            record(browser, ver, "VP2", "%s-%s-download" % (label, fmt), False,
                   "no file; note=%s" % (note_show or note)[:140])
            continue
        ok, detail = verify_file(fname, fmt, expect_rows)
        record(browser, ver, "VP2", "%s-%s-file" % (label, fmt), ok,
               "%s | %s | note=%s" % (os.path.basename(fname), detail, (note_show or note)[:80]))


def wait_download(before, timeout=180):
    t0 = time.time()
    seen = {}
    while time.time() - t0 < timeout:
        cur = set(glob.glob(os.path.join(DL_DIR, "*"))) - before
        busy = False
        for p in cur:
            if p.endswith(".crdownload") or p.endswith(".tmp"):
                busy = True
                continue
            try:
                sz = os.path.getsize(p)
            except OSError:
                busy = True
                continue
            if seen.get(p) != sz:
                seen[p] = sz
                busy = True
        if cur and not busy and not seen.get("__stable__"):
            time.sleep(1.2)
            for p in list(seen):
                if p in ("__stable__",) or not os.path.exists(p):
                    continue
                if os.path.getsize(p) != seen[p]:
                    busy = True
            if not busy:
                for p in cur:
                    if not p.endswith(".crdownload") and os.path.exists(p):
                        return True, p
        time.sleep(1.0)
    return False, ""


def verify_file(path, fmt, expect_rows):
    name = os.path.basename(path)
    try:
        if expect_rows is not None and not (200 <= expect_rows):
            # 行数一致性只对 65 单日等已知页校验；35 页月报行数由页面摘要读出后再比
            pass
        if fmt == "csv":
            with open(path, "rb") as f:
                raw = f.read()
            if not raw:
                return False, "empty csv"
            bom = raw[:3] == b"\xef\xbb\xbf"
            text = raw.decode("utf-8-sig")
            lines = [ln for ln in text.splitlines() if ln.strip()]
            header = lines[0] if lines else ""
            has_cjk = any("\u4e00" <= ch <= "\u9fff" for ch in header)
            detail = "rows=%d bom=%s cjk_header=%s header=%s" % (len(lines) - 1, bom, has_cjk, header[:60])
            ok = bom and has_cjk and len(lines) - 1 > 0
            if expect_rows is not None and expect_rows > 0:
                ok = ok and (len(lines) - 1 == expect_rows)
                detail += " expect=%d" % expect_rows
            return ok, detail
        else:
            if not zipfile.is_zipfile(path):
                return False, "not a zip/xlsx"
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
                if "[Content_Types].xml" not in names:
                    return False, "xlsx missing Content_Types"
                sheet = [n for n in names if n.startswith("xl/worksheets/sheet")]
                if not sheet:
                    return False, "xlsx missing sheet"
                xml = z.read(sheet[0]).decode("utf-8", "replace")
                nrows = xml.count("<row ")
                shared = [n for n in names if n == "xl/sharedStrings.xml"]
                cjk = False
                if shared:
                    ss = z.read(shared[0]).decode("utf-8", "replace")
                    cjk = any("\u4e00" <= ch <= "\u9fff" for ch in ss[:4000])
            detail = "xlsx_rows=%d cjk=%s" % (nrows, cjk)
            ok = nrows > 0 and cjk
            if expect_rows is not None and expect_rows > 0:
                ok = ok and (nrows == expect_rows + 1)
                detail += " expect=%d(+header)" % expect_rows
            return ok, detail
    except Exception as e:
        return False, "verify error: %r" % e


def run(tag, browser, ver, tab, heavy):
    """单浏览器全流程。heavy=True 时执行 15 天 5 万行截断横幅验证。"""
    # ---- VP1/VP4a：查询页 35/45/50/61/65 工具条 ----
    pages = [(35, "page35"), (45, "page45"), (50, "page50"), (61, "page61"), (65, "page65")]
    summary_cache = {}
    for pid, label in pages:
        t0 = time.time()
        tab.navigate(BASE + "/superset/dashboard/%d/" % pid)
        got = tab.wait("!!document.querySelector('.hh-query-toolbar')", timeout=40)
        st = json.loads(tab.eval(TOOLBAR_STATE))
        if not got or not st.get("toolbar"):
            record(browser, ver, "VP1", "%s-toolbar" % label, False, "toolbar=%s nav=%.1fs" % (st.get("toolbar"), time.time() - t0))
            tab.shot("%s-%s-%s-%s-miss" % (tag, "admin", VP_TAG, label))
            continue
        # 等查询完成（61 首载 SQL 兜底；65 兜底+2 万行渲染在旧 Chromium 上波动大）
        timeout = 200 if pid in (61, 65) else 120
        state, secs = wait_chart(tab, timeout)
        # 摘要刷新存在 120ms 级竞态：等到“共返回”出现（最多 8s）
        tab.wait("(function(){var s=document.querySelector('.hh-query-toolbar .hh-qt-summary');return s&&/共返回|查询失败/.test(s.textContent);})()", timeout=8)
        st = json.loads(tab.eval(TOOLBAR_STATE))
        rows_ok = "共返回" in st.get("summary", "") and ("行数据" in st.get("summary", ""))
        record(browser, ver, "VP1", "%s-summary" % label, rows_ok,
               "summary=%r chart=%s %.1fs" % (st.get("summary", "")[:80], state, secs))
        btns = st.get("xlsx") and st.get("csv") and st.get("density")
        enabled = st.get("xlsxDisabled") is False and st.get("csvDisabled") is False
        record(browser, ver, "VP1", "%s-buttons" % label, bool(btns) and enabled,
               "xlsx=%s csv=%s density=%s xlsxDisabled=%s csvDisabled=%s" % (
                   st.get("xlsx"), st.get("csv"), st.get("density"), st.get("xlsxDisabled"), st.get("csvDisabled")))
        record(browser, ver, "VP1", "%s-versions" % label,
               st.get("ui") == "20261105f10" and st.get("guard") == "20261105g4",
               "ui=%s guard=%s dates=%s" % (st.get("ui"), st.get("guard"), st.get("datesUI")))
        record(browser, ver, "VP1", "%s-no-overflow" % label, not st.get("overflow"),
               "scrollWidth overflow=%s" % st.get("overflow"))
        summary_cache[pid] = st.get("summary", "")
        tab.shot("%s-%s-%s-%s" % (tag, "admin", VP_TAG, label))
        if pid == 61:
            total = time.time() - t0
            record(browser, ver, "VP4", "page61-firstload", total < 20,
                   "first-open %.1fs (<20s) state=%s" % (total, state))
    # ---- VP1 行高切换（在 65 页测，轻量）----
    tab.navigate(BASE + "/superset/dashboard/65/")
    tab.wait("!!document.querySelector('.hh-query-toolbar')", timeout=40)
    state, _ = wait_chart(tab, 150)
    # C87 渲染 2.4 万行较慢：等首个 td 出现再量行高
    tab.wait("!!document.querySelector('.superset-chart-table tbody td')", timeout=90)
    r = tab.eval(
        "(function(){var b=document.querySelector('.hh-btn-density');if(!b)return 'missing';"
        "var h0=document.documentElement.classList.contains('hh-density-compact');b.click();"
        "var h1=document.documentElement.classList.contains('hh-density-compact');"
        "var ss=sessionStorage.getItem('hhTableDensity');"
        "var td=document.querySelector('.superset-chart-table td');"
        "var hh=td?Math.round(td.getBoundingClientRect().height):0;"
        "b.click();var h2=document.documentElement.classList.contains('hh-density-compact');"
        "var ss2=sessionStorage.getItem('hhTableDensity');"
        "var td2=document.querySelector('.superset-chart-table td');"
        "var hh2=td2?Math.round(td2.getBoundingClientRect().height):0;"
        "return JSON.stringify({h0:h0,h1:h1,ss:ss,hh:hh,h2:h2,ss2:ss2,hh2:hh2});})()"
    )
    d = json.loads(r or "{}")
    # 紧凑行高受表格单元格内容影响存在少量偏差：以「明显低于标准行高且 ≈32px（容差 44）」为准
    ok = (not d.get("h0")) and d.get("h1") and d.get("ss") == "compact" and 26 <= d.get("hh", 0) <= 44 \
         and (not d.get("h2")) and d.get("ss2") == "standard" and d.get("hh2", 0) > d.get("hh", 0)
    record(browser, ver, "VP1", "density-toggle", ok,
           "compact h=%s ss=%s -> standard h=%s ss=%s" % (d.get("hh"), d.get("ss"), d.get("hh2"), d.get("ss2")))
    tab.shot("%s-%s-%s-density" % (tag, "admin", VP_TAG))
    # ---- VP2：65 页单日 2026-09-16 查询 + 导出 ----
    r = set_draft(tab, "2026-09-16", "2026-09-16")
    time.sleep(1.5)
    tab.eval(CLICK_APPLY)
    state, secs = wait_chart(tab, 200)
    st = json.loads(tab.eval(TOOLBAR_STATE))
    m = state.partition(":")[2].partition(":")
    rows = int(m[0]) if m[0].isdigit() else -1
    limit = int(m[2]) if m[2].isdigit() else 0
    record(browser, ver, "VP2", "page65-day-query", state.startswith("ok:") and rows > 0,
           "draft=%s state=%s %ss summary=%r" % (r, state, secs, st.get("summary", "")[:60]))
    tab.shot("%s-%s-%s-page65-day" % (tag, "admin", VP_TAG))
    check_exports(tag, tab, browser, ver, rows if rows > 0 else None, "page65")
    # ---- VP2：35 页导出（首查默认月份数据，行数从摘要读）----
    tab.navigate(BASE + "/superset/dashboard/35/")
    tab.wait("!!document.querySelector('.hh-query-toolbar')", timeout=40)
    state, _ = wait_chart(tab, 90)
    tab.wait("(function(){var s=document.querySelector('.hh-query-toolbar .hh-qt-summary');return s&&/共返回/.test(s.textContent);})()", timeout=8)
    st = json.loads(tab.eval(TOOLBAR_STATE))
    mm = re.search(r"共返回\s*([\d,]+)\s*行", st.get("summary", ""))
    rows35 = int(mm.group(1).replace(",", "")) if mm else None
    check_exports(tag, tab, browser, ver, rows35, "page35")
    # ---- VP3a：65 页 30 天跨度拦截 ----
    tab.navigate(BASE + "/superset/dashboard/65/")
    tab.wait("!!document.querySelector('.hh-query-toolbar')", timeout=40)
    wait_chart(tab, 150)
    before = tab.eval(CHART_READY)
    r = set_draft(tab, "2026-09-01", "2026-09-30")
    time.sleep(1.5)
    tab.eval(CLICK_APPLY)
    time.sleep(3.0)
    gs = json.loads(tab.eval(GUARD_STATE))
    after = tab.eval(CHART_READY)
    ok = ("请勿超过 15 天" in gs.get("msg", "")) and ("请勿超过 15 天" in gs.get("lastBlock", "")) \
         and ("loading" not in after) and after == before
    record(browser, ver, "VP3", "page65-span30-blocked", ok,
           "msg=%r lastBlock=%r before=%s after=%s draft=%s" % (
               gs.get("msg", "")[:60], gs.get("lastBlock", "")[:50], before, after, r))
    tab.shot("%s-%s-%s-page65-blocked" % (tag, "admin", VP_TAG))
    # ---- VP3b：15 天放行 + 5 万行截断横幅（heavy）----
    if heavy:
        r = set_draft(tab, "2026-09-01", "2026-09-15")
        time.sleep(1.5)
        gs0 = json.loads(tab.eval(GUARD_STATE))
        tab.eval(CLICK_APPLY)
        state, secs = wait_chart(tab, 480)
        st = json.loads(tab.eval(TOOLBAR_STATE))
        mm = state.partition(":")[2].partition(":")
        rows = int(mm[0]) if mm[0].isdigit() else -1
        limit = int(mm[2]) if mm[2].isdigit() else 0
        banner = st.get("banner") and "数据截断警告" in st.get("bannerText", "") and "50,000" in st.get("bannerText", "")
        record(browser, ver, "VP3", "page65-span15-passed", state.startswith("ok:") and rows > 0,
               "draft=%s state=%s %.0fs span=%s" % (r, state, secs, gs0.get("span", "")))
        record(browser, ver, "VP3", "page65-truncation-banner",
               bool(banner) and rows == 50000,
               "banner=%s rows=%d limit=%d text=%r" % (st.get("banner"), rows, limit, st.get("bannerText", "")[:60]))
        tab.shot("%s-%s-%s-page65-banner" % (tag, "admin", VP_TAG))
        # 收窄回单日：横幅自动移除
        set_draft(tab, "2026-09-16", "2026-09-16")
        time.sleep(1.0)
        tab.eval(CLICK_APPLY)
        state2, _ = wait_chart(tab, 200)
        st2 = json.loads(tab.eval(TOOLBAR_STATE))
        record(browser, ver, "VP3", "page65-banner-removed", not st2.get("banner"),
               "after requery banner=%s state=%s" % (st2.get("banner"), state2))
    # ---- VP4b：61 页手选 2026-09-01~09-07 出数 ----
    tab.navigate(BASE + "/superset/dashboard/61/")
    tab.wait("!!document.querySelector('.hh-query-toolbar')", timeout=40)
    r = set_draft(tab, "2026-09-01", "2026-09-07")
    time.sleep(1.5)
    tab.eval(CLICK_APPLY)
    state, secs = wait_chart(tab, 240)
    mm = state.partition(":")[2].partition(":")
    rows = int(mm[0]) if mm[0].isdigit() else -1
    st = json.loads(tab.eval(TOOLBAR_STATE))
    record(browser, ver, "VP4", "page61-week-query", state.startswith("ok:") and rows > 0,
           "draft=%s state=%s %.0fs summary=%r" % (r, state, secs, st.get("summary", "")[:60]))
    tab.shot("%s-%s-%s-page61-week" % (tag, "admin", VP_TAG))


def main():
    global VP_TAG
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--w", type=int, default=1920)
    ap.add_argument("--h", type=int, default=1080)
    ap.add_argument("--heavy", action="store_true", help="执行 15 天 5 万行截断横幅验证")
    args = ap.parse_args()
    VP_TAG = "%dx%d" % (args.w, args.h)
    os.makedirs(SHOT_DIR, exist_ok=True)
    if os.path.isdir(DL_DIR):
        shutil.rmtree(DL_DIR)
    os.makedirs(DL_DIR, exist_ok=True)
    USERS.update({"admin": os.environ["ACC_ADMIN"]})
    profile = os.path.abspath(os.path.join(HERE, "profile-%s-%s" % (args.tag, VP_TAG)))
    proc, ver = launch(args.exe, args.port, profile, args.w, args.h)
    log("browser %s version=%s viewport=%s heavy=%s" % (args.tag, ver, VP_TAG, args.heavy))
    info = new_tab(args.port)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=40)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Runtime.enable")
    # 允许下载到本批目录：browser 级 + tab 级，均读回执确认
    try:
        bws_info = http_json("http://127.0.0.1:%d/json/version" % args.port)
        bws = websocket.create_connection(bws_info["webSocketDebuggerUrl"], timeout=20)
        bws.send(json.dumps({"id": 1, "method": "Browser.setDownloadBehavior",
                             "params": {"behavior": "allow", "downloadPath": DL_DIR, "eventsEnabled": True}}))
        deadline = time.time() + 10
        while time.time() < deadline:
            msg = json.loads(bws.recv())
            if msg.get("id") == 1:
                log("Browser.setDownloadBehavior receipt: %s" % json.dumps(msg.get("result", msg.get("error", {})))[:120])
                break
    except Exception as e:
        log("download behavior warn: %r" % e)
    try:
        try:
            r = tab.send("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": DL_DIR})
            log("Page.setDownloadBehavior receipt: %s" % json.dumps(r)[:100])
        except Exception as e:
            log("Page.setDownloadBehavior warn: %r" % e)
        ok, detail = login(tab, "admin")
        record(args.tag, ver, "LOGIN", "login", ok, detail)
        if ok:
            run(args.tag, args.tag, ver, tab, args.heavy)
    except Exception as e:
        record(args.tag, ver, "ERROR", "driver-error", False, repr(e)[:250])
    finally:
        try:
            tab.eval("(function(){fetch('/logout/',{credentials:'same-origin'});return 1;})()")
        except Exception:
            pass
        try:
            ws.close()
        except Exception:
            pass
        proc.terminate()
        time.sleep(1.5)
        proc.kill()
    out = os.path.join(HERE, "acc2-%s-%s.json" % (args.tag, VP_TAG))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=2)
    log("results -> %s (%d rows, %d fail)" % (out, len(RESULTS), sum(1 for r in RESULTS if r["result"] == "FAIL")))


if __name__ == "__main__":
    main()
