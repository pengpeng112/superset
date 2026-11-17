# -*- coding: utf-8 -*-
"""计划核查：看板 73 日期联动实测（选 2026-11-06 → 查询 → 看 379 的取值与 SQL 是否含该日期）。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from acc4_run import Tab, launch, new_tab, login  # noqa

import websocket

BASE = "http://127.0.0.1:18180"
CHART = r"""(function(id){
function dig(){var e=document.querySelector('[data-test="grid-content"]');if(!e)return null;
var k=Object.keys(e).filter(function(k){return k.indexOf('__reactFiber')===0;})[0];
var f=e[k];while(f){var p=f.memoizedProps,s=p&&(p.store||(p.value&&p.value.store));if(s&&s.getState)return s;f=f.return;}return null;}
var st=dig();if(!st)return JSON.stringify({noStore:true});
var c=st.getState().charts[id];if(!c)return JSON.stringify({noChart:true});
var r=c.queriesResponse&&c.queriesResponse[0];
var q=(r&&r.query)||'';
return JSON.stringify({status:c.chartStatus,data:r?(r.data||[]).slice(0,2):null,err:r&&r.error?String(r.error).slice(0,200):null,
has1106:q.indexOf('2026-11-06')>=0,qhead:q.replace(/\s+/g,' ').slice(0,160),
whereDtime:/DTIME"?\s*>=/.test(q)||/"DTIME"\s*</.test(q)});})('%s')"""


def main():
    proc, ver = launch("C:/Program Files/Google/Chrome/Application/chrome.exe", 9801,
                       os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile-verify73")), 1600, 950)
    info = new_tab(9801)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=60)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Runtime.enable")
    ok, who = login(tab, "admin", os.environ["ACC_ADMIN"])
    print("login:", ok, who)
    tab.navigate(BASE + "/superset/dashboard/73/")
    for _ in range(60):
        s = json.loads(tab.eval(CHART % "379") or "{}")
        if s.get("status") in ("rendered", "success", "failed"):
            break
        time.sleep(1)
    print("379 before:", json.dumps(s, ensure_ascii=False)[:300])
    got = tab.wait("document.querySelectorAll('.hdt-picker input').length>=1", timeout=60)
    pk = tab.eval("(function(){var ps=document.querySelectorAll('.hdt-picker input');for(var i=0;i<ps.length;i++){"
                  "if(ps[i]._flatpickr){ps[i]._flatpickr.setDate(['2026-11-06','2026-11-06'],true);return 'picked';}}return 'no-picker';})()")
    time.sleep(1.5)
    ap = tab.eval("(function(){var b=document.querySelector('[data-test=\"filter-bar__apply-button\"]');if(!b)return 'no-btn';if(b.disabled)return 'disabled';b.click();return 'clicked';})()")
    print("picker:", got, pk, "| apply:", ap)
    s2 = {}
    for _ in range(90):
        time.sleep(1)
        s2 = json.loads(tab.eval(CHART % "379") or "{}")
        if s2.get("status") in ("rendered", "success", "failed") and (s2.get("has1106") or s2.get("err") or s2.get("data") != s.get("data")):
            break
    print("379 after :", json.dumps(s2, ensure_ascii=False)[:400])
    s383 = json.loads(tab.eval(CHART % "383") or "{}")
    print("383 after :", json.dumps(s383, ensure_ascii=False)[:300])
    proc.terminate()
    time.sleep(1)
    proc.kill()


if __name__ == "__main__":
    main()
