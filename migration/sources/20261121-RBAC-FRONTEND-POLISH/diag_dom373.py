# -*- coding: utf-8 -*-
"""看 373/395 KPI holder 内部数字节点结构。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_rbac_frontend_polish as V

DUMP = """(function(){
  var h=document.querySelector('.%s');
  if(!h)return 'none';
  var nums=[].slice.call(h.querySelectorAll('.text-part,.airline-decimal,input,[class*=text]')).slice(0,6)
    .map(function(e){return (e.className||'').slice(0,30)+' => '+e.textContent.slice(0,20);});
  var svg=[].slice.call(h.querySelectorAll('svg text,tspan')).slice(0,8)
    .map(function(e){return e.textContent.slice(0,16);});
  return JSON.stringify({nums:nums,svg:svg});
})()"""


def main():
    s = V.Session("chrome", V.CHROME, 1920, 1080, "diag-dom")
    try:
        assert s.tab.login("admin", V.ADMIN_PW)
        for did, cls in ((72, "dashboard-chart-id-373"), (75, "dashboard-chart-id-395")):
            s.open(V.BASE + "/superset/dashboard/%d/" % did, 14.0)
            for _ in range(8):
                if s.tab.eval("!!document.querySelector('[data-test=\"grid-content\"]')"):
                    break
                time.sleep(4)
            time.sleep(6)
            print("dash %d ->" % did, s.tab.eval(DUMP % cls))
    finally:
        s.close()


if __name__ == "__main__":
    main()
