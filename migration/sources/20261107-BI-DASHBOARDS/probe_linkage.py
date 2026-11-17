# -*- coding: utf-8 -*-
"""联动桥接探针：72 上手动调 bridge.onChange 看 apply 是否启用。"""
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

exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
port = 18940
proc = subprocess.Popen([exe, "--remote-debugging-port=%d" % port, "--user-data-dir=%s" % os.path.abspath("profile-lnk6"),
                         "--no-first-run", "--no-default-browser-check", "--window-size=1600,900", "about:blank"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def ev(js):
    r = send("Runtime.evaluate", {"expression": js, "returnByValue": True})
    if r.get("exceptionDetails"):
        return "JSEXC: " + ((r["exceptionDetails"].get("exception") or {}).get("description") or "")[:250]
    return r.get("result", {}).get("value")


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


mid = 0
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
    send("Page.navigate", {"url": BASE + "/superset/dashboard/74/"})
    time.sleep(10)

    TRIGGER = "(function(){var t=document.querySelector('[data-test=\"time-range-trigger\"][name]');if(!t)return 'NONE';return t.tagName+' name='+t.getAttribute('name')+' connected='+t.isConnected+' text='+t.textContent.trim().slice(0,40)+' parentHidden='+(getComputedStyle(t.parentElement).display==='none');})()"
    APPLY = "(function(){var b=document.querySelector('[data-test=\"filter-bar__apply-button\"]');return b?('disabled='+b.disabled):'no-btn';})()"
    BRIDGE = ("(function(){var t=document.querySelector('[data-test=\"time-range-trigger\"][name]');if(!t)return 'no-trigger';"
              "var k=Object.keys(t).find(function(k){return k.indexOf('__reactFiber')===0;});if(!k)return 'no-fiber';"
              "var f=t[k],r=null,n=0;while(f){var p=f.memoizedProps||{};if(p.name===t.getAttribute('name')&&typeof p.onChange==='function'&&'value'in p){r=p;n++;}f=f.return;}"
              "if(!r)return 'no-props';window.__br=r;return 'matches='+n+' prevValue='+r.value;})()")
    CALL = ("(function(){var r=window.__br;if(!r)return 'no-bridge';try{r.onChange('2026-09-01 : 2026-10-01');return 'called';}catch(e){return 'call-err:'+e;}})()")

    print("trigger:", str(ev(TRIGGER)))
    print("apply before:", str(ev(APPLY)))
    print("bridge:", str(ev(BRIDGE)))
    print("call:", str(ev(CALL)))
    time.sleep(2)
    print("apply after:", str(ev(APPLY)))
    # 再点 apply（若已启用）
    print("click:", str(ev("(function(){var b=document.querySelector('[data-test=\"filter-bar__apply-button\"]');if(!b)return 'no-btn';if(b.disabled)return 'still-disabled';b.click();return 'clicked';})()")))
    time.sleep(6)
    # 读 Redux 值
    STATE = open(os.path.join(HERE, "pilot_render.py"), encoding="utf-8").read().split('STATE = r"""')[1].split('"""')[0]
    st = json.loads(ev("(function(){" + STATE.replace("function dig", "window.__d=dig") .replace("var st=dig&&dig();", "var st=window.__d&&window.__d();") + "})()") or "{}")
    print("values:", json.dumps(st.get("values", {}), ensure_ascii=False))
    ws.close()
finally:
    proc.terminate()
    time.sleep(1)
    proc.kill()
