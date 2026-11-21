# -*- coding: utf-8 -*-
"""终验 KPI+TR 联合读取（72/75）。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_rbac_frontend_polish as V

COMBO = """(function(){
  var g=document.querySelector('[data-test="grid-content"]');
  var h=document.querySelector('.%s');
  var kpi=h?(h.textContent||'').replace(/\\s+/g,' ').slice(0,44):'';
  if(!g)return 'KPI='+kpi+' TR=no-grid';
  var k=Object.keys(g).filter(function(x){return x.indexOf('__reactFiber')===0;})[0];
  var f=g[k],tr='-';
  while(f){
    var p=f.memoizedProps||{};
    var st=p.store||(p.value&&p.value.store);
    if(st&&st.getState){
      var ch=st.getState().charts||{};
      tr=String((ch['%s']&&ch['%s'].latestQueryFormData||{}).time_range||'-').slice(0,26);
      break;
    }
    f=f.return;
  }
  return 'KPI='+kpi+' TR='+tr;
})()"""


def main():
    s = V.Session("chrome", V.CHROME, 1920, 1080, "diag-final3")
    try:
        assert s.tab.login("admin", V.ADMIN_PW)
        for did, cls, cid in ((72, "dashboard-chart-id-373", "373"), (75, "dashboard-chart-id-395", "395")):
            s.open(V.BASE + "/superset/dashboard/%d/" % did, 14.0)
            for _ in range(8):
                if s.tab.eval("!!document.querySelector('[data-test=\"grid-content\"]')"):
                    break
                time.sleep(4)
            time.sleep(6)
            print("dash %d ->" % did, s.tab.eval(COMBO % (cls, cid, cid)))
    finally:
        s.close()


if __name__ == "__main__":
    main()
