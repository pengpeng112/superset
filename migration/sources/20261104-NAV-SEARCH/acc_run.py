# -*- coding: utf-8 -*-
"""20261104-NAV-SEARCH 双浏览器真实验收驱动（Chrome 最新版 + Chromium 87）。
经本机 127.0.0.1:18180 端口转发访问生产 Superset，CDP 驱动真实浏览器窗口，
产出 nav-search-acceptance 结果与脱敏截图。凭据经环境变量注入（ACC_ADMIN/ACC_KYB/ACC_GUEST）。
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

import websocket

BASE = os.environ.get("ACC_BASE", "http://127.0.0.1:18180")
RESULTS = []
SHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")
os.makedirs(SHOT_DIR, exist_ok=True)
USERS = {}


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def record(browser, ver, user, vp, check, result, detail=""):
    RESULTS.append(
        {
            "browser": browser,
            "browser_version": ver,
            "user": user,
            "viewport": VP_TAG[0] if isinstance(VP_TAG, tuple) else VP_TAG,
            "check": check,
            "verify_point": vp,
            "result": "PASS" if result else "FAIL",
            "detail": detail,
        }
    )
    log(("PASS " if result else "FAIL ") + check + " | " + detail[:160])


VP_TAG = ""


class Tab:
    def __init__(self, ws):
        self.ws = ws
        self.mid = 0
        self.events = {}

    def send(self, method, params=None, timeout=30):
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
                self.events[msg["method"]] = msg.get("params", {})
        raise TimeoutError(method)

    def eval(self, expr, await_promise=False):
        r = self.send(
            "Runtime.evaluate",
            {
                "expression": expr,
                "returnByValue": True,
                "awaitPromise": await_promise,
            },
        )
        if r.get("exceptionDetails"):
            d = r["exceptionDetails"]
            desc = ""
            try:
                desc = (d.get("exception") or {}).get("description", "")[:300]
            except Exception:
                pass
            raise RuntimeError("eval error: %s %s | expr=%s" % (d.get("text"), desc, expr[:120]))
        return r["result"].get("value")

    def navigate(self, url, settle=3.0):
        self.events = {}
        self.send("Page.navigate", {"url": url})
        time.sleep(settle)
        for _ in range(40):
            st = self.eval("document.readyState")
            if st == "complete":
                break
            time.sleep(0.5)
        time.sleep(1.0)

    def wait(self, expr, timeout=25, poll=0.4):
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
    # 脱敏：截图前隐藏所有表格体（患者明细不落图）
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
                info = json.loads(r.read().decode("utf-8"))
                return info
        except Exception:
            continue
    targets = http_json("http://127.0.0.1:%d/json" % port)
    for t in targets:
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
        "--window-position=40,40",
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
    state = tab.eval("location.pathname")
    if "login" not in state:
        who = tab.eval("(document.getElementById('app')&&JSON.parse(document.getElementById('app').getAttribute('data-bootstrap')||'{}').user||{}).username||''")
        if who == user:
            return True, "already " + who
        logout(tab)
        tab.navigate(BASE + "/login/")
    tab.wait(
        "(document.querySelectorAll('input[id=\"username\"],input[name=\"username\"]').length>=1"
        "&&document.querySelectorAll('input[id=\"password\"],input[name=\"password\"]').length>=1)",
        timeout=60,
    )
    r = None
    for _ in range(5):
        r = tab.eval(LOGIN_JS_TMPL % (user, USERS[user]))
        if r == "submitted":
            break
        time.sleep(4)
    ok = tab.wait(
        "(function(){var p=location.pathname;return p.indexOf('/login')<0;})()", timeout=20
    )
    if not ok:
        err = tab.eval(
            "(document.querySelector('.alert,.ant-message-error,[role=alert]')||{}).textContent||'no-error-node'"
        )
        return False, "login stuck: %s / %s" % (r, (err or "").strip()[:80])
    who = ""
    for _ in range(30):
        who = tab.eval(
            "(function(){try{var b=document.getElementById('app');"
            "return b&&b.getAttribute('data-bootstrap')?(JSON.parse(b.getAttribute('data-bootstrap')).user||{}).username||'':''}"
            "catch(e){return ''}})()"
        )
        if who:
            break
        time.sleep(1.5)
    return who == user, "logged in as " + who


def logout(tab):
    tab.navigate(BASE + "/logout/")


HOME_STATE = (
    "(function(){var nav=document.getElementById('hh-home-nav');"
    "var kyb=document.getElementById('hh-home-nav-kyb');"
    "var items=nav?nav.querySelectorAll('.hh-home-nav-item').length:-1;"
    "var search=document.getElementById('hh-report-search');"
    "return JSON.stringify({nav:!!nav,items:items,kyb:!!kyb,search:!!search,"
    "kybLabel:kyb?kyb.textContent.trim():'',hhHome:document.documentElement.classList.contains('hh-home')});})()"
)

DROPDOWN_STATE = (
    "(function(){var d=document.getElementById('hh-search-drop');"
    "if(!d||d.style.display==='none')return JSON.stringify({open:false});"
    "var rows=[].map.call(d.querySelectorAll('.hh-search-row'),function(a){return a.textContent.replace(/\\s+/g,' ').trim();});"
    "return JSON.stringify({open:true,rows:rows,empty:!!d.querySelector('.hh-search-empty')});})()"
)

DIR_STATE = (
    "(function(){var gs=[].map.call(document.querySelectorAll('.dashboard-markdown li[data-hh-cat-group]'),function(li){"
    "var nm=li.querySelector('[data-hh-catalog-name]');"
    "return {id:li.getAttribute('data-hh-cat-group'),name:nm?nm.textContent.trim():'',open:li.getAttribute('data-hh-open'),hidden:li.style.display==='none',"
    "reports:[].map.call(li.querySelectorAll('.hh-cat-report'),function(a){return {t:a.textContent.replace(/\\s+/g,' ').trim().slice(0,30),hidden:a.style.display==='none'};})};});"
    "return JSON.stringify({groups:gs,search:!!document.getElementById('hh-dir-search-wrap')});})()"
)

PAGE_STATE = (
    "(function(){var c=document.getElementById('hh-crumb');"
    "return JSON.stringify({"
    "reportPage:document.documentElement.classList.contains('hh-report-page'),"
    "queryUi:document.documentElement.classList.contains('hh-query-ui'),"
    "crumbCount:document.querySelectorAll('.hh-crumb').length,"
    "crumb:c?[].map.call(c.querySelectorAll('a,.hh-crumb-cur'),function(n){return n.textContent.trim();}).join(' / '):'',"
    "crumbLink:c&&c.querySelector('a')?c.querySelector('a').getAttribute('href'):'',"
    "hdt:document.querySelectorAll('.hdt-picker').length,"
    "filterBar:!!document.querySelector('[data-test=\"filter-bar\"]'),"
    "chartTable:!!document.querySelector('.superset-chart-table'),"
    "bodyText:(document.body.innerText||'').replace(/\\s+/g,' ').slice(0,120),"
    "title:(document.querySelector('.dashboard-header-container .input-sizer')||{}).textContent||document.title});})()"
)


def run_home_checks(tab, browser, ver, user, tag):
    vp = "VP1/VP3"
    tab.navigate(BASE + "/superset/welcome/")
    tab.wait("!!document.getElementById('hh-home-nav')||!!document.querySelector('main')", timeout=20)
    time.sleep(2.0)
    st = json.loads(tab.eval(HOME_STATE))
    record(browser, ver, user, vp, "home-sidebar", st["nav"], "nav=%s items=%d" % (st["nav"], st["items"]))
    want_kyb = user in ("admin", "001643")
    record(
        browser, ver, user, vp, "home-nav-kyb",
        st["kyb"] == want_kyb,
        "kyb=%s label=%r (expect %s)" % (st["kyb"], st["kybLabel"], want_kyb),
    )
    record(browser, ver, user, vp, "home-search-input", st["search"], "input#hh-report-search")
    tab.shot("%s-%s-%s-home" % (tag, user, VP_TAG))
    # 搜索交互
    for kw in ("手术", "月报", "医嘱"):
        tab.eval(
            "(function(){var i=document.getElementById('hh-report-search');i.value='%s';"
            "i.dispatchEvent(new Event('input',{bubbles:true}));return true;})()" % kw
        )
        time.sleep(1.2)
        dd = json.loads(tab.eval(DROPDOWN_STATE))
        ok = dd.get("open") and (dd["rows"] and all(kw in r for r in dd["rows"]) or dd.get("empty"))
        if user == "003158" and kw == "医嘱":
            ok = dd.get("open") and dd.get("empty")  # 无抗菌办权限 → 无匹配
        record(
            browser, ver, user, "VP3", "home-search-" + kw, bool(ok),
            "rows=%d empty=%s %s" % (len(dd.get("rows", [])), dd.get("empty"), ";".join(dd.get("rows", [])[:3])),
        )
        if kw == "医嘱" and dd.get("rows"):
            tab.shot("%s-%s-%s-home-drop-%s" % (tag, user, VP_TAG, kw))
    # 跳转：点击第一行
    tab.eval(
        "(function(){var i=document.getElementById('hh-report-search');i.value='医嘱';"
        "i.dispatchEvent(new Event('input',{bubbles:true}));return true;})()"
    )
    time.sleep(1.0)
    dd = json.loads(tab.eval(DROPDOWN_STATE))
    if dd.get("rows"):
        href = tab.eval(
            "(document.querySelector('#hh-search-drop .hh-search-row')||{}).getAttribute ? document.querySelector('#hh-search-drop .hh-search-row').getAttribute('href') : ''"
        )
        tab.eval(
            "(function(){var a=document.querySelector('#hh-search-drop .hh-search-row');if(a){a.click();return 'clicked';}return 'none';})()"
        )
        time.sleep(3.0)
        landed = tab.eval("location.pathname")
        ok = href and href in landed
        record(browser, ver, user, "VP3", "home-search-jump", bool(ok), "href=%s landed=%s" % (href, landed))
        tab.shot("%s-%s-%s-search-jump" % (tag, user, VP_TAG))


def run_dir_checks(tab, browser, ver, user, tag):
    vp = "VP1/VP3"
    tab.navigate(BASE + "/superset/dashboard/34/")
    got = tab.wait("!!document.querySelector('.dashboard-markdown ul')", timeout=20)
    if not got:
        tab.navigate(BASE + "/superset/dashboard/34/", settle=6.0)
        tab.wait("!!document.querySelector('.dashboard-markdown ul')", timeout=45)
    time.sleep(3.0)
    st = json.loads(tab.eval(DIR_STATE))
    n_groups = len(st["groups"])
    want_kyb = user in ("admin", "001643")
    kyb = [g for g in st["groups"] if g["id"] == "kyb"]
    record(browser, ver, user, vp, "dir34-groups", n_groups >= 8, "groups=%d ids=%s" % (n_groups, ",".join(g["id"] for g in st["groups"])))
    record(
        browser, ver, user, vp, "dir34-kyb-group",
        bool(kyb) == want_kyb,
        "kyb group=%s (expect %s)" % (bool(kyb), want_kyb),
    )
    record(browser, ver, user, vp, "dir34-search-input", st["search"], "dir search wrap")
    tab.shot("%s-%s-%s-dir34" % (tag, user, VP_TAG))
    if want_kyb and kyb:
        # 展开 kyb 分组，核对 10 条
        tab.eval(
            "(function(){var li=document.querySelector('li[data-hh-cat-group=\"kyb\"]');"
            "var t=li.querySelector('.hh-cat-toggle');if(t){t.click();}return true;})()"
        )
        time.sleep(2.0)
        st = json.loads(tab.eval(DIR_STATE))
        kyb = [g for g in st["groups"] if g["id"] == "kyb"]
        n = len(kyb[0]["reports"]) if kyb else 0
        hrefs = tab.eval(
            "[].map.call(document.querySelectorAll('li[data-hh-cat-group=\"kyb\"] .hh-cat-report'),function(a){return a.getAttribute('href');}).join(',')"
        )
        ok = n == 10 and all(("/dashboard/%d/" % i) in hrefs for i in range(61, 71))
        record(browser, ver, user, vp, "dir34-kyb-10", ok, "reports=%d hrefs ok=%s" % (n, ok))
        tab.shot("%s-%s-%s-dir34-kyb-open" % (tag, user, VP_TAG))
    # 搜索过滤：只看可见分组；分类名命中则整组放行，否则每条可见行须含关键字
    for kw in ("手术", "月报", "医嘱"):
        if not tab.eval("!!document.getElementById('hh-report-search')"):
            record(browser, ver, user, "VP3", "dir34-search-" + kw, False, "search input missing")
            continue
        tab.eval(
            "(function(){var i=document.getElementById('hh-report-search');i.value='%s';"
            "i.dispatchEvent(new Event('input',{bubbles:true}));return true;})()" % kw
        )
        time.sleep(1.5)
        st = json.loads(tab.eval(DIR_STATE))
        vis = [g for g in st["groups"] if not g["hidden"]]
        expanded = all(g["open"] == "1" for g in vis) if vis else True
        ok_rows = True
        shown = 0
        for g in vis:
            cat_hit = kw in g.get("name", "")
            vis_rows = [r for r in g["reports"] if not r["hidden"]]
            shown += len(vis_rows)
            if not cat_hit:
                if not vis_rows or not all(kw in r["t"] for r in vis_rows):
                    ok_rows = False
        hid_ok = all(
            not r["hidden"]
            for g in st["groups"]
            if g["hidden"]
            for r in g["reports"]
        )
        if user == "003158" and kw == "医嘱":
            ok = len(vis) == 0  # 无抗菌办权限 → 全部隐藏
            detail = "visible=0 expected for guest"
        else:
            ok = bool(vis) and expanded and ok_rows and shown > 0
            detail = "visible=%d expanded=%s rowsOk=%s shown=%d ids=%s" % (
                len(vis), expanded, ok_rows, shown,
                ",".join(g["id"] for g in vis),
            )
        record(browser, ver, user, "VP3", "dir34-search-" + kw, ok, detail)
        if kw == "手术":
            tab.shot("%s-%s-%s-dir34-search-%s" % (tag, user, VP_TAG, kw))
    # 清空恢复
    tab.eval(
        "(function(){var i=document.getElementById('hh-report-search');i.value='';"
        "i.dispatchEvent(new Event('input',{bubbles:true}));return true;})()"
    )
    time.sleep(1.5)
    st = json.loads(tab.eval(DIR_STATE))
    all_vis = all(not g["hidden"] for g in st["groups"])
    all_shown = all(not r["hidden"] for g in st["groups"] for r in g["reports"])
    record(
        browser, ver, user, "VP3", "dir34-search-clear",
        all_vis and all_shown,
        "all visible=%s all rows=%s" % (all_vis, all_shown),
    )
    if want_kyb:
        # 点击 61 链接进入
        tab.eval(
            "(function(){var a=[].filter.call(document.querySelectorAll('li[data-hh-cat-group=\"kyb\"] .hh-cat-report'),function(a){return /\\/dashboard\\/61\\//.test(a.getAttribute('href'));})[0];"
            "if(a){a.click();return 'clicked';}return 'none';})()"
        )
        time.sleep(4.0)
        landed = tab.eval("location.pathname")
        ps = json.loads(tab.eval(PAGE_STATE))
        ok = "/dashboard/61/" in landed and ps["reportPage"] and ps["queryUi"]
        record(browser, ver, user, "VP1", "dir34-kyb-open-61", ok, "landed=%s reportPage=%s queryUi=%s" % (landed, ps["reportPage"], ps["queryUi"]))


def run_page_checks(tab, browser, ver, user, tag, pages):
    for pid, mid_name in pages:
        slug = {2: "/superset/dashboard/mr-discharge-death-detail/", 61: "/superset/dashboard/61/", 65: "/superset/dashboard/65/", 70: "/superset/dashboard/70/"}[pid]
        tab.navigate(BASE + slug)
        time.sleep(1.0)
        tab.wait("!!document.querySelector('#hh-crumb')||!!document.querySelector('.dashboard-header-container')", timeout=25)
        time.sleep(2.0)
        # 等日期契约渲染（首次进入需拉取看板元数据）
        tab.wait("document.querySelectorAll('.hdt-picker').length>=1", timeout=20)
        time.sleep(1.0)
        ps = json.loads(tab.eval(PAGE_STATE))
        ok_cls = ps["reportPage"] and ps["queryUi"]
        record(browser, ver, user, "VP2", "page%d-classes" % pid, ok_cls,
               "hh-report-page=%s hh-query-ui=%s" % (ps["reportPage"], ps["queryUi"]))
        ok_crumb = (
            ps["crumbCount"] == 1
            and ps["crumb"] == "报表目录 / " + mid_name + " / " + ps["title"]
            and ps["crumbLink"] == "/superset/dashboard/34/"
        )
        record(browser, ver, user, "VP2", "page%d-crumb" % pid, ok_crumb,
               "count=%d crumb=%r link=%s" % (ps["crumbCount"], ps["crumb"][:60], ps["crumbLink"]))
        ok_hdt = ps["hdt"] >= 1
        record(browser, ver, user, "VP2", "page%d-hdt" % pid, ok_hdt, "hdt pickers=%d" % ps["hdt"])
        tab.shot("%s-%s-%s-page%d" % (tag, user, VP_TAG, pid))


def run_denied_checks(tab, browser, ver, user, tag):
    # 003158 直开 61：不得出现查询页内容（筛选条/日历/数据表），页面为拒绝/未找到态
    tab.navigate(BASE + "/superset/dashboard/61/")
    time.sleep(5.0)
    ps = json.loads(tab.eval(PAGE_STATE))
    denied = (
        not ps["filterBar"]
        and ps["hdt"] == 0
        and not ps["chartTable"]
    )
    marker = tab.eval(
        "(document.body.innerText.match(/没有权限|无权|not found|404|error|出错了|不存在/i)||['?'])[0]"
    )
    record(browser, ver, user, "VP1", "guest-direct-61-denied", denied,
           "filterBar=%s hdt=%d chartTable=%s marker=%s" % (ps["filterBar"], ps["hdt"], ps["chartTable"], marker))
    tab.shot("%s-%s-%s-direct61" % (tag, user, VP_TAG))


def main():
    global VP_TAG
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--w", type=int, default=1920)
    ap.add_argument("--h", type=int, default=1080)
    ap.add_argument("--users", default="admin,001643,003158")
    args = ap.parse_args()
    VP_TAG = "%dx%d" % (args.w, args.h)
    USERS.update(
        {
            "admin": os.environ["ACC_ADMIN"],
            "001643": os.environ["ACC_KYB"],
            "003158": os.environ["ACC_GUEST"],
        }
    )
    profile = os.path.abspath(os.path.join(SHOT_DIR, "..", "profile-%s-%s" % (args.tag, VP_TAG)))
    proc, ver = launch(args.exe, args.port, profile, args.w, args.h)
    log("browser %s version=%s viewport=%s" % (args.tag, ver, VP_TAG))
    info = new_tab(args.port)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=30)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Runtime.enable")
    try:
        for user in args.users.split(","):
            if user not in USERS:
                continue
            try:
                ok, detail = login(tab, user)
                record(args.tag, ver, user, "LOGIN", "login", ok, detail)
                if not ok:
                    continue
                run_home_checks(tab, args.tag, ver, user, args.tag)
                run_dir_checks(tab, args.tag, ver, user, args.tag)
                if user == "admin":
                    run_page_checks(tab, args.tag, ver, user, args.tag, [(2, "病案专项"), (61, "抗菌药物监测"), (65, "抗菌药物监测"), (70, "抗菌药物监测")])
                elif user == "001643":
                    run_page_checks(tab, args.tag, ver, user, args.tag, [(61, "抗菌药物监测"), (65, "抗菌药物监测"), (70, "抗菌药物监测")])
                else:
                    run_denied_checks(tab, args.tag, ver, user, args.tag)
            except Exception as e:
                record(args.tag, ver, user, "ERROR", "driver-error", False, repr(e)[:200])
            finally:
                try:
                    logout(tab)
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
    out = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "acc-%s-%s.json" % (args.tag, VP_TAG),
    )
    with open(out, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=2)
    log("results -> %s (%d rows, %d fail)" % (out, len(RESULTS), sum(1 for r in RESULTS if r["result"] == "FAIL")))


if __name__ == "__main__":
    main()
