# -*- coding: utf-8 -*-
"""20261108-FINAL-CLOSEOUT 任务2验收驱动：改密入口 / user_info 中文化与高亮 / 未授权中文提示卡。
Chrome 最新 + Chromium 87 × 1920/1366；admin + 003158。结果 acc6-<tag>-<vp>.json + 脱敏截图 shots/。
凭据环境变量 ACC_ADMIN / ACC_GUEST。"""
import argparse
import base64
import json
import os
import subprocess
import time
import urllib.request

import websocket

BASE = os.environ.get("ACC_BASE", "http://127.0.0.1:18180")
RESULTS = []
SHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")
os.makedirs(SHOT_DIR, exist_ok=True)
USERS = {}
VP_TAG = ""


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def record(browser, ver, user, check, result, detail=""):
    RESULTS.append({"browser": browser, "browser_version": ver, "user": user,
                    "viewport": VP_TAG, "check": check,
                    "result": "PASS" if result else "FAIL", "detail": detail})
    log(("PASS " if result else "FAIL ") + check + " | " + detail[:170])


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

    def send(self, method, params=None, timeout=45):
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

    def navigate(self, url, settle=2.5):
        self.send("Page.navigate", {"url": url})
        time.sleep(settle)
        for _ in range(50):
            if self.eval("document.readyState") == "complete":
                break
            time.sleep(0.5)
        time.sleep(1.0)

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
        self.eval("(function(){var s=document.getElementById('hh-acc-mask');if(!s){s=document.createElement('style');s.id='hh-acc-mask';s.textContent='tbody{visibility:hidden!important}';document.head.appendChild(s);}})()")
        time.sleep(0.3)
        r = self.send("Page.captureScreenshot", {"format": "png"})
        path = os.path.join(SHOT_DIR, name + ".png")
        with open(path, "wb") as f:
            f.write(base64.b64decode(r["data"]))
        return path


def launch(exe, port, profile, w, h):
    proc = subprocess.Popen([
        exe, "--remote-debugging-port=%d" % port, "--user-data-dir=%s" % profile,
        "--no-first-run", "--no-default-browser-check", "--disable-session-crashed-bubble",
        "--hide-crash-restore-bubble", "--window-size=%d,%d" % (w, h), "--window-position=30,30",
        "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            ver = http_json("http://127.0.0.1:%d/json/version" % port).get("Browser", "")
            if ver:
                return proc, ver
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("browser did not start")


LOGIN_JS = (
    "(function(){try{"
    "var u=document.querySelector('input[id=\"username\"],input[name=\"username\"]');"
    "var p=document.querySelector('input[id=\"password\"],input[name=\"password\"]');"
    "if(!u||!p)return 'no-form';var f=u.closest('form');"
    "var set=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
    "set.call(u,'%s');u.dispatchEvent(new Event('input',{bubbles:true}));"
    "set.call(p,'%s');p.dispatchEvent(new Event('input',{bubbles:true}));"
    "if(f.requestSubmit){f.requestSubmit();return 'submitted';}return 'no-btn';}catch(e){return 'err:'+e;}})()"
)


def login(tab, user, pw):
    tab.navigate(BASE + "/login/")
    if "login" not in (tab.eval("location.pathname") or ""):
        who = tab.eval("(document.getElementById('app')&&JSON.parse(document.getElementById('app').getAttribute('data-bootstrap')||'{}').user||{}).username||''")
        if who == user:
            return True, "already"
        tab.navigate(BASE + "/logout/")
        tab.navigate(BASE + "/login/")
    tab.wait("document.querySelectorAll('input[id=\"username\"]').length>=1", timeout=60)
    r = tab.eval(LOGIN_JS % (user, pw))
    ok = tab.wait("(location.pathname.indexOf('/login')<0)", timeout=25)
    who = tab.eval("(document.getElementById('app')&&JSON.parse(document.getElementById('app').getAttribute('data-bootstrap')||'{}').user||{}).username||''")
    return bool(ok and who == user), "r=%s who=%s" % (r, who)


def set_input_js(selector, value):
    return ("(function(){var i=document.querySelector('%s');if(!i)return 'nofield';"
            "var set=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
            "set.call(i,'%s');i.dispatchEvent(new Event('input',{bubbles:true}));return 'ok';})()" % (selector, value))


HOME_PWD_STATE = """(function(){
  var b=document.querySelector('#hospital-home-hint a.hh-home-pwd-btn');
  if(!b)return JSON.stringify({exists:false});
  var st=getComputedStyle(b);
  return JSON.stringify({exists:true,text:b.textContent.trim(),href:b.getAttribute('href'),
    h:st.height,bg:st.backgroundColor,border:st.borderTopColor,color:st.color,
    afterPrimary:!!(b.previousElementSibling&&b.previousElementSibling.classList.contains('hh-home-primary'))});
})()"""

USERINFO_STATE = """(function(){
  var crumb=document.getElementById('hh-acct-crumb');
  var back=crumb&&crumb.querySelector('a');
  var ths=[].map.call(document.querySelectorAll('th,label'),function(e){return e.textContent.replace(/\\s+/g,'').trim()});
  var btn=[].slice.call(document.querySelectorAll('button')).filter(function(b){return b.textContent.replace(/\\s+/g,'')==='修改登录密码'})[0];
  var bst=btn?getComputedStyle(btn):null;
  return JSON.stringify({
    crumb:!!crumb, backHref:back?back.getAttribute('href'):'', backText:back?back.textContent.trim():'',
    cur:crumb?crumb.querySelector('.hh-acct-cur').textContent.trim():'',
    hasLoginId:ths.indexOf('登录工号')>=0, hasStatus:ths.indexOf('账号状态')>=0,
    hasRole:ths.indexOf('所属科室与角色')>=0, hasCount:ths.indexOf('登录次数')>=0,
    hasName:ths.indexOf('姓名')>=0, hasSurname:ths.indexOf('工号/姓氏')>=0,
    legacyUser:ths.indexOf('用户名')>=0, legacyCount:ths.indexOf('计数')>=0,
    legacyActive:ths.indexOf('是否启用')>=0,
    btn:!!btn, btnPrimary:bst?bst.backgroundColor:'', adminBg:document.documentElement.classList.contains('hh-admin-page')
  });})()"""

DENIED_STATE = """(function(){
  var card=document.getElementById('hh-denied-card');
  var err=document.querySelector('.error-page-content[data-hh-denied]');
  var escon=(function(){if(!err)return null;return getComputedStyle(err).display==='none'})();
  return JSON.stringify({
    card:!!card,
    title:card?(card.querySelector('.hh-denied-title')||{}).textContent:'',
    text:card?(card.querySelector('.hh-denied-text')||{}).textContent.slice(0,60):'',
    btnText:card?(card.querySelector('.hh-denied-btn')||{}).textContent:'',
    btnHref:card?(card.querySelector('.hh-denied-btn')||{}).getAttribute('href'):'',
    errHidden:escon
  });})()"""


def run_flow(tab, tag, ver, user, is_admin):
    # ---- 1) 首页改密入口 ----
    tab.navigate(BASE + "/superset/welcome/")
    tab.wait("document.querySelector('#hospital-home-hint')&&document.querySelector('#hospital-home-hint .hh-home-pwd-btn')", timeout=30)
    st = json.loads(tab.eval(HOME_PWD_STATE))
    ok = (st.get("exists") and st.get("text") == "修改密码" and st.get("href") == "/user_info/"
          and st.get("h") == "32px" and st.get("bg") in ("rgb(255, 255, 255)",)
          and st.get("border") in ("rgb(217, 225, 234)",) and st.get("color") in ("rgb(68, 83, 106)",))
    record(tag, ver, user, "home-pwd-btn", ok, json.dumps(st, ensure_ascii=False)[:220])
    tab.shot("%s-%s-home-pwdbtn" % (tag, user))
    # 点击进入个人中心
    tab.eval("(document.querySelector('#hospital-home-hint a.hh-home-pwd-btn')||{}).click && document.querySelector('#hospital-home-hint a.hh-home-pwd-btn').click()")
    tab.wait("location.pathname.indexOf('/user_info')===0", timeout=25)

    # ---- 2) user_info 中文化 + 高亮 ----
    tab.wait("document.getElementById('hh-acct-crumb')", timeout=30)
    us = json.loads(tab.eval(USERINFO_STATE))
    ok2 = (us["crumb"] and us["backHref"] == "/superset/welcome/" and "返回工作台" in us["backText"]
           and us["cur"] == "账号基本信息" and us["hasLoginId"] and us["hasStatus"] and us["hasRole"]
           and us["hasCount"] and us["hasName"] and us["hasSurname"]
           and not (us["legacyUser"] or us["legacyCount"] or us["legacyActive"])
           and us["btn"] and us["btnPrimary"] == "rgb(22, 119, 200)")
    record(tag, ver, user, "user-info-zh", ok2, json.dumps(us, ensure_ascii=False)[:260])
    tab.shot("%s-%s-userinfo" % (tag, user))

    # ---- 3) 改密弹窗打开（仅点开验证 UI，不实际改密；真实改密在专项轮） ----
    tab.eval("(function(){var b=[].slice.call(document.querySelectorAll('button')).filter(function(x){return x.textContent.replace(/\\s+/g,'')==='修改登录密码'})[0];if(b){b.click();return 'clicked'}return 'missing'})()")
    modal = tab.wait("(function(){var m=document.querySelector('.ant-modal');return m&&m.textContent.indexOf('密码')>=0})()", timeout=15)
    fields = tab.eval("(function(){var p=[].slice.call(document.querySelectorAll('.ant-modal input')).filter(function(i){return i.type==='password'}).length;var save=[].slice.call(document.querySelectorAll('.ant-modal button')).filter(function(b){return b.textContent.replace(/\\s+/g,'')==='保存'}).length;return JSON.stringify({pw:p,save:save})})()")
    mst = json.loads(fields)
    record(tag, ver, user, "pwd-modal", bool(modal) and mst["pw"] >= 2 and mst["save"] >= 1, fields)
    tab.shot("%s-%s-pwdmodal" % (tag, user))
    tab.eval("(function(){var b=[].slice.call(document.querySelectorAll('.ant-modal button')).filter(function(x){return x.textContent.replace(/\\s+/g,'')==='取消'})[0];if(b)b.click();return 1})()")
    time.sleep(1)

    # ---- 4) 未授权中文提示卡（仅普通员工） ----
    if not is_admin:
        for did, note in [(50, "surgery"), (47, "clinic"), (61, "kyb")]:
            tab.navigate(BASE + "/superset/dashboard/%d/" % did)
            tab.wait("document.getElementById('hh-denied-card')||document.querySelector('.superset-chart-table')", timeout=30)
            ds = json.loads(tab.eval(DENIED_STATE))
            leak = tab.eval("!!document.querySelector('.superset-chart-table')")
            okd = (ds["card"] and ds["title"] == "专项明细权限受控" and ds["btnText"] == "返回报表目录"
                   and ds["btnHref"] == "/superset/dashboard/34/" and ds["errHidden"] and not leak)
            record(tag, ver, user, "denied-card-%d" % did, okd, json.dumps(ds, ensure_ascii=False)[:200] + (" LEAK" if leak else ""))
            if did == 50:
                tab.shot("%s-%s-denied%d" % (tag, user, did))
        # 无关看板号错误页保持原生
        tab.navigate(BASE + "/superset/dashboard/9999/")
        time.sleep(3)
        raw = tab.eval("(function(){return JSON.stringify({card:!!document.getElementById('hh-denied-card'),err:!!document.querySelector('.error-page-content'),errVisible:(function(){var e=document.querySelector('.error-page-content');return e?getComputedStyle(e).display!=='none':false})()})})()")
        rs = json.loads(raw)
        record(tag, ver, user, "unknown-dash-raw", (not rs["card"]) and rs["errVisible"], raw)
    else:
        # Admin 直开 50 应正常出查询页（不受提示卡影响）
        tab.navigate(BASE + "/superset/dashboard/50/")
        got = tab.wait("!!(document.querySelector('.superset-chart-table')||document.getElementById('hh-denied-card'))", timeout=60)
        admin_ok = tab.eval("(function(){return JSON.stringify({table:!!document.querySelector('.superset-chart-table'),card:!!document.getElementById('hh-denied-card')})})()")
        a = json.loads(admin_ok)
        record(tag, ver, user, "admin-50-normal", a["table"] and not a["card"], admin_ok)

    # ---- 5) 回归：查询页工具条/日历仍在 ----
    tab.navigate(BASE + "/superset/dashboard/36/")
    tab.wait("document.querySelector('.hh-query-toolbar')||document.querySelector('.hdt-picker')||document.querySelector('.superset-chart-table')", timeout=60)
    reg = tab.eval("(function(){return JSON.stringify({toolbar:!!document.querySelector('.hh-query-toolbar'),cal:!!document.querySelector('.hdt-picker[data-filter-id]'),table:!!document.querySelector('.superset-chart-table'),crumb:!!document.getElementById('hh-crumb')})})()")
    r = json.loads(reg)
    record(tag, ver, user, "regression-36", r["toolbar"] and r["cal"] and r["crumb"], reg)


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
    USERS.update({"admin": os.environ["ACC_ADMIN"], "003158": os.environ["ACC_GUEST"]})
    profile = os.path.abspath(os.path.join(SHOT_DIR, "..", "profile-acc6-%s-%s" % (args.tag, VP_TAG)))
    proc, ver = launch(args.exe, args.port, profile, args.w, args.h)
    log("browser %s %s viewport=%s" % (args.tag, ver, VP_TAG))
    info = new_tab(args.port)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=30)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Runtime.enable")
    try:
        for user in ["admin", "003158"]:
            try:
                ok, detail = login(tab, user, USERS[user])
                record(args.tag, ver, user, "login", ok, detail)
                if ok:
                    run_flow(tab, args.tag, ver, user, user == "admin")
            except Exception as e:
                record(args.tag, ver, user, "driver-error", False, repr(e)[:200])
            finally:
                try:
                    tab.navigate(BASE + "/logout/")
                except Exception:
                    pass
    finally:
        ws.close()
        proc.terminate()
        time.sleep(1.5)
        proc.kill()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "acc6-%s-%s.json" % (args.tag, VP_TAG))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=2)
    log("results -> %s (%d rows, %d fail)" % (out, len(RESULTS), sum(1 for r in RESULTS if r["result"] == "FAIL")))


if __name__ == "__main__":
    main()
