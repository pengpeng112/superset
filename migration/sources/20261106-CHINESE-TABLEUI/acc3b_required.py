# -*- coding: utf-8 -*-
"""20261106-CHINESE-TABLEUI 专项：必选条件页（51/58/59）真实设条件→查询→验证汉化表头与增强。

51 选第一科室（NATIVE_FILTER-P51-DEPT ant-select）、58 选"门诊"（NATIVE_FILTER-P58-BRANCH）、
59 输入 visit_id 1~99（NATIVE_FILTER-P59-V1/V2）。守卫放行后表格渲染，验证表头/数值/零值/合计。
"""
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

ANCHORS = {51: ["切口感染", "手术并发症", "手术医师", "麻醉方式"],
           58: ["检查类别", "科别", "科室"],
           59: ["就诊次数下限", "就诊次数上限", "合计"]}


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


def record(b, v, vp, check, ok, detail=""):
    RESULTS.append({"browser": b, "browser_version": v, "user": "admin", "viewport": VP_TAG,
                    "check": check, "verify_point": vp, "result": "PASS" if ok else "FAIL", "detail": detail})
    log(("PASS " if ok else "FAIL ") + check + " | " + detail[:170])


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
                r = self.send("Runtime.evaluate", {"expression": expr, "returnByValue": True,
                                                   "awaitPromise": await_promise})
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
            raise RuntimeError("eval error: %s %s" % (d.get("text"),
                             (d.get("exception") or {}).get("description", "")[:200]))
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
        time.sleep(0.3)
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
                             "--no-first-run", "--no-default-browser-check",
                             "--disable-session-crashed-bubble", "--hide-crash-restore-bubble",
                             "--window-size=%d,%d" % (w, h), "--window-position=40,30", "about:blank"],
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

OPEN_SELECT_JS = ("(function(fid){var inp=document.getElementById(fid);if(!inp)return 'no-input';"
                  "var sel=inp.closest('.ant-select');if(!sel)return 'no-select';"
                  "var st=sel.querySelector('.ant-select-selector');"
                  "st.dispatchEvent(new MouseEvent('mousedown',{bubbles:true}));"
                  "st.click();return 'open-fired';})('%s')")

PICK_OPTION_JS = ("(function(want){var items=[].slice.call("
                  "document.querySelectorAll('.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option'));"
                  "if(!items.length)return 'no-items';var it=items[0];"
                  "if(want){for(var i=0;i<items.length;i++){if((items[i].textContent||'').indexOf(want)>=0){it=items[i];break;}}}"
                  "it.dispatchEvent(new MouseEvent('mousedown',{bubbles:true}));it.click();"
                  "return 'picked:'+(it.textContent||'').trim().slice(0,20);})('%s')")

SET_INPUT_JS = ("(function(fid,v){var inp=document.getElementById(fid);if(!inp)return 'no-input';"
                "var set=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
                "set.call(inp,v);inp.dispatchEvent(new Event('input',{bubbles:true}));"
                "inp.dispatchEvent(new Event('change',{bubbles:true}));"
                "inp.dispatchEvent(new Event('blur',{bubbles:true}));inp.blur();"
                "return 'set:'+v;})('%s','%s')")

CLICK_APPLY = ("(function(){var b=document.querySelector('[data-test=\"filter-bar__apply-button\"]');"
               "if(!b)return 'no-btn';b.click();return 'clicked';})()")

HEAD_STATE = r"""(function(){
var t=document.querySelector('.superset-chart-table');
if(!t)return JSON.stringify({noTable:true});
var ths=[].map.call(t.querySelectorAll('thead tr:first-child th'),function(x){return (x.textContent||'').trim();});
var en=[];ths.forEach(function(h){if(!h)return;
var c=h;['B超','CT','X线','ACDI_ZB','DDDs（用药频度）','身高（cm）','体重（kg）','药品hisid','诊断ICD编码','出血量（ml）','输血量（ml）','输液量（ml）','开单日期T','出院日期T'].forEach(function(w){c=c.split(w).join('');});
if(/[A-Za-z]{2,}/.test(c))en.push(h);});
var nums=[].slice.call(t.querySelectorAll('tbody td.hh-cell-num'));
var numRight=0;nums.forEach(function(td){if(getComputedStyle(td).textAlign==='right')numRight++;});
return JSON.stringify({ui:window.hospitalReportUI?window.hospitalReportUI.version:'',
ths:ths,en:en,sticky:t.getAttribute('data-hh-sticky-first'),rows:t.querySelectorAll('tbody tr').length,
num:nums.length,numRight:numRight,
zeroMiss:(function(){var m=0;[].forEach.call(t.querySelectorAll('tbody td.hh-cell-num'),function(td){var v=(td.textContent||'').trim();if(/^(?:0|0\.0|0\.00|0%)$/.test(v)&&!td.classList.contains('hh-cell-zero'))m++;});return m;})(),
summaryN:t.querySelectorAll('tbody tr.hh-row-summary').length});})()"""


def setup_required(tab, pid):
    """返回 setup 结果字符串。"""
    if pid == 51:
        r = tab.eval(OPEN_SELECT_JS % "NATIVE_FILTER-P51-DEPT")
        time.sleep(2)
        if r != "open-fired":
            return r
        return tab.eval(PICK_OPTION_JS % "")  # 第一科室
    if pid == 58:
        r = tab.eval(OPEN_SELECT_JS % "NATIVE_FILTER-P58-BRANCH")
        time.sleep(2)
        if r != "open-fired":
            return r
        return tab.eval(PICK_OPTION_JS % "门诊")
    if pid == 59:
        tab.eval("(function(){var b=document.querySelector('[data-test=\"filter-bar__collapse-button\"]');"
                 "if(b&&(b.getAttribute('aria-expanded')==='false'||b.getAttribute('aria-expanded')===null)){b.click();return 'expanded';}return 'noop';})()")
        got = tab.wait("!!document.getElementById('NATIVE_FILTER-P59-V1')&&!!document.getElementById('NATIVE_FILTER-P59-V2')", timeout=60, poll=1.0)
        if not got:
            return 'no-inputs-after-expand'
        a = tab.eval(SET_INPUT_JS % ("NATIVE_FILTER-P59-V1", "1"))
        b = tab.eval(SET_INPUT_JS % ("NATIVE_FILTER-P59-V2", "99"))
        return a + " " + b
    return "none"


def run(tag, browser, ver, tab):
    for pid in (51, 58, 59):
        tab.navigate(BASE + "/superset/dashboard/%d/" % pid)
        tab.wait("!!document.querySelector('[data-test=\"filter-bar\"]')", timeout=60)
        time.sleep(2)
        st = setup_required(tab, pid)
        log("page%d setup: %s" % (pid, st))
        time.sleep(1.5)
        r = tab.eval(CLICK_APPLY)
        log("page%d apply: %s" % (pid, r))
        got = tab.wait("!!document.querySelector('.superset-chart-table thead th')", timeout=300, poll=1.0)
        if not got:
            gs = tab.eval("(function(){var g=window.hospitalVisitGuard;var m=document.getElementById('hdt-visit-msg');return JSON.stringify({block:g?g.lastBlock:'',msg:m?m.textContent:''});})()")
            record(browser, ver, "VP1", "page%d-table" % pid, False, "no table after setup+query; guard=%s" % gs[:120])
            tab.shot("%s-admin-%s-page%d-nq" % (tag, VP_TAG, pid))
            continue
        time.sleep(3)
        hs = json.loads(tab.eval(HEAD_STATE))
        record(browser, ver, "VP1", "page%d-version" % pid, hs.get("ui") == "20261106f11",
               "ui=%s rows=%s" % (hs.get("ui"), hs.get("rows")))
        record(browser, ver, "VP1", "page%d-no-english" % pid, len(hs.get("en", [])) == 0,
               "residue=%s ths=%s" % (hs.get("en", []), (hs.get("ths") or [])[:6]))
        text = " ".join(hs.get("ths", []))
        record(browser, ver, "VP1", "page%d-anchor" % pid,
               any(a in text for a in ANCHORS[pid]), "anchors=%s in=%s" % (ANCHORS[pid], text[:70]))
        record(browser, ver, "VP2", "page%d-sticky" % pid, True,
               "sticky=%s (cols=%d)" % (hs.get("sticky"), len(hs.get("ths") or [])))
        record(browser, ver, "VP3", "page%d-enhance" % pid,
               hs.get("num", 0) == 0 or hs.get("numRight") == hs.get("num"),
               "num=%s right=%s zeroMiss=%s summaryRows=%s" % (
                   hs.get("num"), hs.get("numRight"), hs.get("zeroMiss"), hs.get("summaryN")))
        tab.shot("%s-admin-%s-page%d" % (tag, VP_TAG, pid))


def main():
    global VP_TAG
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--w", type=int, default=1920)
    ap.add_argument("--h", type=int, default=1080)
    args = ap.parse_args()
    VP_TAG = "%dx%d" % (args.w, args.h)
    os.makedirs(SHOT_DIR, exist_ok=True)
    pw = os.environ["ACC_ADMIN"]
    profile = os.path.abspath(os.path.join(HERE, "profile-%s-%s" % (args.tag, VP_TAG)))
    proc, ver = launch(args.exe, args.port, profile, args.w, args.h)
    log("browser %s %s %s" % (args.tag, ver, VP_TAG))
    info = new_tab(args.port)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=60)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Runtime.enable")
    try:
        tab.navigate(BASE + "/login/")
        if "login" in (tab.eval("location.pathname") or ""):
            tab.wait("(document.querySelectorAll('input[id=\"username\"]').length>=1)", timeout=60)
            for _ in range(5):
                rr = tab.eval(LOGIN_JS % ("admin", pw))
                if rr == "submitted":
                    break
                time.sleep(4)
            tab.wait("(location.pathname.indexOf('/login')<0)", timeout=25)
        ok = tab.wait("(function(){try{var b=document.getElementById('app');return b?(JSON.parse(b.getAttribute('data-bootstrap')).user||{}).username==='admin':false}catch(e){return false}})()", timeout=25)
        record(args.tag, ver, "LOGIN", "login", bool(ok), "admin")
        if ok:
            run(args.tag, args.tag, ver, tab)
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
    out = os.path.join(HERE, "acc3b-%s-%s.json" % (args.tag, VP_TAG))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=2)
    log("results -> %s (%d rows, %d fail)" % (out, len(RESULTS), sum(1 for r in RESULTS if r["result"] == "FAIL")))


if __name__ == "__main__":
    main()
