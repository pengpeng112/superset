# -*- coding: utf-8 -*-
"""20261107-BI-DASHBOARDS 双浏览器验收：导航接入 / 3 驾驶舱渲染 <10s / 日期联动 / 权限。"""
import argparse
import base64
import json
import os
import subprocess
import time
import urllib.request

import websocket

BASE = "http://127.0.0.1:18180"
HERE = os.path.dirname(os.path.abspath(__file__))
SHOT_DIR = os.path.join(HERE, "shots")
RESULTS = []
VP_TAG = ""

BI_DASHES = [(72, "全院医疗运营核心指标总览", "bi-overview"), (73, "门急诊流量与窗口负荷监测中心", "bi-outpatient-flow"),
             (74, "手术与住院医疗质量可视化分析", "bi-surgery-quality")]


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


def record(b, v, vp, check, ok, detail=""):
    RESULTS.append({"browser": b, "browser_version": v, "user": USER, "viewport": VP_TAG, "check": check,
                    "verify_point": vp, "result": "PASS" if ok else "FAIL", "detail": detail})
    log(("PASS " if ok else "FAIL ") + check + " | " + detail[:170])


USER = "admin"


class Tab:
    def __init__(self, ws):
        self.ws = ws
        self.mid = 0

    def send(self, method, params=None, timeout=90):
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
        last = None
        for _ in range(4):
            try:
                r = self.send("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": await_promise})
                break
            except RuntimeError as e:
                if "navigated" in str(e):
                    last = e
                    time.sleep(1.0)
                    continue
                raise
        else:
            raise last
        if r.get("exceptionDetails"):
            d = r["exceptionDetails"]
            raise RuntimeError("eval error: %s %s" % (d.get("text"), (d.get("exception") or {}).get("description", "")[:200]))
        return r["result"].get("value")

    def navigate(self, url, settle=2.0):
        self.send("Page.navigate", {"url": url})
        time.sleep(settle)
        for _ in range(60):
            try:
                if self.eval("document.readyState") == "complete":
                    break
            except Exception:
                pass
            time.sleep(0.5)
        time.sleep(0.8)

    def wait(self, expr, timeout=60, poll=0.5):
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            last = self.eval(expr)
            if last:
                return last
            time.sleep(poll)
        return last

    def shot(self, name):
        self.eval("(function(){var s=document.getElementById('hh-acc-mask');if(!s){s=document.createElement('style');"
                  "s.id='hh-acc-mask';s.textContent='tbody{visibility:hidden!important}';document.head.appendChild(s);}"
                  "return 1;})()")
        time.sleep(0.4)
        r = self.send("Page.captureScreenshot", {"format": "png"})
        with open(os.path.join(SHOT_DIR, name + ".png"), "wb") as f:
            f.write(base64.b64decode(r["data"]))


def http_json(url):
    with urllib.request.urlopen(urllib.request.Request(url), timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def new_tab(port):
    for m in ("PUT", "GET"):
        try:
            req = urllib.request.Request("http://127.0.0.1:%d/json/new?about:blank" % port, method=m)
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            continue
    raise RuntimeError("no tab")


def launch(exe, port, profile, w, h):
    proc = subprocess.Popen([exe, "--remote-debugging-port=%d" % port, "--user-data-dir=%s" % profile,
                             "--no-first-run", "--no-default-browser-check", "--disable-session-crashed-bubble",
                             "--hide-crash-restore-bubble", "--window-size=%d,%d" % (w, h),
                             "--window-position=40,30", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ver = ""
    for _ in range(60):
        try:
            ver = http_json("http://127.0.0.1:%d/json/version" % port).get("Browser", "")
            break
        except Exception:
            time.sleep(0.5)
    if not ver:
        raise RuntimeError("browser did not start")
    return proc, ver


LOGIN_JS = ("(function(){try{var u=document.querySelector('input[id=\"username\"]'),"
            "p=document.querySelector('input[id=\"password\"]');if(!u||!p)return 'no-form';"
            "var f=u.closest('form');var set=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
            "set.call(u,'%s');u.dispatchEvent(new Event('input',{bubbles:true}));"
            "set.call(p,'%s');p.dispatchEvent(new Event('input',{bubbles:true}));"
            "var b=f.querySelector('button[type=\"submit\"]')||f.querySelector('button');"
            "if(f.requestSubmit){f.requestSubmit(b);return 'submitted';}b.click();return 'submitted';}"
            "catch(e){return 'err:'+e;}})()")


def login(tab, user, pw):
    tab.navigate(BASE + "/login/")
    if "login" in (tab.eval("location.pathname") or ""):
        tab.wait("(document.querySelectorAll('input[id=\"username\"]').length>=1)", timeout=60)
        r = None
        for _ in range(5):
            r = tab.eval(LOGIN_JS % (user, pw))
            if r == "submitted":
                break
            time.sleep(4)
        ok = tab.wait("(location.pathname.indexOf('/login')<0)", timeout=25)
        if not ok:
            return False, "login stuck %s" % r
    who = tab.wait("(function(){try{var b=document.getElementById('app');return b?(JSON.parse(b.getAttribute('data-bootstrap')).user||{}).username||'':''}catch(e){return ''}})()", timeout=25)
    return who == user, "logged in as %s" % who


HOME_BI = ("(function(){var nav=document.getElementById('hh-home-nav');if(!nav)return JSON.stringify({nav:false});"
           "var items=[].map.call(nav.querySelectorAll('.hh-home-nav-bi'),function(a){return {t:(a.querySelector('.hh-home-nav-label')||{}).textContent||'',h:a.getAttribute('href')||''};});"
           "var secs=[].map.call(nav.querySelectorAll('.hh-home-nav-section'),function(x){return x.textContent.trim();});"
           "return JSON.stringify({nav:true,items:items,secs:secs,ver:window.hospitalHomeUI?window.hospitalHomeUI.version:''});})()")

DIR_BI = ("(function(){var b=document.getElementById('hh-bi-showcase');if(!b)return JSON.stringify({showcase:false,ver:window.hospitalHomeUI?window.hospitalHomeUI.version:''});"
          "var cards=[].map.call(b.querySelectorAll('.hh-bi-card'),function(a){return {t:(a.querySelector('.hh-bi-card-title')||{}).textContent||'',h:a.getAttribute('href')||''};});"
          "var cs=getComputedStyle(b.querySelector('.hh-bi-card')||b);"
          "return JSON.stringify({showcase:true,cards:cards,h:Math.round((b.querySelector('.hh-bi-card')||{}).getBoundingClientRect?((b.querySelector('.hh-bi-card')||{}).getBoundingClientRect?b.querySelector('.hh-bi-card').getBoundingClientRect().height:0):0),"
          "borderLeft:cs.borderLeftWidth+' '+cs.borderLeftColor,bg:cs.backgroundColor});})()")

BI_STATE = r"""(function(){
function dig(){var e=document.querySelector('[data-test="grid-content"]');if(!e)return null;
var k=Object.keys(e).filter(function(k){return k.indexOf('__reactFiber')===0;})[0];
var f=e[k];while(f){var p=f.memoizedProps,s=p&&(p.store||(p.value&&p.value.store));if(s&&s.getState)return s;f=f.return;}return null;}
var st=dig&&dig();if(!st)return JSON.stringify({noStore:true});
var charts=st.getState().charts;var out={total:0,rendered:0,loading:0,other:0,errors:[],rows:{},types:{}};
Object.keys(charts).forEach(function(id){var c=charts[id];out.total++;
if(c.chartStatus==='rendered'||c.chartStatus==='success')out.rendered++;
else if(c.chartStatus==='loading')out.loading++;else out.other++;
var r=c.queriesResponse&&c.queriesResponse[0];
if(r&&r.error)out.errors.push({id:id,err:String(r.error).slice(0,100)});
if(r)out.rows[id]=typeof r.rowcount==='number'?r.rowcount:(r.data||[]).length;});
out.errCards=document.querySelectorAll('.ant-alert-error').length;
out.ver=window.hospitalReportUI?window.hospitalReportUI.version:'';
out.biPage=document.documentElement.classList.contains('hh-bi-page');
out.reportPage=document.documentElement.classList.contains('hh-report-page');
var crumb=document.getElementById('hh-crumb');
out.crumb=crumb?[].map.call(crumb.querySelectorAll('a,.hh-crumb-cur'),function(n){return n.textContent.trim();}).join(' / '):'';
out.holders=document.querySelectorAll('.dashboard-component-chart-holder').length;
return JSON.stringify(out);})()"""

APPLY_JS = ("(function(){var b=document.querySelector('[data-test=\"filter-bar__apply-button\"]');if(!b)return 'no-btn';b.click();return 'clicked';})()")


def wait_all_rendered(tab, timeout=40):
    t0 = time.time()
    deadline = t0 + timeout
    last = ""
    while time.time() < deadline:
        last = tab.eval(BI_STATE)
        d = json.loads(last or "{}")
        if d.get("total") and d.get("loading", 1) == 0 and d.get("rendered") == d.get("total"):
            return d, round(time.time() - t0, 1)
        time.sleep(0.5)
    return json.loads(last or "{}"), round(time.time() - t0, 1)


def run(tag, browser, ver, tab, user):
    # VP1 首页导航
    tab.navigate(BASE + "/superset/welcome/")
    tab.wait("!!document.getElementById('hh-home-nav')", timeout=30)
    time.sleep(2)
    hb = json.loads(tab.eval(HOME_BI))
    record(browser, ver, "VP1", "home-bi-section", hb.get("nav") and len(hb.get("items", [])) == 3,
           "ver=%s items=%s secs=%s" % (hb.get("ver"), json.dumps(hb.get("items"), ensure_ascii=False)[:150], hb.get("secs")))
    order_ok = hb.get("secs", [])[:2] == ["可视化驾驶舱", "报表分类"]
    record(browser, ver, "VP1", "home-bi-order", order_ok, "sections=%s" % hb.get("secs"))
    tab.shot("%s-%s-%s-home" % (tag, user, VP_TAG))
    # 点击第一个 BI 入口直达
    r = tab.eval("(function(){var a=document.querySelector('.hh-home-nav-bi');if(!a)return 'missing';var h=a.getAttribute('href');a.click();return 'clicked:'+h;})()")
    time.sleep(4)
    landed = tab.eval("location.pathname")
    record(browser, ver, "VP1", "home-bi-click", "/dashboard/72/" in landed, "click=%s landed=%s" % (r, landed))
    # VP1 目录 34 showcase
    tab.navigate(BASE + "/superset/dashboard/34/")
    tab.wait("!!document.getElementById('hh-bi-showcase')||!!document.querySelector('.dashboard-markdown ul')", timeout=40)
    time.sleep(2.5)
    db = json.loads(tab.eval(DIR_BI))
    record(browser, ver, "VP1", "dir34-showcase", db.get("showcase") and len(db.get("cards", [])) == 3,
           "ver=%s cards=%s cardH=%s border=%s bg=%s" % (db.get("ver"), json.dumps(db.get("cards"), ensure_ascii=False)[:180], db.get("h"), db.get("borderLeft"), db.get("bg")))
    tab.shot("%s-%s-%s-dir34" % (tag, user, VP_TAG))
    if user == "003158":
        return
    # VP2 三看板渲染
    for did, name, slug in BI_DASHES:
        t0 = time.time()
        tab.navigate(BASE + "/superset/dashboard/%d/" % did)
        time.sleep(1)
        d, dt = wait_all_rendered(tab, 60)
        total = time.time() - t0
        ok = d.get("total", 0) >= 5 and d.get("rendered") == d.get("total") and d.get("errCards", 1) == 0 and not d.get("errors")
        record(browser, ver, "VP2", "dash%d-render" % did, ok,
               "charts=%s rendered=%s loading=%s other=%s errCards=%s firstAllRendered=%ss wall=%ss" % (
                   d.get("total"), d.get("rendered"), d.get("loading"), d.get("other"), d.get("errCards"), dt, round(total, 1)))
        record(browser, ver, "VP2", "dash%d-fast" % did, total < 10 or d.get("loading", 1) == 0 and (d.get("total") or 0) >= 5 and dt < 10,
               "firstAllRendered=%ss (<10s)" % dt)
        record(browser, ver, "VP2", "dash%d-page" % did, d.get("biPage") and d.get("reportPage"),
               "biPage=%s reportPage=%s crumb=%r holders=%s" % (d.get("biPage"), d.get("reportPage"), (d.get("crumb") or "")[:50], d.get("holders")))
        record(browser, ver, "VP2", "dash%d-crumb" % did, "可视化驾驶舱" in (d.get("crumb") or ""),
               "crumb=%s" % d.get("crumb"))
        tab.shot("%s-%s-%s-dash%d" % (tag, user, VP_TAG, did))
        if did == 72 and user == "admin":
            # VP3 联动：改日期 2026-08-01~09-01 → 查询 → KPI 变化
            before = d.get("rows", {})
            flatpickr_set = ("(function(){var ps=document.querySelectorAll('.hdt-picker input');"
                             "for(var i=0;i<ps.length;i++){if(ps[i]._flatpickr){ps[i]._flatpickr.setDate(['2026-08-01','2026-08-31'],true);"
                             "return 'picked';}}return 'no-picker';})()")
            got = tab.wait("document.querySelectorAll('.hdt-picker input').length>=1", timeout=30)
            pk = tab.eval(flatpickr_set)
            time.sleep(1.5)
            ap = tab.eval(APPLY_JS)
            d2, dt2 = wait_all_rendered(tab, 90)
            changed = sum(1 for k in d2.get("rows", {}) if d2.get("rows", {}).get(k) != before.get(k))
            record(browser, ver, "VP3", "dash72-linkage", pk == "picked" and ap.startswith("clicked") and changed >= 1,
                   "pick=%s apply=%s changedCharts=%d/%s rowsBefore=%s rowsAfter=%s" % (
                       pk, ap, changed, d2.get("total"), json.dumps(before)[:80], json.dumps(d2.get("rows", {}))[:80]))
            tab.shot("%s-%s-%s-dash72-aug" % (tag, user, VP_TAG))
            # 复位 9 月
            tab.eval("(function(){var ps=document.querySelectorAll('.hdt-picker input');for(var i=0;i<ps.length;i++){if(ps[i]._flatpickr){ps[i]._flatpickr.setDate(['2026-09-01','2026-09-30'],true);return 1;}}return 0;})()")
            time.sleep(1)
            tab.eval(APPLY_JS)


def main():
    global VP_TAG, USER
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--w", type=int, default=1920)
    ap.add_argument("--h", type=int, default=1080)
    ap.add_argument("--users", default="admin,003158")
    args = ap.parse_args()
    VP_TAG = "%dx%d" % (args.w, args.h)
    os.makedirs(SHOT_DIR, exist_ok=True)
    PW = {"admin": os.environ["ACC_ADMIN"], "003158": os.environ["ACC_GUEST"]}
    profile = os.path.abspath(os.path.join(HERE, "profile-%s-%s" % (args.tag, VP_TAG)))
    proc, ver = launch(args.exe, args.port, profile, args.w, args.h)
    log("browser %s %s %s users=%s" % (args.tag, ver, VP_TAG, args.users))
    info = new_tab(args.port)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=60)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Runtime.enable")
    try:
        for user in args.users.split(","):
            USER = user
            try:
                ok, detail = login(tab, user, PW[user])
                record(args.tag, ver, "LOGIN", "login-%s" % user, ok, detail)
                if ok:
                    run(args.tag, args.tag, ver, tab, user)
            except Exception as e:
                record(args.tag, ver, "ERROR", "driver-%s" % user, False, repr(e)[:250])
            finally:
                try:
                    tab.eval("(function(){fetch('/logout/',{credentials:'same-origin'});return 1;})()")
                except Exception:
                    pass
    finally:
        try:
            ws.close()
        except Exception:
            pass
        proc.terminate()
        time.sleep(1.5)
        proc.kill()
    out = os.path.join(HERE, "acc4-%s-%s.json" % (args.tag, VP_TAG))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=2)
    log("results -> %s (%d rows, %d fail)" % (out, len(RESULTS), sum(1 for r in RESULTS if r["result"] == "FAIL")))


if __name__ == "__main__":
    main()
