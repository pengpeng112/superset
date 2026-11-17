# -*- coding: utf-8 -*-
"""一次性探测：59 号页筛选条 DOM 结构（visit_id 双下拉 + 日历 + 查询按钮）。"""
import json
import sys
import time

sys.path.insert(0, r"F:\python\superset\migration\sources\20261112-WARMUP-PERF")
from wb_run import Tab, launch, new_tab  # noqa: E402
import websocket  # noqa: E402

port = 19312
proc, ver = launch(r"C:\Program Files\Google\Chrome\Application\chrome.exe", "p59", port)
info = new_tab(port)
ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=30)
tab = Tab(ws)
tab.send("Page.enable")
tab.login("admin", "<REDACTED-SUPERSET-ADMIN-PW>")
tab.send("Page.navigate", {"url": "http://127.0.0.1:18180/superset/dashboard/59/"})
for _ in range(40):
    time.sleep(1)
    if tab.eval("(function(){return document.querySelectorAll('.hdt-picker[data-filter-id]').length})()") or 0:
        break
time.sleep(3)
probe = tab.eval("""(function(){
  var out={pickers:[],v1:null,v2:null,btn:null,selects:[]};
  document.querySelectorAll('.hdt-picker[data-filter-id]').forEach(function(p){
    out.pickers.push({fid:p.getAttribute('data-filter-id'),mode:p.getAttribute('data-mode'),
      input:(p.querySelector('input')||{}).value||''});
  });
  ['NATIVE_FILTER-P59-V1','NATIVE_FILTER-P59-V2'].forEach(function(id){
    var el=document.getElementById(id);
    if(el)out[id.split('-').pop().toLowerCase()]=({tag:el.tagName,cls:el.className.slice(0,80),
      hasFp:!!(el._flatpickr),text:(el.textContent||'').slice(0,40)});
  });
  var b=document.querySelector('[data-test="filter-bar__apply-button"]');
  out.btn=b?{text:(b.textContent||'').trim(),disabled:b.disabled,cls:b.className.slice(0,60)}:null;
  document.querySelectorAll('.filter-bar [class*=ant-select], [data-test=filter-bar] .ant-select').forEach(function(s,i){
    if(i<8)out.selects.push({id:s.id||s.getAttribute('id')||'',cls:s.className.slice(0,60),
      innerId:((s.querySelector('input')||{}).id)||''});
  });
  out.guard=window.hospitalVisitGuard?window.hospitalVisitGuard.version:null;
  out.ui=window.hospitalDateUI?Object.keys(window.hospitalDateUI).slice(0,12):null;
  return JSON.stringify(out);
})()""")
print(probe)
ws.close()
proc.terminate()
time.sleep(1)
proc.kill()
