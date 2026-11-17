# -*- coding: utf-8 -*-
"""KYB 下钻问题诊断：34 目录页 抗菌药物监测 分组的真实点击行为复现。

步骤：
  D1 打开 34（无锚点），检查 kyb 组存在性/展开态/children 内容/箭头
  D2 点击 ▸ 箭头 → children 链接数（箭头展开是否可用）
  D3 收起后点击 分类名称链接 → 链接数 + URL 变化（名称点击是否展开）
  D4 收起后点击 描述文字「门急诊处方…10 项专项查询」 → 链接数（描述点击是否展开）
  D5 home 侧栏入口跳转 34#kyb → 落地是否自动展开
输出 kyb-diag.json。
"""
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
  return JSON.stringify({exists:true,open:li.getAttribute('data-hh-open'),
    toggle:t?t.textContent:null,toggleAria:t?t.getAttribute('aria-expanded'):null,
    links:box?box.querySelectorAll('a').length:-1,
    childText:box?box.textContent.slice(0,60):null,
    head:(li.querySelector('.hh-cat-head')||{}).tagName||null});
})()"""

CLICK = """(function(sel){
  var li=document.querySelector('li[data-hh-cat-group="kyb"]');if(!li)return 'no-li';
  var el=sel==='toggle'?li.querySelector('.hh-cat-toggle')
        :sel==='name'?li.querySelector('[data-hh-catalog-name]')
        :li.querySelector('[data-hh-catalog-description]');
  if(!el)return 'no-el:'+sel;
  ['pointerdown','mousedown','pointerup','mouseup','click'].forEach(function(t){
    el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window}));});
  return 'clicked '+sel;
})("%s")"""

port = 19360
proc, ver = launch(r"C:\Program Files\Google\Chrome\Application\chrome.exe", "kybdiag", port)
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
        if tab.eval("(document.querySelector('li[data-hh-cat-group=kyb]')?1:0)") or tab.eval("(document.getElementById('hh-home-nav-kyb')?1:0)"):
            break
        time.sleep(1)
    time.sleep(2.5)


# D1 初始态（无锚点）
nav("/superset/dashboard/34/")
checks["D1_init"] = json.loads(tab.eval(KYB_STATE))

# D2 箭头展开
if checks["D1_init"].get("exists") and checks["D1_init"].get("open") != "1":
    tab.eval(CLICK % "toggle")
    time.sleep(2)
checks["D2_toggle_expand"] = json.loads(tab.eval(KYB_STATE))
first_names = tab.eval("""(function(){var box=document.querySelector('li[data-hh-cat-group=kyb] .hh-cat-children');
  return box?[].slice.call(box.querySelectorAll('a')).slice(0,3).map(function(a){return a.textContent.trim()}).join('|'):'-';})()""")

# D3 名称点击（先收起）
tab.eval(CLICK % "toggle")
time.sleep(1.5)
collapsed = json.loads(tab.eval(KYB_STATE))
tab.eval(CLICK % "name")
time.sleep(2.5)
checks["D3_name_click"] = {"collapsed_before": collapsed, "after": json.loads(tab.eval(KYB_STATE)),
                           "url": tab.eval("location.pathname+location.hash")}

# D4 描述文字点击（先收起）
tab.eval(CLICK % "toggle")
time.sleep(1.5)
collapsed = json.loads(tab.eval(KYB_STATE))
tab.eval(CLICK % "desc")
time.sleep(2.5)
checks["D4_desc_click"] = {"collapsed_before": collapsed, "after": json.loads(tab.eval(KYB_STATE))}

# D5 home 侧栏入口 → 34#kyb
nav("/", settle=8)
has_side = tab.eval("(document.getElementById('hh-home-nav-kyb')?1:0)")
checks["D5_home_entry"] = {"sidebar_item": bool(has_side)}
if has_side:
    tab.eval("(function(){var a=document.getElementById('hh-home-nav-kyb');a.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));return 'clicked';})()")
    time.sleep(7)
    checks["D5_home_entry"]["after_nav"] = json.loads(tab.eval(KYB_STATE))
    checks["D5_home_entry"]["url"] = tab.eval("location.pathname+location.hash")

ws.close()
proc.terminate()
time.sleep(1)
proc.kill()
out = os.path.join(HERE, "kyb-diag.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump({"browser": ver, "checks": checks, "first_names": first_names}, f, ensure_ascii=False, indent=1)
for k, v in checks.items():
    print(k, "=>", json.dumps(v, ensure_ascii=False)[:220], flush=True)
print("first names:", first_names)
print("saved", out, flush=True)
