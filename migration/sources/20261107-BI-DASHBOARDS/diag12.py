# -*- coding: utf-8 -*-
"""diag12：72 页逐图错误详情 + 34 页 showcase 插入诊断。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from acc4_run import Tab, launch, new_tab, login  # noqa
import acc4_run

import websocket

pw = {"admin": os.environ["ACC_ADMIN"]}
proc, ver = launch("C:/Program Files/Google/Chrome/Application/chrome.exe", int(sys.argv[1]) if len(sys.argv) > 1 else 9711,
                   os.path.abspath("profile-diag12"), 1600, 950)
info = new_tab(9711)
ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=60)
tab = Tab(ws)
tab.send("Page.enable")
tab.send("Runtime.enable")
ok, det = login(tab, "admin", pw["admin"])
print("login:", ok)
tab.navigate("http://127.0.0.1:18180/superset/dashboard/72/")
for i in range(80):
    d = tab.eval(acc4_run.BI_STATE)
    dd = json.loads(d or "{}")
    if dd.get("total") and dd.get("loading") == 0:
        break
    time.sleep(1)
print("state:", json.dumps({k: v for k, v in dd.items() if k != "rows"}, ensure_ascii=False)[:600])
# 逐图错误
out = tab.eval(r"""(function(){
function dig(){var e=document.querySelector('[data-test="grid-content"]');if(!e)return null;
var k=Object.keys(e).filter(function(k){return k.indexOf('__reactFiber')===0;})[0];
var f=e[k];while(f){var p=f.memoizedProps,s=p&&(p.store||(p.value&&p.value.store));if(s&&s.getState)return s;f=f.return;}return null;}
var st=dig();var charts=st.getState().charts;var out=[];
Object.keys(charts).forEach(function(id){var c=charts[id];var r=c.queriesResponse&&c.queriesResponse[0];
out.push({id:id,name:c.sliceName||'',status:c.chartStatus,err:r&&r.error?String(r.error).slice(0,260):null,
rows:r?r.rowcount:null,formMetric:JSON.stringify((c.latestQueryFormData||{}).metrics||[]).slice(0,180)});});
return JSON.stringify(out);})()""")
print("per-chart:", out[:1800])
# 34 showcase 诊断
tab.navigate("http://127.0.0.1:18180/superset/dashboard/34/")
tab.wait("!!document.querySelector('.dashboard-markdown ul')", timeout=40)
time.sleep(3)
d34 = tab.eval("""(function(){
var md=document.querySelector('.dashboard-markdown');
var wrap=document.getElementById('hh-dir-search-wrap');
var box=document.getElementById('hh-bi-showcase');
var firstChildren=[].map.call(md?md.children:[],function(x){return x.id||x.className||x.tagName;}).slice(0,6);
return JSON.stringify({hasMd:!!md,hasWrap:!!wrap,hasBox:!!box,
wrapParent:wrap?(wrap.parentElement===md?'md':'other'):'',
firstChildren:firstChildren,
ver:window.hospitalHomeUI?window.hospitalHomeUI.version:'',
dirTreeRan:!!document.querySelector('li[data-hh-cat-group]')});})()""")
print("34 diag:", d34)
proc.terminate()
time.sleep(1)
proc.kill()
