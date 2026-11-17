# -*- coding: utf-8 -*-
"""20261108-FINAL-CLOSEOUT 任务2前置探针：dump 未授权看板页 / user_info / resetmypassword 真实 DOM。
凭据环境变量 ACC_GUEST。CDP 驱动真实浏览器（复用 20261104 acc_run.py 的 Tab 模式）。"""
import json
import os
import subprocess
import sys
import time

import websocket

BASE = os.environ.get("ACC_BASE", "http://127.0.0.1:18180")
OUT = {}


def http_json(url, method="GET"):
    import urllib.request
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


class Tab:
    def __init__(self, ws):
        self.ws = ws
        self.mid = 0

    def send(self, method, params=None, timeout=40):
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
            raise RuntimeError(str(r["exceptionDetails"])[:200])
        return r["result"].get("value")

    def navigate(self, url, settle=3.0):
        self.send("Page.navigate", {"url": url})
        time.sleep(settle)
        for _ in range(40):
            if self.eval("document.readyState") == "complete":
                break
            time.sleep(0.5)
        time.sleep(1.5)


def launch(exe, port, profile):
    proc = subprocess.Popen([
        exe, "--remote-debugging-port=%d" % port, "--user-data-dir=%s" % profile,
        "--no-first-run", "--no-default-browser-check", "--disable-session-crashed-bubble",
        "--window-size=1366,900", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            ver = http_json("http://127.0.0.1:%d/json/version" % port).get("Browser", "")
            if ver:
                return proc, ver
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("browser not started")


def login(tab, user, pw):
    tab.navigate(BASE + "/login/")
    tab.eval(
        "(function(){var u=document.querySelector('input[id=\"username\"]');"
        "var p=document.querySelector('input[id=\"password\"]');if(!u||!p)return 'no-form';"
        "var f=u.closest('form');var set=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
        "set.call(u,'%s');u.dispatchEvent(new Event('input',{bubbles:true}));"
        "set.call(p,'%s');p.dispatchEvent(new Event('input',{bubbles:true}));"
        "f.requestSubmit();return 'ok';})()" % (user, pw))
    for _ in range(30):
        time.sleep(1)
        if "/login" not in (tab.eval("location.pathname") or ""):
            return True
    return False


DUMP_JS = """(function(){
  function sel(s){var e=document.querySelector(s);return e?{tag:e.tagName,cls:e.className.toString().slice(0,120),text:(e.textContent||'').trim().slice(0,200)}:null}
  var main=document.querySelector('main')||document.querySelector('#app')||document.body;
  return JSON.stringify({
    path:location.pathname,
    title:document.title,
    bodyHead:(document.body.innerText||'').replace(/\\s+/g,' ').slice(0,500),
    alerts:[].map.call(document.querySelectorAll('.ant-alert-error,.ant-alert,[role=alert],.alert'),function(e){return e.className.toString().slice(0,80)+' || '+(e.textContent||'').trim().slice(0,160)}),
    h12:[].map.call(document.querySelectorAll('h1,h2'),function(e){return e.tagName+':'+(e.textContent||'').trim().slice(0,80)}),
    buttons:[].map.call(document.querySelectorAll('button,a.btn,.ant-btn'),function(e){return (e.textContent||'').trim().slice(0,40)}).filter(Boolean).slice(0,20),
    labels:[].map.call(document.querySelectorAll('label,th,.ant-form-item-label'),function(e){return (e.textContent||'').trim().slice(0,40)}).filter(Boolean).slice(0,30),
    tables:[].map.call(document.querySelectorAll('table'),function(t){return [].map.call(t.querySelectorAll('th'),function(h){return h.textContent.trim()}).join(',')}).slice(0,4),
    mainCls:(main.className||'').toString().slice(0,120),
    htmlCls:document.documentElement.className,
    hhAdmin:document.documentElement.classList.contains('hh-admin-page')
  });})()"""


def probe(tag, exe, port):
    proc, ver = 0, ""
    try:
        profile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile-probe-%s" % tag)
        proc, ver = launch(exe, port, profile)
        info = http_json("http://127.0.0.1:%d/json/new?about:blank" % port)
        ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=30)
        tab = Tab(ws)
        tab.send("Page.enable")
        ok = login(tab, "003158", os.environ["ACC_GUEST"])
        out = {"browser": ver, "login": ok, "pages": {}}
        for name, url in [
            ("dashboard50_denied", "/superset/dashboard/50/"),
            ("dashboard47_denied", "/superset/dashboard/47/"),
            ("user_info", "/user_info/"),
            ("resetmypassword", "/resetmypassword/form"),
        ]:
            tab.navigate(BASE + url)
            time.sleep(3)
            out["pages"][name] = json.loads(tab.eval(DUMP_JS))
        ws.close()
        OUT[tag] = out
    finally:
        if proc:
            proc.terminate(); time.sleep(1); proc.kill()


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    c87 = r"F:\python\superset\migration\tools\chromium87-r809590\chrome-win\chrome.exe"
    for tag, exe, port in [("chrome", chrome, 19222), ("c87", c87, 19223)]:
        try:
            probe(tag, exe, port)
        except Exception as e:
            OUT[tag] = {"error": repr(e)[:300]}
    with open(os.path.join(here, "probe-dom.json"), "w", encoding="utf-8") as f:
        json.dump(OUT, f, ensure_ascii=False, indent=1)
    print("saved probe-dom.json")
    for t, v in OUT.items():
        print("==", t, "==")
        print(json.dumps(v, ensure_ascii=False)[:2600])
