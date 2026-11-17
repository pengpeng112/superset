# -*- coding: utf-8 -*-
"""复现诊断：65 页 set_draft + apply 是否触发查询；工具条 fetch 导出的真实状态码。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from acc2_run import Tab, login, launch, new_tab, http_json, USERS  # noqa

import websocket

BASE = "http://127.0.0.1:18180"
USERS.update({"admin": os.environ["ACC_ADMIN"]})

SET_DRAFT = (
    "(function(v){var t=document.querySelector('[data-test=time-range-trigger][name]');"
    "if(!t)return 'no-trigger';"
    "var k=Object.keys(t).find(function(k){return k.indexOf('__reactFiber')===0;});"
    "var f=t[k],r=null;while(f){var p=f.memoizedProps||{};"
    "if(p.name===t.getAttribute('name')&&typeof p.onChange==='function'&&'value'in p)r=p;f=f.return;}"
    "if(!r)return 'no-bridge';r.onChange(v);return 'set:'+v;})('%s')"
)

PROBE = (
    "(function(){function dig(){var e=document.querySelector('[data-test=\"grid-content\"]');"
    "if(!e)return null;var k=Object.keys(e).filter(function(k){return k.indexOf('__reactFiber')===0;})[0];"
    "var f=e[k];while(f){var p=f.memoizedProps,s=p&&(p.store||(p.value&&p.value.store));"
    "if(s&&s.getState)return s;f=f.return;}return null;}"
    "var st=dig&&dig();var charts=st?st.getState().charts:null;"
    "var h=document.querySelector('.dashboard-component-chart-holder');"
    "var m=h&&(h.className||'').match(/dashboard-chart-id-(\\d+)/);var id=m?m[1]:'';"
    "var c=charts?charts[id]:null;"
    "var tb=document.querySelector('.hh-query-toolbar .hh-qt-summary');"
    "var msg=document.getElementById('hdt-visit-msg');"
    "var g=window.hospitalVisitGuard;"
    "return JSON.stringify({id:id,status:c?c.chartStatus:null,"
    "rowCount:(c&&c.queriesResponse&&c.queriesResponse[0])?(c.queriesResponse[0].rowcount!=null?c.queriesResponse[0].rowcount:(c.queriesResponse[0].data||[]).length):null,"
    "qfd:c&&c.latestQueryFormData?{row_limit:c.latestQueryFormData.row_limit,time_range:c.latestQueryFormData.time_range,ds:JSON.stringify(c.latestQueryFormData.datasource).slice(0,60),keys:Object.keys(c.latestQueryFormData).length}:null,"
    "triggers:document.querySelectorAll('[data-test=time-range-trigger]').length,"
    "applyBtn:!!document.querySelector('[data-test=\"filter-bar__apply-button\"]'),"
    "applyDisabled:(document.querySelector('[data-test=\"filter-bar__apply-button\"]')||{}).disabled,"
    "summary:tb?tb.textContent:'',msg:msg?msg.textContent:'',lastBlock:g?(g.lastBlock||''):'noguard',"
    "span:g&&g.dateSpan?JSON.stringify(g.dateSpan()):''});})()"
)


def main():
    proc, ver = launch("C:/Program Files/Google/Chrome/Application/chrome.exe", 9341,
                       os.path.abspath("profile-diag"), 1600, 900)
    info = new_tab(9341)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=40)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Runtime.enable")
    tab.send("Network.enable")
    ok, det = login(tab, "admin")
    print("login:", ok, det)
    tab.navigate(BASE + "/superset/dashboard/65/")
    tab.wait("!!document.querySelector('.hh-query-toolbar')", timeout=40)
    for i in range(30):
        st = tab.eval(PROBE)
        d = json.loads(st or "{}")
        if d.get("status") in ("rendered", "success") and d.get("rowCount") is not None:
            break
        time.sleep(1)
    print("initial:", tab.eval(PROBE))
    # 拦截记录 chart/data 网络请求
    requests_seen = []

    def on_event(_):
        pass

    # 简易：直接 click 并观察状态流转
    r = tab.eval(SET_DRAFT % "2026-09-16 : 2026-09-17")
    print("set_draft:", r)
    time.sleep(2)
    print("after draft:", tab.eval(PROBE))
    c = tab.eval("(function(){var b=document.querySelector('[data-test=\"filter-bar__apply-button\"]');if(!b)return 'no-btn';b.click();return 'clicked:'+!b.disabled;})()")
    print("apply click:", c)
    for i in range(24):
        d = json.loads(tab.eval(PROBE) or "{}")
        print("t+%02ds" % (i * 3), "status=%s rows=%s msg=%r summary=%r" % (
            d.get("status"), d.get("rowCount"), (d.get("msg") or "")[:40], (d.get("summary") or "")[:60]))
        if d.get("status") in ("rendered", "success") and i > 0:
            break
        time.sleep(3)
    # 导出 fetch 真实诊断：手动跑与工具条同构的 fetch，读状态码
    diag_js = (
        "(function(){"
        "var e=document.querySelector('[data-test=\"grid-content\"]');"
        "var k=Object.keys(e).filter(function(k){return k.indexOf('__reactFiber')===0;})[0];"
        "var f=e[k],store=null;while(f){var p=f.memoizedProps,s=p&&(p.store||(p.value&&p.value.store));"
        "if(s&&s.getState){store=s;break;}f=f.return;}"
        "var st=store.getState().charts;var h=document.querySelector('.dashboard-component-chart-holder');"
        "var m=(h.className||'').match(/dashboard-chart-id-(\\d+)/);var c=st[m[1]];"
        "var fd={};for(var kk in c.latestQueryFormData)fd[kk]=c.latestQueryFormData[kk];"
        "var m2=document.cookie.match(/(?:^|;\\s*)(csrf_token|csrftoken)=([^;]+)/);"
        "var tok=m2?decodeURIComponent(m2[1]):'';"
        "window.__hhDiag={cookieNames:document.cookie.split(/; */).map(function(x){return x.split('=')[0];}).join(','),"
        "fdKeys:Object.keys(fd).join(','),timeRange:fd.time_range,ds:JSON.stringify(fd.datasource),"
        "rowLimit:fd.row_limit,serverPageLen:fd.server_page_length};"
        "return fetch('/api/v1/chart/data',{method:'POST',credentials:'same-origin',"
        "headers:{'Content-Type':'application/json','X-CSRFToken':tok},"
        "body:JSON.stringify({result_format:'csv',result_type:'full',form_data:fd})})"
        ".then(function(r){window.__hhDiag.status=r.status;window.__hhDiag.ct=r.headers.get('Content-Type');"
        "return r.text();}).then(function(t){window.__hhDiag.len=t.length;window.__hhDiag.head=t.slice(0,80);"
        "return JSON.stringify(window.__hhDiag);});})()"
    )
    out = tab.eval(diag_js, await_promise=True)
    print("fetch diag:", out)
    proc.terminate()
    time.sleep(1)
    proc.kill()


if __name__ == "__main__":
    main()
