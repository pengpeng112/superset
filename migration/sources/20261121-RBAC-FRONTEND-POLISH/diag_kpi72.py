# -*- coding: utf-8 -*-
"""决定性诊断：72 vs 75 KPI 数值 + Redux time_range 列表。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_rbac_frontend_polish as V

KPI = """(function(){
  var h=document.querySelector('.%s');
  return h ? (h.textContent||'').replace(/\\s+/g,' ').slice(0,44) : '';
})()"""

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
  return out.join(' | ');
})()"""


def main():
    s = V.Session("chrome", V.CHROME, 1920, 1080, "diag-kpi3")
    try:
        assert s.tab.login("admin", V.ADMIN_PW)
        for did, cls in ((72, "dashboard-chart-id-373"), (75, "dashboard-chart-id-395")):
            s.open(V.BASE + "/superset/dashboard/%d/" % did, 10.0)
            time.sleep(5)
            print("dash %d KPI=%r" % (did, s.tab.eval(KPI % cls)))
            print("   TRs:", s.tab.eval(TRS))
    finally:
        s.close()


if __name__ == "__main__":
    main()
