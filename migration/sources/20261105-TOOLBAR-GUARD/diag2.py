# -*- coding: utf-8 -*-
"""诊断2：工具条导出 fetch 的真实 HTTP 状态码与 cookie/form_data 形态。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from acc2_run import Tab, login, launch, new_tab, USERS  # noqa

import websocket

BASE = "http://127.0.0.1:18180"

DIAG_JS = r"""(function(){
var e=document.querySelector('[data-test="grid-content"]');
if(!e)return JSON.stringify({err:'no-grid'});
var k=Object.keys(e).filter(function(k){return k.indexOf('__reactFiber')===0;})[0];
if(!k)return JSON.stringify({err:'no-fiber'});
var f=e[k],store=null;while(f){var p=f.memoizedProps,s=p&&(p.store||(p.value&&p.value.store));
if(s&&s.getState){store=s;break;}f=f.return;}
if(!store)return JSON.stringify({err:'no-store'});
var st=store.getState();
var h=document.querySelector('.dashboard-component-chart-holder[class*="dashboard-chart-id-"]');
if(!h)return JSON.stringify({err:'no-holder'});
var m=(h.className||'').match(/dashboard-chart-id-(\d+)/);var c=st.charts[m[1]];
var fd={};for(var kk in c.latestQueryFormData)fd[kk]=c.latestQueryFormData[kk];
delete fd.page;
var m2=document.cookie.match(/(?:^|;\s*)(csrf_token|csrftoken)=([^;]+)/);
var tok=m2?decodeURIComponent(m2[1]):'';
window.__hhDiag={cookies:document.cookie.split(/; */).map(function(x){return x.split('=')[0];}).join(','),
fdKeys:Object.keys(fd).join(','),timeRange:fd.time_range,ds:JSON.stringify(fd.datasource),
rowLimit:fd.row_limit,pageLen:fd.server_page_length,status:c.chartStatus,
rows:(c.queriesResponse&&c.queriesResponse[0])?c.queriesResponse[0].rowcount:null,tokLen:tok.length};
return fetch('/api/v1/chart/data',{method:'POST',credentials:'same-origin',
headers:{'Content-Type':'application/json','X-CSRFToken':tok},
body:JSON.stringify({result_format:'csv',result_type:'full',form_data:fd})})
.then(function(r){window.__hhDiag.http=r.status;window.__hhDiag.ct=r.headers.get('Content-Type');
return r.text();}).then(function(t){window.__hhDiag.len=t.length;window.__hhDiag.head=t.slice(0,120);
return JSON.stringify(window.__hhDiag);}).catch(function(err){window.__hhDiag.err=String(err);
return JSON.stringify(window.__hhDiag);});})()"""


def main():
    USERS.update({"admin": os.environ["ACC_ADMIN"]})
    proc, ver = launch("C:/Program Files/Google/Chrome/Application/chrome.exe", int(sys.argv[1]) if len(sys.argv) > 1 else 9345,
                       os.path.abspath("profile-diag5"), 1600, 900)
    info = new_tab(int(sys.argv[1]) if len(sys.argv) > 1 else 9345)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=40)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Runtime.enable")
    ok, det = login(tab, "admin")
    print("login:", ok, "|", det)
    if not ok:
        proc.terminate(); proc.kill(); return
    tab.navigate(BASE + "/superset/dashboard/65/")
    tab.wait("!!document.querySelector('.hh-query-toolbar')", timeout=40)
    s = ""
    for i in range(40):
        s = tab.eval("((document.querySelector('.hh-query-toolbar .hh-qt-summary')||{}).textContent||'')")
        if "共返回" in s:
            break
        time.sleep(1)
    print("summary:", s)
    for attempt in range(3):
        try:
            out = tab.eval(DIAG_JS, await_promise=True)
            print("fetch diag:", out)
            break
        except Exception as e:
            print("attempt %d failed: %r" % (attempt, e))
            time.sleep(2)
    proc.terminate()
    time.sleep(1)
    proc.kill()


if __name__ == "__main__":
    main()
