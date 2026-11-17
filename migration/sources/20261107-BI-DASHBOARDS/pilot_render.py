# -*- coding: utf-8 -*-
"""T3 试点浏览器核验：打开看板，读 Redux 各图状态与 queriesResponse 数据。用法：python pilot_render.py <dashboard_id>"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import urllib.request

import websocket

BASE = "http://127.0.0.1:18180"
HERE = os.path.dirname(os.path.abspath(__file__))

STATE = r"""(function(){
function dig(){var e=document.querySelector('[data-test="grid-content"]');if(!e)return null;
var k=Object.keys(e).filter(function(k){return k.indexOf('__reactFiber')===0;})[0];
var f=e[k];while(f){var p=f.memoizedProps,s=p&&(p.store||(p.value&&p.value.store));if(s&&s.getState)return s;f=f.return;}return null;}
var st=dig&&dig();if(!st)return JSON.stringify({noStore:true});
var charts=st.getState().charts;var out={total:0,rendered:0,loading:0,other:0,errors:[],info:{}};
Object.keys(charts).forEach(function(id){var c=charts[id];out.total++;
var stx=c.chartStatus;out.info[id]={status:stx};
if(stx==='rendered'||stx==='success')out.rendered++;
else if(stx==='loading')out.loading++;else out.other++;
var r=c.queriesResponse&&c.queriesResponse[0];
if(r&&r.error)out.errors.push({id:id,err:String(r.error).slice(0,120)});
if(r)out.info[id].rowcount=(typeof r.rowcount==='number')?r.rowcount:(r.data||[]).length;});
out.errCards=document.querySelectorAll('.ant-alert-error').length;
return JSON.stringify(out);})()"""

DATA = r"""(function(){
function dig(){var e=document.querySelector('[data-test="grid-content"]');if(!e)return null;
var k=Object.keys(e).filter(function(k){return k.indexOf('__reactFiber')===0;})[0];
var f=e[k];while(f){var p=f.memoizedProps,s=p&&(p.store||(p.value&&p.value.store));if(s&&s.getState)return s;f=f.return;}return null;}
var st=dig&&dig();if(!st)return '{}';
var charts=st.getState().charts;var out={};
Object.keys(charts).forEach(function(id){var c=charts[id];var r=c.queriesResponse&&c.queriesResponse[0];
if(r&&r.data)out[id]={rows:r.data.length,head:JSON.stringify(r.data.slice(0,4)).slice(0,300)};});
return JSON.stringify(out);})()"""


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


LOGIN_JS = ("(function(){try{var u=document.querySelector('input[id=\"username\"]'),"
            "p=document.querySelector('input[id=\"password\"]');if(!u||!p)return 'no-form';"
            "var f=u.closest('form');var set=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
            "set.call(u,'%s');u.dispatchEvent(new Event('input',{bubbles:true}));"
            "set.call(p,'%s');p.dispatchEvent(new Event('input',{bubbles:true}));"
            "var b=f.querySelector('button[type=\"submit\"]')||f.querySelector('button');"
            "if(f.requestSubmit){f.requestSubmit(b);return 'submitted';}b.click();return 'submitted';}"
            "catch(e){return 'err:'+e;}})()")


def http_json(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    did = sys.argv[1] if len(sys.argv) > 1 else "72"
    exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    port = 18923
    profile = os.path.join(HERE, "profile-pilot")
    proc = subprocess.Popen([exe, "--remote-debugging-port=%d" % port, "--user-data-dir=%s" % profile,
                             "--no-first-run", "--no-default-browser-check", "--window-size=1600,900", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                http_json("http://127.0.0.1:%d/json/version" % port)
                break
            except Exception:
                time.sleep(0.5)
        info = None
        for m in ("PUT", "GET"):
            try:
                req = urllib.request.Request("http://127.0.0.1:%d/json/new?about:blank" % port, method=m)
                with urllib.request.urlopen(req, timeout=10) as r:
                    info = json.loads(r.read().decode("utf-8"))
                break
            except Exception:
                continue
        ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=60)
        tab = Tab(ws)
        tab.send("Page.enable")
        tab.navigate(BASE + "/login/")
        tab.wait("document.querySelectorAll('input[id=\"username\"]').length>=1", timeout=60)
        tab.eval(LOGIN_JS % ("admin", os.environ["ACC_ADMIN"]))
        tab.wait("(location.pathname.indexOf('/login')<0)", timeout=25)
        t0 = time.time()
        tab.navigate(BASE + "/superset/dashboard/%s/" % did)
        # 等全部渲染
        deadline = time.time() + 60
        st = "{}"
        while time.time() < deadline:
            st = tab.eval(STATE)
            d = json.loads(st)
            if d.get("total") and d.get("loading", 1) == 0 and d.get("rendered") == d.get("total"):
                break
            time.sleep(0.5)
        d = json.loads(st)
        print("STATE:", json.dumps(d, ensure_ascii=False)[:1200])
        print("wall=%.1fs" % (time.time() - t0))
        time.sleep(1)
        print("DATA:", tab.eval(DATA)[:2500])
        tab.eval("(function(){fetch('/logout/',{credentials:'same-origin'});return 1;})()")
        ws.close()
    finally:
        proc.terminate()
        time.sleep(1)
        proc.kill()


if __name__ == "__main__":
    main()
