# -*- coding: utf-8 -*-
"""对比两看板 Redux 关键切片。--a=62 --b=74"""
import json
import os
import subprocess
import sys
import time
import urllib.request

sys.stdout = __import__("io").TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import websocket

BASE = "http://127.0.0.1:18180"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pilot_render import LOGIN_JS

DA, DB = "62", "74"
for a in sys.argv:
    if a.startswith("--a="):
        DA = a.split("=", 1)[1]
    if a.startswith("--b="):
        DB = a.split("=", 1)[1]

DUMP = r"""(function(){
function dig(){var e=document.querySelector('[data-test="grid-content"]');if(!e)return null;
var k=Object.keys(e).filter(function(k){return k.indexOf('__reactFiber')===0;})[0];
var f=e[k];while(f){var p=f.memoizedProps,s=p&&(p.store||(p.value&&p.value.store));if(s&&s.getState)return s;f=f.return;}return null;}
var st=dig();if(!st)return 'nostore';
var s=st.getState();
return JSON.stringify({slices:Object.keys(s), dataMask:JSON.stringify(s.dataMask).slice(0,500),
  nativeFilters:JSON.stringify(s.nativeFilters||{}).slice(0,700),
  charts:JSON.stringify(Object.keys(s.charts||{}))});})()"""

exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
port = 18956
proc = subprocess.Popen([exe, "--remote-debugging-port=%d" % port, "--user-data-dir=%s" % os.path.abspath("probe-redux"),
                         "--no-first-run", "--no-default-browser-check", "--window-size=1600,900", "about:blank"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
mid = 0


def send(m, p=None, t=120):
    global mid
    mid += 1
    i = mid
    ws.send(json.dumps({"id": i, "method": m, "params": p or {}}))
    dl = time.time() + t
    while time.time() < dl:
        ws.settimeout(max(0.5, dl - time.time()))
        msg = json.loads(ws.recv())
        if msg.get("id") == i:
            return msg.get("result", {})
    raise TimeoutError(m)


def ev(js):
    r = send("Runtime.evaluate", {"expression": js, "returnByValue": True})
    if r.get("exceptionDetails"):
        return "JSEXC: " + ((r["exceptionDetails"].get("exception") or {}).get("description") or "")[:250]
    return r.get("result", {}).get("value")


try:
    for _ in range(40):
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=5)
            break
        except Exception:
            time.sleep(0.5)
    req = urllib.request.Request("http://127.0.0.1:%d/json/new?about:blank" % port, method="PUT")
    info = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=60)
    send("Page.enable")
    send("Page.navigate", {"url": BASE + "/login/"})
    time.sleep(3)
    for _ in range(15):
        if "/login" not in (ev("location.pathname") or ""):
            break
        try:
            ev(LOGIN_JS % ("admin", os.environ["ACC_ADMIN"]))
        except Exception:
            pass
        time.sleep(2)
    for d in (DA, DB):
        send("Page.navigate", {"url": BASE + "/superset/dashboard/%s/" % d})
        for i in range(20):
            time.sleep(3)
            if ev("document.querySelectorAll('[data-test=\"filter-bar__apply-button\"]').length"):
                break
        time.sleep(3)
        print("== d%s ==" % d)
        print(str(ev(DUMP))[:1600])
    ws.close()
finally:
    proc.terminate()
    time.sleep(1)
    proc.kill()
