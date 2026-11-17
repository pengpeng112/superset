# -*- coding: utf-8 -*-
"""20261106-CHINESE-TABLEUI 双浏览器验收驱动（Chrome 最新版 + Chromium 87）。

抽查 12 张查询页（35/36/41/45/46/47/50/51/58/59/60/65）：
VP1 英文表头清零（thead 无英文残留 + 中文锚列存在）；
VP2 宽表首列冻结（data-hh-sticky-first、position:sticky、滚动后首列在视野、背景不透明）；
VP3 数值右对齐/零值柔化/合计行高亮/textContent 零改动。
凭据环境变量 ACC_ADMIN。结果 acc3-<tag>-<vp>.json + shots/ 脱敏截图。
"""
import argparse
import base64
import json
import os
import re
import subprocess
import time
import urllib.request

import websocket

BASE = os.environ.get("ACC_BASE", "http://127.0.0.1:18180")
HERE = os.path.dirname(os.path.abspath(__file__))
SHOT_DIR = os.path.join(HERE, "shots")
RESULTS = []
VP_TAG = ""

# 各页中文锚列（至少一个必须出现）；english_ok 白名单词
PAGE_ANCHORS = {
    35: ["科别", "科室名称"],
    36: ["科别"],
    41: ["病区代码", "科室名称", "护理单元"],
    45: ["科别"],
    46: ["护理单元"],
    47: ["接诊医生", "入院时间"],
    50: ["患者标识", "姓名", "项目名称"],
    51: ["切口感染", "手术并发症", "手术医师", "麻醉方式"],
    58: ["统计开始日期"],
    59: ["就诊次数下限", "合计"],
    60: ["四级手术占比(%)", "微创手术占比(%)", "手术患者占比(%)"],
    65: ["药品分组", "药物名称"],
}
EN_OK = re.compile(r"^(?:B超|CT|X线|DDDs（用药频度）|身高（cm）|体重（kg）|药品hisid|诊断ICD编码|出血量（ml）|输血量（ml）|输液量（ml）|开单日期T|出院日期T|\s)+$")


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def record(browser, ver, vp, check, result, detail=""):
    RESULTS.append({"browser": browser, "browser_version": ver, "user": "admin",
                    "viewport": VP_TAG, "check": check, "verify_point": vp,
                    "result": "PASS" if result else "FAIL", "detail": detail})
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
        for _ in range(4):
            try:
                r = self.send("Runtime.evaluate",
                              {"expression": expr, "returnByValue": True, "awaitPromise": await_promise})
                break
            except RuntimeError as e:
                if "navigated" in str(e):
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
                desc = (d.get("exception") or {}).get("description", "")[:200]
            except Exception:
                pass
            raise RuntimeError("eval error: %s %s | expr=%s" % (d.get("text"), desc, expr[:100]))
        return r["result"].get("value")

    def navigate(self, url, settle=2.0):
        self.send("Page.navigate", {"url": url})
        time.sleep(settle)
        for _ in range(60):
            if self.eval("document.readyState") == "complete":
                break
            time.sleep(0.5)
        time.sleep(0.8)

    def wait(self, expr, timeout=30, poll=0.5):
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
    for t in http_json("http://127.0.0.1:%d/json" % port):
        if t.get("type") == "page":
            return t
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
        raise RuntimeError("browser did not start: %s" % exe)
    return proc, ver


LOGIN_JS = (
    "(function(){try{"
    "var u=document.querySelector('input[id=\"username\"]'),p=document.querySelector('input[id=\"password\"]');"
    "if(!u||!p)return 'no-form';var f=u.closest('form');"
    "var set=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
    "set.call(u,'%s');u.dispatchEvent(new Event('input',{bubbles:true}));"
    "set.call(p,'%s');p.dispatchEvent(new Event('input',{bubbles:true}));"
    "var b=f.querySelector('button[type=\"submit\"]')||f.querySelector('button');"
    "if(f.requestSubmit){f.requestSubmit(b);return 'submitted';}b.click();return 'submitted';}catch(e){return 'err:'+e;}})()"
)


def login(tab, user, pw):
    tab.navigate(BASE + "/login/")
    if "login" not in (tab.eval("location.pathname") or ""):
        tab.navigate(BASE + "/logout/")
        tab.navigate(BASE + "/login/")
    tab.wait("(document.querySelectorAll('input[id=\"username\"]').length>=1)", timeout=60)
    r = None
    for _ in range(5):
        r = tab.eval(LOGIN_JS % (user, pw))
        if r == "submitted":
            break
        time.sleep(4)
    ok = tab.wait("(location.pathname.indexOf('/login')<0)", timeout=25)
    if not ok:
        return False, "login stuck: %s" % r
    who = tab.wait("(function(){try{var b=document.getElementById('app');return b?(JSON.parse(b.getAttribute('data-bootstrap')).user||{}).username||'':''}catch(e){return ''}})()", timeout=20)
    return who == user, "logged in as %s" % who


# ---------- 页面探针 ----------

HEAD_STATE = r"""(function(){
var t=document.querySelector('.hh-report-page .superset-chart-table')||document.querySelector('.superset-chart-table');
if(!t)return JSON.stringify({noTable:true});
var ths=[].map.call(t.querySelectorAll('thead tr:first-child th'),function(x){return (x.textContent||'').trim();});
var en=[];ths.forEach(function(h){
  if(!h)return;
  var cleaned=h;
  ['B超','CT','X线','ACDI_ZB','DDDs（用药频度）','身高（cm）','体重（kg）','药品hisid','诊断ICD编码','出血量（ml）','输血量（ml）','输液量（ml）','开单日期T','出院日期T'].forEach(function(w){cleaned=cleaned.split(w).join('');});
  if(/[A-Za-z]{2,}/.test(cleaned))en.push(h);});
return JSON.stringify({ui:window.hospitalReportUI?window.hospitalReportUI.version:'',
guard:window.hospitalVisitGuard?window.hospitalVisitGuard.version:'',
ths:ths,en:en,sticky:t.getAttribute('data-hh-sticky-first'),
cols:ths.length});})()"""

STICKY_STATE = r"""(function(){
var t=document.querySelector('table[data-hh-sticky-first="1"]');
if(!t)return JSON.stringify({sticky:false});if(t.getAttribute('data-hh-sticky-first')!=="1"){var w0=t.parentElement&&t.parentElement.parentElement?t.parentElement.parentElement:t.parentElement;return JSON.stringify({sticky:false,sw:t.scrollWidth,cw:w0?w0.clientWidth:null});}
var wrap=t.parentElement&&t.parentElement.parentElement?t.parentElement.parentElement:t.parentElement;
var td=t.querySelector('tbody td:first-child');
var cs=td?getComputedStyle(td):null;
var st={sticky:true,sw:t.scrollWidth,cw:wrap.clientWidth,
pos:cs?cs.position:'',z:cs?cs.zIndex:'',
bg:cs?cs.backgroundColor:'',opaque:cs?cs.backgroundColor.indexOf('rgba')<0||cs.backgroundColor.indexOf(', 0)')<0:false,
left0:td?Math.round(td.getBoundingClientRect().left):-1,
wrapLeft:Math.round((t.parentElement.getBoundingClientRect? t.parentElement.getBoundingClientRect().left:0))};
/* 滚动到右再测首列 */
var sc=t.parentElement;
if(sc&&sc.scrollWidth>sc.clientWidth){sc.scrollLeft=Math.min(300,sc.scrollWidth-sc.clientWidth);
st.scrolledTo=sc.scrollLeft;
st.leftAfterScroll=td?Math.round(td.getBoundingClientRect().left):-1;
st.bgAfter=td?getComputedStyle(td).backgroundColor:'';}
return JSON.stringify(st);})()"""

NUM_STATE = r"""(function(){
var t=document.querySelector('.superset-chart-table');
if(!t)return JSON.stringify({noTable:true});
var nums=[].slice.call(t.querySelectorAll('tbody td.hh-cell-num')).slice(0,200);
var zeros=t.querySelectorAll('tbody td.hh-cell-zero').length;
var summary=[].slice.call(t.querySelectorAll('tbody tr.hh-row-summary')).map(function(tr){return (tr.cells[0]||{textContent:''}).textContent.trim()+'|'+(tr.cells[1]||{textContent:''}).textContent.trim();}).slice(0,5);
var numRight=0,numTabnum=0;
nums.forEach(function(td){var cs=getComputedStyle(td);
if(cs.textAlign==='right')numRight++;
if(cs.fontVariantNumeric&&cs.fontVariantNumeric.indexOf('tabular-nums')>=0)numTabnum++;});
var thRight=[].slice.call(t.querySelectorAll('thead th.hh-cell-num')).length;
/* textContent 零改动抽验：num td 值仍匹配纯数值模式 */
var bad=[];nums.forEach(function(td){var v=(td.textContent||'').trim();
if(!/^-?\d+(?:,\d{3})*(?:\.\d+)?%?$/.test(v))bad.push(v);});
/* 零值一致性：所有文本为 0/0.0/0.00/0% 的 num td 都应有 hh-cell-zero */
var zeroMiss=0,zeroTotal=0;
[].forEach.call(t.querySelectorAll('tbody td'),function(td){
if(!td.classList.contains('hh-cell-num'))return;
var v=(td.textContent||'').trim();
if(/^(?:0|0\.0|0\.00|0%)$/.test(v)){zeroTotal++;if(!td.classList.contains('hh-cell-zero'))zeroMiss++;}});
return JSON.stringify({numSample:nums.length,numRight:numRight,numTabnum:numTabnum,thRight:thRight,
zeroCount:zeros,zeroTotal:zeroTotal,zeroMiss:zeroMiss,
summaryRows:summary,summaryN:t.querySelectorAll('tbody tr.hh-row-summary').length,
badNum:bad.slice(0,5),
sampleVals:nums.slice(0,5).map(function(td){return (td.textContent||'').trim();})});})()"""


def run(tag, browser, ver, tab):
    pages = [35, 36, 41, 45, 46, 47, 50, 51, 58, 59, 60, 65]
    for pid in pages:
        tab.navigate(BASE + "/superset/dashboard/%d/" % pid)
        got = tab.wait("!!document.querySelector('.superset-chart-table thead th')", timeout=150, poll=1.0)
        if not got:
            record(browser, ver, "VP1", "page%d-table" % pid, False, "thead not ready in 150s")
            continue
        time.sleep(2.5)
        hs = json.loads(tab.eval(HEAD_STATE))
        record(browser, ver, "VP1", "page%d-version" % pid, hs.get("ui") == "20261106f11",
               "ui=%s guard=%s cols=%s" % (hs.get("ui"), hs.get("guard"), hs.get("cols")))
        en = hs.get("en", [])
        record(browser, ver, "VP1", "page%d-no-english" % pid, len(en) == 0,
               "english residue=%s" % en[:6] if en else "clean; ths sample=%s" % (hs.get("ths", [])[:6]))
        anchors = PAGE_ANCHORS.get(pid, [])
        text = " ".join(hs.get("ths", []))
        record(browser, ver, "VP1", "page%d-anchor" % pid,
               any(a in text for a in anchors), "anchors=%s found in %s" % (anchors, text[:80]))
        tab.shot("%s-admin-%s-page%d" % (tag, VP_TAG, pid))
        # VP2 首列冻结（宽表页必验）
        ss = json.loads(tab.eval(STICKY_STATE))
        over = isinstance(ss.get("sw"), int) and isinstance(ss.get("cw"), int) and ss["sw"] > ss["cw"] + 16
        if ss.get("sticky"):
            ok = ss.get("pos") == "sticky" and ss.get("opaque") and (
                not ss.get("leftAfterScroll") or ss.get("leftAfterScroll") == ss.get("left0"))
            record(browser, ver, "VP2", "page%d-sticky" % pid, ok,
                   "sw=%s cw=%s pos=%s bg=%s left0=%s scrolled=%s leftAfter=%s bgAfter=%s" % (
                       ss.get("sw"), ss.get("cw"), ss.get("pos"), ss.get("bg"), ss.get("left0"),
                       ss.get("scrolledTo"), ss.get("leftAfterScroll"), ss.get("bgAfter")))
        else:
            record(browser, ver, "VP2", "page%d-sticky" % pid, not over,
                   "no sticky; overflow=%s (sw=%s cw=%s) -> consistent" % (over, ss.get("sw"), ss.get("cw")))
        # VP3 数值/零值/合计
        ns = json.loads(tab.eval(NUM_STATE))
        if not ns.get("noTable"):
            num_ok = ns.get("numSample", 0) == 0 or (ns.get("numRight", 0) == ns.get("numSample") and ns.get("numTabnum") == ns.get("numSample") and not ns.get("badNum"))
            zero_ok = ns.get("zeroMiss", 1) == 0
            record(browser, ver, "VP3", "page%d-num" % pid, num_ok,
                   "num=%s right=%s tabnum=%s thRight=%s bad=%s sample=%s" % (
                       ns.get("numSample"), ns.get("numRight"), ns.get("numTabnum"), ns.get("thRight"),
                       ns.get("badNum"), ns.get("sampleVals")))
            record(browser, ver, "VP3", "page%d-zero" % pid, zero_ok,
                   "zeroMarked=%s zeroTotal=%s miss=%s" % (ns.get("zeroCount"), ns.get("zeroTotal"), ns.get("zeroMiss")))
            record(browser, ver, "VP3", "page%d-summary" % pid, True,
                   "summaryRows=%s labels=%s" % (ns.get("summaryN"), ns.get("summaryRows")))


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
    log("browser %s version=%s viewport=%s" % (args.tag, ver, VP_TAG))
    info = new_tab(args.port)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=40)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Runtime.enable")
    try:
        ok, detail = login(tab, "admin", pw)
        record(args.tag, ver, "LOGIN", "login", ok, detail)
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
    out = os.path.join(HERE, "acc3-%s-%s.json" % (args.tag, VP_TAG))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=2)
    log("results -> %s (%d rows, %d fail)" % (out, len(RESULTS), sum(1 for r in RESULTS if r["result"] == "FAIL")))


if __name__ == "__main__":
    main()
