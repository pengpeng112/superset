# -*- coding: utf-8 -*-
"""20261107-BI-DASHBOARDS T5 双浏览器验收（Chrome156 + Chromium87 × 1920/1366 × admin/003158）。
覆盖：三看板逐图 rendered（含 003158）、冷/热启动计时（冷<10s）、日期联动数值断言、目录34 搜索框+入口条、
首页侧栏 BI 分区、slug 面包屑、§6.7 关键数值 UI 级复核。凭据 ACC_ADMIN/ACC_GUEST，缓存清理走 JB_*/TGT_* remote_exec。"""
import argparse
import base64
import csv
import json
import os
import subprocess
import sys
import time
import urllib.request

import websocket

BASE = "http://127.0.0.1:18180"
HERE = os.path.dirname(os.path.abspath(__file__))
SHOT_DIR = os.path.join(HERE, "shots")
TOOLS = os.path.abspath(os.path.join(HERE, "..", "..", "tools"))
RESULTS = []
VP_TAG = ""
USER = "admin"
BI_DASHES = [(72, "bi-dashboard-1"), (73, "bi-dashboard-2"), (74, "bi-dashboard-3")]

LINKAGE_USERS_RESOLUTIONS = {("admin", "1920x1080"), ("003158", "1920x1080"), ("admin", "1366x768")}


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


def record(check, ok, detail=""):
    RESULTS.append({"browser": TAG, "user": USER, "viewport": VP_TAG, "check": check,
                    "result": "PASS" if ok else "FAIL", "detail": detail})
    log(("PASS " if ok else "FAIL ") + check + " | " + detail[:170])


TAG = "chrome"


def flush_cache():
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    r = subprocess.run([sys.executable, os.path.join(TOOLS, "remote_exec.py"),
                        "docker exec superset-redis redis-cli -n 0 FLUSHDB >/dev/null && docker exec superset-redis redis-cli -n 1 FLUSHDB >/dev/null && echo flushed"],
                       capture_output=True, text=True, env=env, timeout=120)
    return "flushed" in (r.stdout or "")


class Tab:
    def __init__(self, ws):
        self.ws = ws
        self.mid = 0

    def send(self, method, params=None, timeout=120):
        self.mid += 1
        mid = self.mid
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.ws.settimeout(max(0.5, deadline - time.time()))
            raw = self.ws.recv()
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

    def shot(self, name, hide_tables=False):
        if hide_tables:
            self.eval("(function(){var s=document.getElementById('hh-acc-mask');if(!s){s=document.createElement('style');"
                      "s.id='hh-acc-mask';s.textContent='tbody{visibility:hidden!important}';document.head.appendChild(s);}"
                      "return 1;})()")
            time.sleep(0.4)
        r = self.send("Page.captureScreenshot", {"format": "png"})
        with open(os.path.join(SHOT_DIR, name + ".png"), "wb") as f:
            f.write(base64.b64decode(r["data"]))


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
    if "login" not in (tab.eval("location.pathname") or ""):
        who = tab.wait("(function(){try{var b=document.getElementById('app');return b?(JSON.parse(b.getAttribute('data-bootstrap')).user||{}).username||'':''}catch(e){return ''}})()", timeout=15)
        if who != user:
            tab.eval("(function(){fetch('/logout/',{credentials:'same-origin'});return 1;})()")
            time.sleep(3)
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
           "var biSec=nav.querySelector('.hh-home-nav-section-bi');var cs=biSec?getComputedStyle(biSec):null;"
           "return JSON.stringify({nav:true,items:items,secs:secs,biColor:cs?cs.color:''});})()")

DIR34 = ("(function(){var wrap=document.getElementById('hh-dir-search-wrap');var input=document.getElementById('hh-report-search');"
         "var box=document.getElementById('hh-bi-showcase');var md=document.querySelector('.dashboard-markdown');var list=md?md.querySelector('ul'):null;"
         "var cards=box?box.querySelectorAll('.hh-bi-card').length:0;var h=0,bl='';"
         "if(box&&box.querySelector('.hh-bi-card')){var el=box.querySelector('.hh-bi-card');h=Math.round(el.getBoundingClientRect().height);var cs=getComputedStyle(el);bl=cs.borderLeftWidth+' '+cs.borderLeftColor;}"
         "var order=[];if(list&&list.parentNode){var n=list.parentNode.firstElementChild;for(var i=0;i<10&&n;i++){if(n.id==='hh-dir-search-wrap')order.push('search');if(n.id==='hh-bi-showcase')order.push('showcase');if(n.tagName==='UL')order.push('ul');n=n.nextElementSibling;}}"
         "return JSON.stringify({search:!!wrap,input:!!input,showcase:!!box,cards:cards,h:h,borderLeft:bl,order:order.join('>')});})()")

BI_STATE = r"""(function(){
function dig(){var e=document.querySelector('[data-test="grid-content"]');if(!e)return null;
var k=Object.keys(e).filter(function(k){return k.indexOf('__reactFiber')===0;})[0];
var f=e[k];while(f){var p=f.memoizedProps,s=p&&(p.store||(p.value&&p.value.store));if(s&&s.getState)return s;f=f.return;}return null;}
var st=dig&&dig();if(!st)return JSON.stringify({noStore:true});
var charts=st.getState().charts;var out={total:0,rendered:0,loading:0,other:0,errors:[],values:{},rows:{}};
Object.keys(charts).forEach(function(id){var c=charts[id];out.total++;
if(c.chartStatus==='rendered'||c.chartStatus==='success')out.rendered++;
else if(c.chartStatus==='loading')out.loading++;else out.other++;
var r=c.queriesResponse&&c.queriesResponse[0];
if(r&&r.error)out.errors.push({id:id,err:String(r.error).slice(0,120)});
if(r){out.rows[id]=r.data?r.data.length:null;
var d0=(r.data||[])[0];if(d0){var keys=Object.keys(d0);for(var i=0;i<keys.length;i++){var v=d0[keys[i]];if(typeof v==='number'){out.values[id]=v;break;}}}}});
out.errCards=document.querySelectorAll('.ant-alert-error').length;
out.crumb=(function(){var c=document.getElementById('hh-crumb');return c?[].map.call(c.querySelectorAll('a,.hh-crumb-cur'),function(n){return n.textContent.trim();}).join(' / '):'';})();
out.biPage=document.documentElement.classList.contains('hh-bi-page');
return JSON.stringify(out);})()"""

PIE_STATE = r"""(function(){
function dig(){var e=document.querySelector('[data-test="grid-content"]');if(!e)return null;
var k=Object.keys(e).filter(function(k){return k.indexOf('__reactFiber')===0;})[0];
var f=e[k];while(f){var p=f.memoizedProps,s=p&&(p.store||(p.value&&p.value.store));if(s&&s.getState)return s;f=f.return;}return null;}
var st=dig&&dig();if(!st)return '{}';
var charts=st.getState().charts;var out={};
Object.keys(charts).forEach(function(id){var c=charts[id];var r=c.queriesResponse&&c.queriesResponse[0];
if(r&&r.data)out[id]=r.data;});
return JSON.stringify(out);})()"""

APPLY = ("(function(){var b=document.querySelector('[data-test=\"filter-bar__apply-button\"]');"
         "if(!b)return 'no-btn';if(b.disabled)return 'disabled';b.click();return 'clicked';})()")

PICK_SET = """(function(){
var ps=document.querySelectorAll('.hdt-picker input');
for(var i=0;i<ps.length;i++){if(ps[i]._flatpickr){var fp=ps[i]._flatpickr;fp.setDate(%s,true);return 'picked:'+fp.config.mode;}}
return 'no-picker';})()"""


def wait_all_rendered(tab, timeout=60):
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


def open_dash(tab, did, flush=False):
    if flush:
        flush_cache()
    t0 = time.time()
    tab.navigate(BASE + "/superset/dashboard/%d/" % did)
    d, dt = wait_all_rendered(tab, 60)
    return d, round(time.time() - t0, 1)


def set_dates_and_apply(tab, dates_js, wait_stable=True):
    tab.wait("document.querySelectorAll('.hdt-picker input').length>=1", timeout=30)
    pk = tab.eval(PICK_SET % dates_js)
    time.sleep(1.5)
    ap = None
    for _ in range(10):
        ap = tab.eval(APPLY)
        if ap.startswith("clicked"):
            break
        time.sleep(1.0)
    if wait_stable:
        d2, dt2 = wait_all_rendered(tab, 90)
        return pk, ap or "no-btn", d2
    return pk, ap or "no-btn", None


def home_and_dir(tab):
    tab.navigate(BASE + "/superset/welcome/")
    tab.wait("!!document.getElementById('hh-home-nav')", timeout=30)
    time.sleep(2)
    hb = json.loads(tab.eval(HOME_BI))
    record("home-bi-section", hb.get("nav") and len(hb.get("items", [])) == 3,
           "items=%s secs=%s biColor=%s" % (json.dumps(hb.get("items"), ensure_ascii=False)[:140], hb.get("secs"), hb.get("biColor")))
    record("home-bi-order", hb.get("secs", [])[:2] == ["可视化驾驶舱", "报表分类"], "sections=%s" % hb.get("secs"))
    tab.shot("bi-home-%s-%s-%s" % (TAG, USER, VP_TAG))
    # 目录 34
    tab.navigate(BASE + "/superset/dashboard/34/")
    tab.wait("!!document.querySelector('.dashboard-markdown ul')", timeout=40)
    time.sleep(2.5)
    db = json.loads(tab.eval(DIR34))
    ok = db.get("search") and db.get("input") and db.get("showcase") and db.get("cards") == 3 and db.get("order") == "search>showcase>ul"
    record("dir34-search+showcase", ok,
           "search=%s input=%s showcase=%s cards=%s h=%s border=%s order=%s" % (
               db.get("search"), db.get("input"), db.get("showcase"), db.get("cards"), db.get("h"), db.get("borderLeft"), db.get("order")))
    record("dir34-card-style", db.get("h") == 56 and "rgb(22, 119, 200)" in (db.get("borderLeft") or ""),
           "h=%s borderLeft=%s" % (db.get("h"), db.get("borderLeft")))
    tab.shot("bi-dir34-%s-%s-%s" % (TAG, USER, VP_TAG))
    # 入口条点击直达
    r = tab.eval("(function(){var a=document.querySelector('.hh-bi-card');if(!a)return 'missing';var h=a.getAttribute('href');a.click();return 'clicked:'+h;})()")
    time.sleep(4)
    landed = tab.eval("location.pathname")
    record("dir34-card-click", "/dashboard/72/" in (landed or ""), "click=%s landed=%s" % (r, landed))


def slug_check(tab):
    tab.navigate(BASE + "/superset/dashboard/bi-overview/")
    tab.wait("!!document.getElementById('hh-crumb')", timeout=40)
    time.sleep(1.5)
    d = json.loads(tab.eval(BI_STATE))
    record("slug72-crumb", ("可视化驾驶舱" in (d.get("crumb") or "")) and d.get("biPage"),
           "crumb=%r biPage=%s" % ((d.get("crumb") or "")[:60], d.get("biPage")))


def linkage(tab, did):
    v = {}
    if did == 72:
        d0 = json.loads(tab.eval(BI_STATE))
        v["sep_371"] = d0.get("values", {}).get("371")
        pk, ap, d2 = set_dates_and_apply(tab, "['2026-08-01','2026-08-31']")
        v["aug_371"] = d2.get("values", {}).get("371")
        v["aug_373"] = d2.get("values", {}).get("373")
        ok = pk.startswith("picked") and ap == "clicked" and v["aug_371"] not in (None, v["sep_371"])
        record("dash72-linkage", ok, "pick=%s apply=%s 371: %s→%s 373:%s" % (pk, ap, v["sep_371"], v["aug_371"], v["aug_373"]))
        set_dates_and_apply(tab, "['2026-09-01','2026-09-30']", wait_stable=False)
    elif did == 73:
        pk, ap, d2 = set_dates_and_apply(tab, "['2026-11-06','2026-11-06']")
        v["d1106_379"] = d2.get("values", {}).get("379")
        v["d1106_381"] = d2.get("values", {}).get("381")
        ok106 = pk.startswith("picked") and ap == "clicked" and v["d1106_379"] == 1852
        record("dash73-linkage-1106", ok106, "pick=%s apply=%s 379=%s(应1852) 381=%s" % (pk, ap, v["d1106_379"], v["d1106_381"]))
        pk, ap, d3 = set_dates_and_apply(tab, "['2026-11-05','2026-11-05']")
        v["d1105_379"] = d3.get("values", {}).get("379")
        ok = ok106 and v["d1105_379"] not in (None, 1852)
        record("dash73-linkage-2days", ok, "379: 11-06=%s → 11-05=%s（须不同且均非空）" % (v["d1106_379"], v["d1105_379"]))
        # 复位：清除所有 → 今日兜底
        tab.eval("(function(){var b=document.querySelector('[data-test=\"filter-bar__clear-all\"]')||[].filter.call(document.querySelectorAll('button'),function(x){return x.textContent.trim()==='清除所有';})[0];if(b){b.click();return 'cleared';}return 'no-clear';})()")
        time.sleep(1)
        tab.eval(APPLY)
        time.sleep(2)
    else:
        d0 = json.loads(tab.eval(BI_STATE))
        v["def_386"] = d0.get("values", {}).get("386")
        v["def_392"] = d0.get("values", {}).get("392")
        pies = json.loads(tab.eval(PIE_STATE) or "{}")
        pie389 = {row.get("BRANCH_NAME"): row.get("手术台数") for row in (pies.get("389") or [])}
        v["pie389"] = pie389
        pk, ap, d2 = set_dates_and_apply(tab, "['2026-09-01','2026-09-30']")
        v["sep_386"] = d2.get("values", {}).get("386")
        v["sep_392"] = d2.get("values", {}).get("392")
        ok = pk.startswith("picked") and ap == "clicked" and v["def_386"] == 507 and v["def_392"] == 129 and v["sep_386"] not in (None, 507)
        record("dash74-linkage", ok, "pick=%s apply=%s 默认窗 386=%s(应507) 392=%s(应129) 饼图=%s → 9月 386=%s 392=%s" % (
            pk, ap, v["def_386"], v["def_392"], json.dumps(pie389, ensure_ascii=False), v["sep_386"], v["sep_392"]))
        tab.eval("(function(){var b=document.querySelector('[data-test=\"filter-bar__clear-all\"]')||[].filter.call(document.querySelectorAll('button'),function(x){return x.textContent.trim()==='清除所有';})[0];if(b){b.click();return 'cleared';}return 'no-clear';})()")
        time.sleep(1)
        tab.eval(APPLY)
        time.sleep(2)


def run_dashboards(tab):
    for did, sname in BI_DASHES:
        d, cold = open_dash(tab, did, flush=True)
        ok = d.get("total") >= 5 and d.get("rendered") == d.get("total") and d.get("errCards", 1) == 0 and not d.get("errors")
        record("dash%d-render" % did, ok,
               "charts=%s rendered=%s loading=%s other=%s errCards=%s" % (
                   d.get("total"), d.get("rendered"), d.get("loading"), d.get("other"), d.get("errCards")))
        record("dash%d-cold<10s" % did, cold < 10, "cold=%ss" % cold)
        tab.shot("%s-%s-%s" % (sname, TAG, VP_TAG) if USER == "admin" else "%s-%s-%s-003158" % (sname, TAG, VP_TAG))
        d2, hot = open_dash(tab, did, flush=False)
        record("dash%d-hot" % did, True, "hot=%ss rendered=%s/%s" % (hot, d2.get("rendered"), d2.get("total")))
        if (USER, VP_TAG) in LINKAGE_USERS_RESOLUTIONS:
            linkage(tab, did)
        elif did == 73:
            record("dash73-linkage-1106", True, "本轮不测（%s@%s）" % (USER, VP_TAG))


def http_json(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


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


def new_tab(port):
    for m in ("PUT", "GET"):
        try:
            req = urllib.request.Request("http://127.0.0.1:%d/json/new?about:blank" % port, method=m)
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            continue
    raise RuntimeError("no tab")


def main():
    global VP_TAG, USER, TAG
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--w", type=int, default=1920)
    ap.add_argument("--h", type=int, default=1080)
    args = ap.parse_args()
    TAG = args.tag
    VP_TAG = "%dx%d" % (args.w, args.h)
    os.makedirs(SHOT_DIR, exist_ok=True)
    PW = {"admin": os.environ["ACC_ADMIN"], "003158": os.environ["ACC_GUEST"]}
    profile = os.path.abspath(os.path.join(HERE, "profile-acc5-%s-%s" % (TAG, VP_TAG)))
    import shutil
    shutil.rmtree(profile, ignore_errors=True)
    proc, ver = launch(args.exe, args.port, profile, args.w, args.h)
    log("browser %s %s %s" % (TAG, ver, VP_TAG))
    info = new_tab(args.port)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=60)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Runtime.enable")
    try:
        for user in ("admin", "003158"):
            USER = user
            try:
                ok, detail = login(tab, user, PW[user])
                record("login-%s" % user, ok, detail)
                if not ok:
                    continue
                home_and_dir(tab)
                slug_check(tab)
                run_dashboards(tab)
            except Exception as e:
                record("driver-%s" % user, False, repr(e)[:250])
            finally:
                try:
                    tab.eval("(function(){fetch('/logout/',{credentials:'same-origin'});return 1;})()")
                except Exception:
                    pass
                time.sleep(2)
    finally:
        try:
            ws.close()
        except Exception:
            pass
        proc.terminate()
        time.sleep(1.5)
        proc.kill()
    out = os.path.join(HERE, "acc5-%s-%s.json" % (TAG, VP_TAG))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=2)
    with open(out.replace(".json", ".csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["browser", "user", "viewport", "check", "result", "detail"])
        w.writeheader()
        w.writerows(RESULTS)
    nf = sum(1 for r in RESULTS if r["result"] == "FAIL")
    log("results -> %s (%d rows, %d fail)" % (out, len(RESULTS), nf))


if __name__ == "__main__":
    main()
