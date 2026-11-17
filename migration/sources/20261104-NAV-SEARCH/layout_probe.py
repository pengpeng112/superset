# -*- coding: utf-8 -*-
"""布局探针：双浏览器×双分辨率下测量行高/溢出/关键样式，替代人工目检。"""
import json,subprocess,time,urllib.request,websocket,os,sys
BASE="http://127.0.0.1:18180"
ADMIN=os.environ["ACC_ADMIN"]
def http_json(u):
    with urllib.request.urlopen(u,timeout=10) as r: return json.loads(r.read().decode())
MEASURE = (
 "(function(){function o(){return {sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth,sh:document.documentElement.scrollHeight,ih:innerHeight};}"
 "var nav=document.getElementById('hh-home-nav');var navItems=nav?[].map.call(nav.querySelectorAll('.hh-home-nav-item'),function(a){return Math.round(a.getBoundingClientRect().height);}):[];"
 "var rows=[].map.call(document.querySelectorAll('.dashboard-markdown li'),function(li){return Math.round(li.getBoundingClientRect().height);});"
 "var reports=[].map.call(document.querySelectorAll('.hh-cat-report'),function(a){return Math.round(a.getBoundingClientRect().height);});"
 "var hint=document.getElementById('hospital-home-hint');var search=document.getElementById('hh-report-search');"
 "var sr=search?search.getBoundingClientRect():null;"
 "return JSON.stringify({overflow:o(),navItems:navItems,rowHeights:rows.slice(0,5),reportRowHeights:reports.slice(0,3),"
 "hintHeight:hint?Math.round(hint.getBoundingClientRect().height):0,searchBox:search?{w:Math.round(sr.width),h:Math.round(sr.height)}:null,"
 "bg:getComputedStyle(document.body).backgroundColor});})()"
)
import acc_run
acc_run.USERS.update({'admin':ADMIN})


def run(exe,tag,port,w,h):
    import acc_run
    proc=subprocess.Popen([exe,"--remote-debugging-port=%d"%port,"--user-data-dir="+os.path.abspath("profile-lp-%s-%d"%(tag,w)),"--no-first-run","--window-size=%d,%d"%(w,h),"about:blank"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for _ in range(60):
        try: http_json("http://127.0.0.1:%d/json/version"%port); break
        except Exception: time.sleep(0.5)
    info=None
    for m in ("PUT","GET"):
        try:
            req=urllib.request.Request("http://127.0.0.1:%d/json/new?about:blank"%port,method=m)
            with urllib.request.urlopen(req,timeout=10) as r: info=json.loads(r.read().decode()); break
        except Exception: continue
    tab=acc_run.Tab(websocket.create_connection(info["webSocketDebuggerUrl"],timeout=90))
    tab.send("Page.enable"); tab.send("Runtime.enable")
    out=[]
    try:
        ok,detail=acc_run.login(tab,'admin')
        out.append({"page":"login","data":{"ok":ok,"detail":detail}})
        if ok:
            for name,url,wait in [("welcome",BASE+"/superset/welcome/",12),("dir34",BASE+"/superset/dashboard/34/",15),("page61",BASE+"/superset/dashboard/61/",14)]:
                tab.navigate(url,wait)
                for _ in range(20):
                    try:
                        if name=="dir34" and tab.eval("!!document.querySelector('.dashboard-markdown ul')"): break
                        if name=="page61" and tab.eval("document.querySelectorAll('.hdt-picker').length>=1"): break
                        if name=="welcome" and tab.eval("!!document.getElementById('hh-home-nav')"): break
                    except Exception: pass
                    time.sleep(1.5)
                time.sleep(2.0)
                out.append({"page":name,"data":json.loads(tab.eval(MEASURE))})
    finally:
        try: tab.ws.close()
        except Exception: pass
        proc.terminate(); time.sleep(1); proc.kill()
    return out
if __name__=="__main__":
    exe,tag,port,w,h=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),int(sys.argv[5])
    print(json.dumps(run(exe,tag,port,w,h),ensure_ascii=False))
