# -*- coding: utf-8 -*-
"""T1③ 前端修复冒烟：目录34 搜索框+入口条、slug 打开 72 的面包屑/页面类。一次性，用完即弃。"""
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


def http_json(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


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

CHECK = r"""(function(){
var md=document.querySelector('.dashboard-markdown');
var list=md?md.querySelector('ul'):null;
var wrap=document.getElementById('hh-dir-search-wrap');
var input=document.getElementById('hh-report-search');
var box=document.getElementById('hh-bi-showcase');
var cards=box?box.querySelectorAll('.hh-bi-card').length:0;
var cardH=0,bl='';
if(box&&box.querySelector('.hh-bi-card')){var el=box.querySelector('.hh-bi-card');var r=el.getBoundingClientRect();cardH=Math.round(r.height);var cs=getComputedStyle(el);bl=cs.borderLeftWidth+' '+cs.borderLeftColor;}
var order=[];
if(md){var n=md.firstElementChild;for(var i=0;i<12&&n;i++){if(n.id==='hh-dir-search-wrap')order.push('search');if(n.id==='hh-bi-showcase')order.push('showcase');if(n.tagName==='UL')order.push('ul');n=n.nextElementSibling;}}
if(!order.length&&list){var p=list.parentNode;n=p.firstElementChild;for(var i=0;i<12&&n;i++){if(n.id==='hh-dir-search-wrap')order.push('search');if(n.id==='hh-bi-showcase')order.push('showcase');if(n.tagName==='UL')order.push('ul');n=n.nextElementSibling;}}
return JSON.stringify({hasMd:!!md,search:!!wrap,input:!!input,showcase:!!box,cards:cards,cardH:cardH,borderLeft:bl,order:order.join('>'),ver:window.hospitalHomeUI?window.hospitalHomeUI.version:''});})()"""

SLUG_CHECK = r"""(function(){
var crumb=document.getElementById('hh-crumb');
var path=location.pathname;
return JSON.stringify({path:path,
 crumb:crumb?[].map.call(crumb.querySelectorAll('a,.hh-crumb-cur'),function(n){return n.textContent.trim();}).join(' / '):'',
 biPage:document.documentElement.classList.contains('hh-bi-page'),
 reportPage:document.documentElement.classList.contains('hh-report-page')});})()"""


def main():
    exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    port = 18922
    profile = os.path.join(HERE, "profile-smoke-t1")
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
        print("login ok")
        # 1) 目录 34
        tab.navigate(BASE + "/superset/dashboard/34/")
        tab.wait("!!document.querySelector('.dashboard-markdown ul')", timeout=40)
        time.sleep(2.5)
        print("dir34:", tab.eval(CHECK))
        # 2) slug 打开 72
        tab.navigate(BASE + "/superset/dashboard/bi-overview/")
        tab.wait("!!document.getElementById('hh-crumb')", timeout=40)
        time.sleep(1.5)
        print("slug72:", tab.eval(SLUG_CHECK))
        tab.eval("(function(){fetch('/logout/',{credentials:'same-origin'});return 1;})()")
        ws.close()
    finally:
        proc.terminate()
        time.sleep(1)
        proc.kill()


if __name__ == "__main__":
    main()
