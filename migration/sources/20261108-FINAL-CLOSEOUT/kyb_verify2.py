# -*- coding: utf-8 -*-
"""KYB 下钻修复终版验收（h14）：头部整行点击 + 锚点 + 原生分类展开粘住 + 刷新记忆。"""
import json
import os
import sys
import time

import websocket

sys.path.insert(0, r"F:\python\superset\migration\sources\20261112-WARMUP-PERF")
from wb_run import Tab, launch, new_tab  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "http://127.0.0.1:18180"

KYB_STATE = """(function(){
  var li=document.querySelector('li[data-hh-cat-group="kyb"]');
  if(!li)return JSON.stringify({exists:false});
  var box=li.querySelector('.hh-cat-children');
  var cs=getComputedStyle(box);
  return JSON.stringify({exists:true,open:li.getAttribute('data-hh-open'),
    links:box?box.querySelectorAll('a').length:-1,
    visible:cs.display!=='none'&&cs.visibility!=='hidden'});
})()"""

N33 = """(function(){
  var li=document.querySelector('li[data-hh-cat-group="33"]');
  if(!li)return JSON.stringify({exists:false});
  var box=li.querySelector('.hh-cat-children');
  var cs=getComputedStyle(box);
  return JSON.stringify({exists:true,open:li.getAttribute('data-hh-open'),
    links:box?box.querySelectorAll('a').length:-1,visible:cs.display!=='none',
    ss:sessionStorage.getItem('hhDirOpenIds')});
})()"""

CLICK = """(function(sel,gid){
  var li=document.querySelector('li[data-hh-cat-group="'+gid+'"]');if(!li)return 'no-li';
  var el=sel==='toggle'?li.querySelector('.hh-cat-toggle')
        :sel==='name'?li.querySelector('[data-hh-catalog-name]')
        :li.querySelector('[data-hh-catalog-description]');
  if(!el)return 'no-el:'+sel;
  el.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));
  return 'clicked '+sel;
})("%s","%s")"""

SET_FLAG = """(function(){window.__hh_no_reload=Date.now();return 1;})()"""
FLAG_OK = """(function(){return window.__hh_no_reload||0;})()"""

port = 19364
proc, ver = launch(r"C:\Program Files\Google\Chrome\Application\chrome.exe", "kybv2", port)
info = new_tab(port)
ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=30)
tab = Tab(ws)
tab.send("Page.enable")
tab.login("admin", "<REDACTED-SUPERSET-ADMIN-PW>")
checks = {}


def nav(url, settle=7):
    tab.send("Page.navigate", {"url": BASE + url})
    time.sleep(2)
    for _ in range(30):
        if tab.eval("document.readyState") == "complete":
            break
        time.sleep(0.5)
    for _ in range(settle * 2):
        if tab.eval("(document.querySelector('li[data-hh-cat-group=kyb]')?1:0)"):
            break
        time.sleep(1)
    time.sleep(2.5)


def kyb_collapse():
    if json.loads(tab.eval(KYB_STATE)).get("open") == "1":
        tab.eval(CLICK % ("toggle", "kyb"))
        time.sleep(1.2)
    return json.loads(tab.eval(KYB_STATE))


nav("/superset/dashboard/34/")
checks["V0_version"] = {"v": tab.eval("(window.hospitalHomeUI||{}).version"),
                        "md_links": tab.eval("(document.querySelectorAll('.dashboard-markdown a[href*=\"/superset/dashboard/\"]').length)||0")}
checks["V1_kyb_init"] = kyb_collapse()

# KYB：描述/名称点击就地展开（无整页刷新）
tab.eval(SET_FLAG)
tab.eval(CLICK % ("desc", "kyb"))
time.sleep(1.8)
st = json.loads(tab.eval(KYB_STATE))
checks["V2_desc_expands"] = {"open": st.get("open"), "visible": st.get("visible"),
                             "flag_alive": tab.eval(FLAG_OK) > 0, "url": tab.eval("location.pathname+location.hash")}
kyb_collapse()
tab.eval(SET_FLAG)
tab.eval(CLICK % ("name", "kyb"))
time.sleep(1.8)
st = json.loads(tab.eval(KYB_STATE))
checks["V3_name_toggles"] = {"open": st.get("open"), "flag_alive": tab.eval(FLAG_OK) > 0,
                             "url": tab.eval("location.pathname+location.hash")}

# KYB：收起不回弹
kyb_collapse()
time.sleep(3.0)
checks["V4_collapse_sticks"] = json.loads(tab.eval(KYB_STATE))

# 锚点 hashchange 展开
tab.eval("(function(){history.replaceState(null,'',location.pathname);return 1;})()")
kyb_collapse()
tab.eval("location.hash='#kyb';1")
time.sleep(2.5)
checks["V5_hashchange_expands"] = json.loads(tab.eval(KYB_STATE))

# 原生 33：箭头展开后必须“粘住”（h14 修复点）且存储为字符串
n0 = json.loads(tab.eval(N33))
if n0.get("open") == "1":
    tab.eval(CLICK % ("toggle", "33"))
    time.sleep(1.0)  # 先收起作为基线
n0 = json.loads(tab.eval(N33))
tab.eval(CLICK % ("toggle", "33"))
time.sleep(0.3)
n1 = json.loads(tab.eval(N33))
time.sleep(2.5)
n2 = json.loads(tab.eval(N33))
checks["V6_native_toggle_sticks"] = {"before": n0.get("open"), "just_after": n1.get("open"),
                                     "after_2_5s": n2.get("open"), "ss": n2.get("ss"),
                                     "visible": n2.get("visible"), "links": n2.get("links")}

# 刷新记忆：重载后 33 仍展开（sessionStorage 记忆生效）
nav("/superset/dashboard/34/")
n3 = json.loads(tab.eval(N33))
checks["V7_native_reload_memory"] = {"open_after_reload": n3.get("open"), "ss": n3.get("ss")}

# KYB 十条链接指向 61-70
names = tab.eval("(function(){var box=document.querySelector('li[data-hh-cat-group=kyb] .hh-cat-children');"
                 "return box?[].slice.call(box.querySelectorAll('a')).map(function(a){return (a.href.match(/dashboard\\/(\\d+)\\//)||[])[1];}).join(','):'';})()")
checks["V8_kyb_link_ids"] = names

# 首页入口落地自动展开（回归）
nav("/", settle=8)
if tab.eval("(document.getElementById('hh-home-nav-kyb')?1:0)"):
    tab.eval("(function(){document.getElementById('hh-home-nav-kyb').dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));return 1;})()")
    time.sleep(7)
    checks["V9_home_landing"] = {"url": tab.eval("location.pathname+location.hash"),
                                 "open": json.loads(tab.eval(KYB_STATE)).get("open")}
else:
    checks["V9_home_landing"] = {"sidebar_item": False}

ws.close()
proc.terminate()
time.sleep(1)
proc.kill()

expect = {
    "V0_version": lambda c: c.get("v") == "20261117h14" and c.get("md_links", 0) >= 57,
    "V1_kyb_init": lambda c: c.get("open") == "0",
    "V2_desc_expands": lambda c: c.get("open") == "1" and c.get("visible") and c.get("flag_alive"),
    "V3_name_toggles": lambda c: c.get("open") == "1" and c.get("flag_alive") and "#" not in c.get("url", ""),
    "V4_collapse_sticks": lambda c: c.get("open") == "0",
    "V5_hashchange_expands": lambda c: c.get("open") == "1" and c.get("visible"),
    "V6_native_toggle_sticks": lambda c: c.get("just_after") == "1" and c.get("after_2_5s") == "1" and c.get("visible") and (c.get("ss") or "").find('"33"') >= 0,
    "V7_native_reload_memory": lambda c: c.get("open_after_reload") == "1",
    "V8_kyb_link_ids": lambda s: [x for x in s.split(",") if x] == [str(i) for i in range(61, 71)],
    "V9_home_landing": lambda c: c.get("open") == "1",
}
rows = []
for k, v in checks.items():
    ok = True
    if k in expect:
        try:
            ok = bool(expect[k](v))
        except Exception:
            ok = False
    rows.append({"check": k, "pass": ok, "detail": v})
    print(("PASS " if ok else "FAIL ") + k + " " + json.dumps(v, ensure_ascii=False)[:180], flush=True)
out = os.path.join(HERE, "kyb-verify-final.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump({"browser": ver, "checks": rows}, f, ensure_ascii=False, indent=1)
print("final verify: %d/%d pass -> %s" % (sum(1 for r in rows if r["pass"]), len(rows), out), flush=True)
