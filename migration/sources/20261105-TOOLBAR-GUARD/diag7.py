# -*- coding: utf-8 -*-
"""诊断7：toolbar 重建计数（listener 失效假说）+ 61 页服务端分页 rowcount 语义。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from acc2_run import Tab, login, launch, new_tab, USERS  # noqa

import websocket

BASE = "http://127.0.0.1:18180"


def main():
    USERS.update({"admin": os.environ["ACC_ADMIN"]})
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9410
    which = sys.argv[2] if len(sys.argv) > 2 else "65"
    proc, ver = launch("C:/Program Files/Google/Chrome/Application/chrome.exe", port,
                       os.path.abspath("profile-diag11"), 1500, 950)
    info = new_tab(port)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=40)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Runtime.enable")
    ok, det = login(tab, "admin")
    print("login:", ok)
    tab.navigate(BASE + "/superset/dashboard/%s/" % which)
    tab.wait("!!document.querySelector('.hh-query-toolbar')", timeout=60)
    for i in range(150):
        s = tab.eval("((document.querySelector('.hh-query-toolbar .hh-qt-summary')||{}).textContent||'')")
        if "共返回" in s:
            break
        time.sleep(1)
    print("summary0:", s)
    # 重建计数：1 秒窗口内 toolbar DOM 节点身份是否变化 + 位置
    r = tab.eval(
        "(function(){window.__n0=document.querySelector('.hh-query-toolbar');"
        "window.__seq=0;window.__pos0=(window.__n0.parentElement.firstChild===window.__n0);"
        "return 'marked';})()"
    )
    time.sleep(2.0)
    r = tab.eval(
        "(function(){var n=document.querySelector('.hh-query-toolbar');"
        "var same=(n===window.__n0);var pos=(n.parentElement.firstChild===n);"
        "var idx=[].indexOf.call(n.parentElement.children,n);"
        "var parentCls=n.parentElement.className;var firstCls=n.parentElement.firstElementChild.className;"
        "return JSON.stringify({sameNode:same,isFirst:pos,idx:idx,parentCls:String(parentCls).slice(0,60),firstCls:String(firstCls).slice(0,60)});})()"
    )
    print("toolbar stability:", r)
    # 服务端分页语义：读响应 rowcount / data.length / 分页器总数
    r2 = tab.eval(
        "(function(){var e=document.querySelector('[data-test=\"grid-content\"]');"
        "var k=e&&Object.keys(e).filter(function(k){return k.indexOf('__reactFiber')===0;})[0];"
        "var f=e&&e[k],store=null;while(f){var p=f.memoizedProps,s=p&&(p.store||(p.value&&p.value.store));"
        "if(s&&s.getState){store=s;break;}f=f.return;}"
        "var st=store.getState();var out={};"
        "Object.keys(st.charts).forEach(function(id){var c=st.charts[id];"
        "var r=c.queriesResponse&&c.queriesResponse[0];"
        "out[id]={status:c.chartStatus,rowcount:r?r.rowcount:null,dataLen:r&&r.data?r.data.length:null,"
        "rowLimit:(c.latestQueryFormData||{}).row_limit,serverPageLen:(c.latestQueryFormData||{}).server_page_length,"
        "keys:r?Object.keys(r).join(','):''};});"
        "var pager=document.querySelector('.pagination, [class*=pagination]');"
        "return JSON.stringify({charts:out,pagerText:pager?pager.textContent.replace(/\\s+/g,' ').trim().slice(0,120):''});})()"
    )
    print("paging semantics:", r2[:1500])
    proc.terminate()
    time.sleep(1.5)
    proc.kill()


if __name__ == "__main__":
    main()
