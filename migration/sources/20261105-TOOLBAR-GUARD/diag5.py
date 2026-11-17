# -*- coding: utf-8 -*-
"""诊断5：真实路径选日期→查询→用「原生同构 QueryContext」构造实测导出（行数与页面一致性）。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from acc2_run import Tab, login, launch, new_tab, USERS  # noqa

import websocket

BASE = "http://127.0.0.1:18180"

PICK_JS = (
    "(function(a,b){var ps=document.querySelectorAll('.hdt-picker input');"
    "for(var i=0;i<ps.length;i++){if(ps[i]._flatpickr){ps[i]._flatpickr.setDate([a,b],true);return 'picked:'+a+'|'+b;}}"
    "return 'no-picker:'+ps.length;})('%s','%s')"
)

EXPORT_JS = r"""(function(fmt){
var e=document.querySelector('[data-test="grid-content"]');
if(!e)return 'no-grid';
var k=Object.keys(e).filter(function(k){return k.indexOf('__reactFiber')===0;})[0];
var f=e[k],store=null;while(f){var p=f.memoizedProps,s=p&&(p.store||(p.value&&p.value.store));
if(s&&s.getState){store=s;break;}f=f.return;}
if(!store)return 'no-store';
var st=store.getState();
var h=document.querySelector('.dashboard-component-chart-holder[class*="dashboard-chart-id-"]');
var m=(h.className||'').match(/dashboard-chart-id-(\d+)/);var c=st.charts[m[1]];
if(!c||!c.latestQueryFormData)return 'no-fd';
var fd=c.latestQueryFormData;
var ds=fd.datasource;
var dsObj=null;
if(typeof ds==='string'){var mm=ds.match(/^(\d+)__(\w+)$/);dsObj=mm?{id:+mm[1],type:mm[2]}:{id:0,type:'table'};}
else if(ds&&typeof ds==='object'){dsObj={id:+ds.id,type:ds.type};}
var q={filters:[],extras:{having:'',where:''},applied_time_extras:{},
columns:fd.all_columns||[],orderby:fd.order_by_cols||[],annotation_layers:[],
row_limit:fd.row_limit||50000,series_limit:0,group_others_when_limit_reached:false,
order_desc:!!fd.order_desc,url_params:fd.url_params||{},custom_params:{},custom_form_data:{},
post_processing:[],time_offsets:[]};
var payload={datasource:dsObj,force:false,queries:[q],form_data:fd,result_format:fmt,result_type:'full'};
window.__hhExp={ds:JSON.stringify(dsObj),rowLimit:q.row_limit,urlParams:JSON.stringify(q.url_params).slice(0,120),
pageRows:(c.queriesResponse&&c.queriesResponse[0])?c.queriesResponse[0].rowcount:null,
fdTimeRange:fd.time_range||'',fdNfk:(fd.url_params||{}).native_filters_key||''};
return fetch('/api/v1/chart/data',{method:'POST',credentials:'same-origin',
headers:{'Content-Type':'application/json'},
body:JSON.stringify(payload)})
.then(function(r){window.__hhExp.http=r.status;window.__hhExp.ct=r.headers.get('Content-Type');
if(!r.ok)return r.text().then(function(t){window.__hhExp.errBody=t.slice(0,200);return JSON.stringify(window.__hhExp);});})
.then(function(){return fmt==='csv'?fetch('/api/v1/chart/data',{method:'POST',credentials:'same-origin',
headers:{'Content-Type':'application/json'},
body:JSON.stringify(payload)}):(window.__hhNext=1,fetch('/api/v1/chart/data',{method:'POST',credentials:'same-origin',
headers:{'Content-Type':'application/json'},
body:JSON.stringify(payload)}));})
.then(function(r){return r.text();})
.then(function(t){window.__hhExp.len=t.length;
window.__hhExp.firstLines=t.split(/\r?\n/).slice(0,2).join(' | ').slice(0,160);
window.__hhExp.lineCount=t.split(/\r?\n/).length-1;
return JSON.stringify(window.__hhExp);});})('csv')"""


def main():
    USERS.update({"admin": os.environ["ACC_ADMIN"]})
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9380
    proc, ver = launch("C:/Program Files/Google/Chrome/Application/chrome.exe", port,
                       os.path.abspath("profile-diag9"), 1600, 900)
    info = new_tab(port)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=40)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Runtime.enable")
    ok, det = login(tab, "admin")
    print("login:", ok)
    tab.navigate(BASE + "/superset/dashboard/65/")
    tab.wait("!!document.querySelector('.hh-query-toolbar')", timeout=60)
    # 等 hdt-picker 出现（dashboard 元数据加载后）
    got = tab.wait("document.querySelectorAll('.hdt-picker input').length>=1", timeout=60)
    print("picker wait:", got)
    # 等首查完成（兜底可能 3~60s 波动）
    for i in range(120):
        s = tab.eval("((document.querySelector('.hh-query-toolbar .hh-qt-summary')||{}).textContent||'')")
        if "共返回" in s:
            break
        time.sleep(1)
    print("summary0:", s)
    # flatpickr 真实选 9-16 单日
    for attempt in range(10):
        r = tab.eval(PICK_JS % ("2026-09-16", "2026-09-16"))
        print("pick try", attempt, ":", r)
        if r.startswith("picked"):
            break
        time.sleep(2)
    time.sleep(1.5)
    tab.eval("(function(){var b=document.querySelector('[data-test=\"filter-bar__apply-button\"]');if(b)b.click();return 1;})()")
    # 等查询完成（非兜底行数）
    for i in range(120):
        s = tab.eval("((document.querySelector('.hh-query-toolbar .hh-qt-summary')||{}).textContent||'')")
        if "4,444" in s:
            break
        time.sleep(1)
    print("summary1:", s)
    time.sleep(2)
    out = tab.eval(EXPORT_JS, await_promise=True)
    print("export diag:", out)
    proc.terminate()
    time.sleep(1)
    proc.kill()


if __name__ == "__main__":
    main()
