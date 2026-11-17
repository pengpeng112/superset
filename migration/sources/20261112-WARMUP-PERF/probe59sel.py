# -*- coding: utf-8 -*-
"""交互式探测：59 号页 ant-select 打开方式（pointerdown/mousedown/focus）。"""
import json
import sys
import time

sys.path.insert(0, r"F:\python\superset\migration\sources\20261112-WARMUP-PERF")
from wb_run import Tab, launch, new_tab  # noqa: E402
import websocket  # noqa: E402

port = 19313
proc, ver = launch(r"C:\Program Files\Google\Chrome\Application\chrome.exe", "sel59", port)
info = new_tab(port)
ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=30)
tab = Tab(ws)
tab.send("Page.enable")
tab.send("Network.enable", {"maxPostDataSize": 65536})
tab.login("admin", "<REDACTED-SUPERSET-ADMIN-PW>")
tab.send("Page.navigate", {"url": "http://127.0.0.1:18180/superset/dashboard/59/"})
for _ in range(40):
    time.sleep(1)
    if (tab.eval("(document.querySelectorAll('.hdt-picker[data-filter-id]').length)||0") or 0):
        break
time.sleep(3)


def probe(label, expr):
    try:
        r = tab.eval(expr)
        print(label, "->", r, flush=True)
    except Exception as e:
        print(label, "ERR", repr(e)[:100], flush=True)


probe("step0", """(function(){
  var i=document.getElementById('NATIVE_FILTER-P59-V1');
  var sel=i.closest('.ant-select');
  var selr=sel.querySelector('.ant-select-selector');
  return JSON.stringify({inputId:i.id,selCls:sel.className.slice(0,50),hasSelector:!!selr,
    ariaEx:sel.getAttribute('aria-expanded'),inputRole:i.getAttribute('role')});
})()""")

# 尝试1: 真实鼠标事件序列 pointerdown+mousedown on selector
probe("pointerdown", """(function(){
  var i=document.getElementById('NATIVE_FILTER-P59-V1');
  var selr=i.closest('.ant-select').querySelector('.ant-select-selector');
  ['pointerdown','mousedown','pointerup','mouseup','click'].forEach(function(t){
    selr.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window}));
  });
  return 'dispatched';
})()""")
time.sleep(1.5)
probe("dd1", """(function(){
  var dd=document.querySelectorAll('.ant-select-dropdown:not(.ant-select-dropdown-hidden)');
  var opts=dd.length?dd[dd.length-1].querySelectorAll('.ant-select-item-option').length:0;
  return JSON.stringify({open:dd.length,opts:opts,ex:(document.getElementById('NATIVE_FILTER-P59-V1').closest('.ant-select').getAttribute('aria-expanded'))});
})()""")
# 尝试2: focus input
probe("focus", """(function(){var i=document.getElementById('NATIVE_FILTER-P59-V1');i.focus();return document.activeElement.id;})()""")
time.sleep(1.2)
probe("dd2", """(function(){
  var dd=document.querySelectorAll('.ant-select-dropdown:not(.ant-select-dropdown-hidden)');
  return JSON.stringify({open:dd.length,opts:dd.length?dd[dd.length-1].querySelectorAll('.ant-select-item-option').length:0});
})()""")
# 若开着，点 option 3
probe("pick3", """(function(){
  var dd=document.querySelectorAll('.ant-select-dropdown:not(.ant-select-dropdown-hidden)');
  if(!dd.length)return 'no-dd';
  var opts=dd[dd.length-1].querySelectorAll('.ant-select-item-option');
  var titles=[];
  for(var k=0;k<Math.min(opts.length,5);k++)titles.push(opts[k].textContent.trim());
  for(var j=0;j<opts.length;j++){
    if(opts[j].textContent.trim()==='3'){
      opts[j].dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true}));
      opts[j].dispatchEvent(new MouseEvent('mouseup',{bubbles:true,cancelable:true}));
      opts[j].click();
      return 'clicked3 of '+opts.length+' sample='+titles.join('|');
    }
  }
  return 'no3:'+titles.join('|');
})()""")
time.sleep(1.5)
probe("after", """(function(){
  var g=window.hospitalVisitGuard;
  var v1=g.draftValue('NATIVE_FILTER-P59-V1');
  return JSON.stringify({v1:v1});
})()""")
ws.close()
proc.terminate()
time.sleep(1)
proc.kill()
