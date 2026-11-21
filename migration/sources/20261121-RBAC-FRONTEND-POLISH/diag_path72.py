# -*- coding: utf-8 -*-
"""对照实验：登录后直接开 72 vs 经首页再开 72，读查询时间窗。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_rbac_frontend_polish as V

TRS = """(function(){
  var g=document.querySelector('[data-test="grid-content"]');
  if(!g)return 'no-grid';
  var k=Object.keys(g).filter(function(x){return x.indexOf('__reactFiber')===0;})[0];
  var f=g[k],out=[];
  while(f){
    var p=f.memoizedProps||{};
    var st=p.store||(p.value&&p.value.store);
    if(st&&st.getState){
      var ch=st.getState().charts||{};
      for(var c in ch){out.push(c+':'+String((ch[c]&&ch[c].latestQueryFormData||{}).time_range||'-').slice(0,26));}
      break;
    }
    f=f.return;
  }
  return out.slice(0,3).join(' | ');
})()"""


def open72_direct(tag):
    s = V.Session("chrome", V.CHROME, 1920, 1080, "pathA-" + tag)
    try:
        assert s.tab.login("admin", V.ADMIN_PW)
        s.open(V.BASE + "/superset/dashboard/72/", 12.0)
        time.sleep(6)
        print("[direct-72]   TRs:", s.tab.eval(TRS))
    finally:
        s.close()


def open72_via_home(tag):
    s = V.Session("chrome", V.CHROME, 1920, 1080, "pathB-" + tag)
    try:
        assert s.tab.login("admin", V.ADMIN_PW)
        s.open(V.BASE + "/superset/welcome/", 7.0)
        s.open(V.BASE + "/superset/dashboard/72/", 12.0)
        time.sleep(6)
        print("[via-home-72] TRs:", s.tab.eval(TRS))
    finally:
        s.close()


if __name__ == "__main__":
    open72_direct("a")
    open72_via_home("b")
