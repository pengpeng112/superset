# -*- coding: utf-8 -*-
"""深挖：带 native_filters_key 的 URL + 非管理员探针模拟 + 子容器真实几何测量。"""
import json
import os
import sys
import time

import websocket

sys.path.insert(0, r"F:\python\superset\migration\sources\20261112-WARMUP-PERF")
from wb_run import Tab, launch, new_tab  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "http://127.0.0.1:18180"

# 注入：记录 kyb 伪 URL 是否被请求；延迟 61 探针 1.2s 模拟真实网络
INJECT = """
(function(){
  window.__kyb404fetch=0;window.__probe61=0;window.__errs=[];
  window.addEventListener('error',function(e){window.__errs.push(String(e.message).slice(0,80));});
  var of=window.fetch;
  window.fetch=function(u,o){
    try{
      var s=typeof u==='string'?u:(u&&u.url)||'';
      if(s.indexOf('/api/v1/dashboard/kyb')>=0){window.__kyb404fetch++;}
      if(s.indexOf('/api/v1/dashboard/61')>=0){
        window.__probe61++;
        return new Promise(function(res){
          setTimeout(function(){res(new Response('{}',{status:200}));},1200);
        });
      }
    }catch(e){}
    return of.apply(this,arguments);
  };
})();"""

GEOM = """(function(){
  var li=document.querySelector('li[data-hh-cat-group="kyb"]');
  if(!li)return JSON.stringify({exists:false,cls:document.documentElement.className.slice(0,80)});
  var box=li.querySelector('.hh-cat-children');
  var r=box.getBoundingClientRect();
  var links=box.querySelectorAll('a');
  var lr=links.length?links[0].getBoundingClientRect():null;
  var cs=getComputedStyle(box);
  var lip=li.getBoundingClientRect();
  return JSON.stringify({open:li.getAttribute('data-hh-open'),links:links.length,
    boxH:Math.round(r.height),boxTop:Math.round(r.top),boxDisplay:cs.display,boxVis:cs.visibility,
    boxOverflow:cs.overflow,liBottom:Math.round(lip.bottom),
    link0H:lr?Math.round(lr.height):null,link0W:lr?Math.round(lr.width):null,
    kyb404:window.__kyb404fetch||0,probe61:window.__probe61||0,errs:(window.__errs||[]).slice(0,3)});
})()"""

port = 19366
proc, ver = launch(r"C:\Program Files\Google\Chrome\Application\chrome.exe", "kybdeep", port)
info = new_tab(port)
ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=30)
tab = Tab(ws)
tab.send("Page.enable")
tab.send("Page.addScriptToEvaluateOnNewDocument", {"source": INJECT})
tab.login("admin", "<REDACTED-SUPERSET-ADMIN-PW>")
out = {"browser": ver}


def load(url, settle=10):
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
    time.sleep(3)


# A：带 native_filters_key 的 URL（用户日志里的形态）
load("/superset/dashboard/34/?native_filters_key=a365lLDAMto")
out["A_nfkey_geom"] = json.loads(tab.eval(GEOM))
out["A_nfkey_click_desc"] = None
tab.eval("(function(){var li=document.querySelector('li[data-hh-cat-group=\"kyb\"]');"
         "var el=li.querySelector('[data-hh-catalog-description]');"
         "el.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));return 1;})()")
time.sleep(2)
out["A_nfkey_click_desc"] = json.loads(tab.eval(GEOM))

# B：非管理员模拟——本会话已注入延迟探针；强制走 probe 路径不可行（admin 同步），
#    改为验证：清 sessionStorage 后重载（模拟用户首次访问），量几何
tab.eval("(function(){sessionStorage.removeItem('hhDirOpenIds');return 1;})()")
load("/superset/dashboard/34/")
out["B_fresh_geom"] = json.loads(tab.eval(GEOM))

# C：模拟用户截图态——强制 open=1 + 清空 children，然后点击名称观察是否自愈
tab.eval("(function(){var li=document.querySelector('li[data-hh-cat-group=\"kyb\"]');"
         "li.setAttribute('data-hh-open','1');"
         "var t=li.querySelector('.hh-cat-toggle');t.textContent='▾';"
         "var b=li.querySelector('.hh-cat-children');while(b.firstChild)b.removeChild(b.firstChild);b.removeAttribute('data-hh-signature');"
         "return 1;})()")
time.sleep(1)
out["C_forced_empty"] = json.loads(tab.eval(GEOM))
tab.eval("(function(){var li=document.querySelector('li[data-hh-cat-group=\"kyb\"]');"
         "var el=li.querySelector('[data-hh-catalog-name]');"
         "el.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));return 1;})()")
time.sleep(2)
out["C_click_name_after"] = json.loads(tab.eval(GEOM))
tab.eval("(function(){var li=document.querySelector('li[data-hh-cat-group=\"kyb\"]');"
         "var el=li.querySelector('[data-hh-catalog-name]');"
         "el.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));return 1;})()")
time.sleep(2)
out["C_click_name_2nd"] = json.loads(tab.eval(GEOM))

ws.close()
proc.terminate()
time.sleep(1)
proc.kill()
for k, v in out.items():
    if k != "browser":
        print(k, "=>", json.dumps(v, ensure_ascii=False)[:260], flush=True)
with open(os.path.join(HERE, "kyb-deep.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("saved kyb-deep.json")
