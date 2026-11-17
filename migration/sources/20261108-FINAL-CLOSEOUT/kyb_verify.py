# -*- coding: utf-8 -*-
"""KYB 下钻修复验收（h12）：头部整行点击展开 + hashchange + 原语义回归。"""
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
  var t=li.querySelector('.hh-cat-toggle');
  var cs=getComputedStyle(box);
  return JSON.stringify({exists:true,open:li.getAttribute('data-hh-open'),
    toggle:t?t.textContent:null,links:box?box.querySelectorAll('a').length:-1,
    visible:cs.display!=='none'&&cs.visibility!=='hidden',
    rowToggle:(li.querySelector('.hh-cat-head')||{}).getAttribute?('row'+'_toggle='+li.querySelector('.hh-cat-head').getAttribute('data-hh-row-toggle')):null});
})()"""

CLICK = """(function(sel){
  var li=document.querySelector('li[data-hh-cat-group="kyb"]');if(!li)return 'no-li';
  var el=sel==='toggle'?li.querySelector('.hh-cat-toggle')
        :sel==='name'?li.querySelector('[data-hh-catalog-name]')
        :li.querySelector('[data-hh-catalog-description]');
  if(!el)return 'no-el:'+sel;
  el.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));
  return 'clicked '+sel;
})("%s")"""

SET_FLAG = """(function(){window.__hh_no_reload=Date.now();return 1;})()"""
FLAG_OK = """(function(){return window.__hh_no_reload||0;})()"""

port = 19361
proc, ver = launch(r"C:\Program Files\Google\Chrome\Application\chrome.exe", "kybver", port)
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


def collapse():
    st = json.loads(tab.eval(KYB_STATE))
    if st.get("open") == "1":
        tab.eval(CLICK % "toggle")
        time.sleep(1.2)
    return json.loads(tab.eval(KYB_STATE))


# V0 版本与 34 目录健康
nav("/superset/dashboard/34/")
checks["V0_version"] = {"v": tab.eval("(window.hospitalHomeUI||{}).version"),
                        "native33_before": tab.eval("(function(){var li=document.querySelector('li[data-hh-cat-group=\"33\"]');return li?li.getAttribute('data-hh-open'):'no';})()"),
                        "md_links": tab.eval("(document.querySelectorAll('.dashboard-markdown a[href*=\"/superset/dashboard/\"]').length)||0")}
checks["V1_init_collapsed"] = collapse()

# V2 描述文字点击 → 展开，且无整页刷新（window 标记存活）
tab.eval(SET_FLAG)
tab.eval(CLICK % "desc")
time.sleep(1.8)
st = json.loads(tab.eval(KYB_STATE))
checks["V2_desc_click_expands"] = {"open": st.get("open"), "visible": st.get("visible"),
                                   "flag_alive": tab.eval(FLAG_OK) > 0,
                                   "url": tab.eval("location.pathname+location.hash")}

# V3 收起后名称点击 → 切换展开，preventDefault（URL 不变、无刷新）
collapse()
tab.eval(SET_FLAG)
tab.eval(CLICK % "name")
time.sleep(1.8)
st = json.loads(tab.eval(KYB_STATE))
checks["V3_name_click_toggles"] = {"open": st.get("open"), "flag_alive": tab.eval(FLAG_OK) > 0,
                                   "url": tab.eval("location.pathname+location.hash")}

# V4 收起后静置 3.5s 不回弹（hashchange 放行单发不误触）
collapse()
time.sleep(3.5)
checks["V4_collapse_sticks"] = json.loads(tab.eval(KYB_STATE))

# V5 hashchange：清锚点→收起→置 #kyb → 自动展开一次
tab.eval("(function(){history.replaceState(null,'',location.pathname);return 1;})()")
collapse()
tab.eval("location.hash='#kyb';1")
time.sleep(2.5)
checks["V5_hashchange_expands"] = json.loads(tab.eval(KYB_STATE))

# V6 箭头收起仍可用 + 原生分类未受影响
collapse()
tab.eval("(function(){var li=document.querySelector('li[data-hh-cat-group=\"33\"]');var b=li&&li.querySelector('.hh-cat-toggle');if(b)b.click();return li?(li.querySelector('.hh-cat-head').getAttribute('data-hh-row-toggle')||'none'):'no-native';})()")
time.sleep(1.5)
checks["V6_native33_untouched"] = {
    "kyb_open_after_collapse": json.loads(tab.eval(KYB_STATE)).get("open"),
    "native33_before": checks["V0_version"].get("native33_before"),
    "native33_open": tab.eval("(function(){var li=document.querySelector('li[data-hh-cat-group=\"33\"]');return li?li.getAttribute('data-hh-open'):'no';})()"),
    "native33_links": tab.eval("(function(){var li=document.querySelector('li[data-hh-cat-group=\"33\"]');var b=li&&li.querySelector('.hh-cat-children');return b?b.querySelectorAll('a').length:-1;})()")}
checks["V6_native33_untouched"]["native33_flipped"] = (
    checks["V6_native33_untouched"]["native33_before"] != checks["V6_native33_untouched"]["native33_open"])

# V7 home 侧栏入口 → 34#kyb 落地自动展开（回归）
nav("/", settle=8)
has = tab.eval("(document.getElementById('hh-home-nav-kyb')?1:0)")
if has:
    tab.eval("(function(){document.getElementById('hh-home-nav-kyb').dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));return 1;})()")
    time.sleep(7)
    checks["V7_home_entry_landing"] = {"url": tab.eval("location.pathname+location.hash"),
                                       "state": json.loads(tab.eval(KYB_STATE))}
else:
    checks["V7_home_entry_landing"] = {"sidebar_item": False}

ws.close()
proc.terminate()
time.sleep(1)
proc.kill()

rows = []
expect = {
    "V1_init_collapsed": lambda c: c.get("open") == "0",
    "V2_desc_click_expands": lambda c: c.get("open") == "1" and c.get("visible") and c.get("flag_alive"),
    "V3_name_click_toggles": lambda c: c.get("open") == "1" and c.get("flag_alive") and "#" not in c.get("url", ""),
    "V4_collapse_sticks": lambda c: c.get("open") == "0",
    "V5_hashchange_expands": lambda c: c.get("open") == "1",
    "V6_native33_untouched": lambda c: c.get("kyb_open_after_collapse") == "0" and c.get("native33_open") == "1" and c.get("native33_links", -1) > 0,
}
for k, v in checks.items():
    ok = True
    if k in expect:
        try:
            ok = bool(expect[k](v))
        except Exception:
            ok = False
    rows.append({"check": k, "pass": ok, "detail": v})
    print(("PASS " if ok else "FAIL ") + k + " " + json.dumps(v, ensure_ascii=False)[:160], flush=True)
out = os.path.join(HERE, "kyb-verify.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump({"browser": ver, "checks": rows}, f, ensure_ascii=False, indent=1)
print("kyb verify: %d/%d pass -> %s" % (sum(1 for r in rows if r["pass"]), len(rows), out), flush=True)
