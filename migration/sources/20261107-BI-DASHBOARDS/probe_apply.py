# -*- coding: utf-8 -*-
"""统一联动探针：--dash=N [--range='a : b'] 匹配 bridge→调用→apply 状态→masks。"""
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

DASH = "72"
RANGE = "2026-09-01 : 2026-10-01"
for a in sys.argv:
    if a.startswith("--dash="):
        DASH = a.split("=", 1)[1]
    if a.startswith("--range="):
        RANGE = a.split("=", 1)[1]

exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
port = 18949
proc = subprocess.Popen([exe, "--remote-debugging-port=%d" % port, "--user-data-dir=%s" % os.path.abspath("probe-prof"),
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
        return "JSEXC: " + ((r["exceptionDetails"].get("exception") or {}).get("description") or "")[:200]
    return r.get("result", {}).get("value")


CALL = r"""(function(){
var b=document.querySelector('[data-test="time-range-trigger"][name]');if(!b)return 'no-trigger';
var k=Object.keys(b).find(function(k){return k.indexOf('__reactFiber')===0;});
var f=b[k],r=null;while(f){var props=f.memoizedProps||{};
 if(props.name===b.getAttribute('name')&&typeof props.onChange==='function'&&'value'in props){r=props;}f=f.return;}
if(!r)return 'no-match';
var prev=r.value;
try{r.onChange('%s');}catch(e){return 'call-err:'+e;}
return 'called prev='+prev;})()"""

MASKS = r"""(function(){
var b=document.querySelector('[data-test="filter-bar__apply-button"]');if(!b)return 'no-btn';
var k=Object.keys(b).find(function(k){return k.indexOf('__reactFiber')===0;});
var f=b[k];while(f){var p=f.memoizedProps||{};
 if(p.hasOwnProperty('isApplyDisabled')){return JSON.stringify({disabled:p.isApplyDisabled,sel:JSON.stringify(p.dataMaskSelected),app:JSON.stringify(p.dataMaskApplied),out:p.hasOutOfScopeRequiredFilters});}
 f=f.return;}return 'not-found';})()"""

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
    send("Page.navigate", {"url": BASE + "/superset/dashboard/%s/" % DASH})
    time.sleep(10)
    print("DASH", DASH, "| before:", str(ev(MASKS))[:300])
    print("call:", str(ev(CALL % RANGE)))
    time.sleep(2)
    print("after:", str(ev(MASKS))[:400])
    print("apply btn:", str(ev("(function(){var x=document.querySelector('[data-test=\"filter-bar__apply-button\"]');return x?('disabled='+x.disabled):'no-btn';})()")))
    ws.close()
finally:
    proc.terminate()
    time.sleep(1)
    proc.kill()
