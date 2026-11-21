# -*- coding: utf-8 -*-
"""手工复现最近使用过滤逻辑，定位未生效原因。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_rbac_frontend_polish as V

PROBE = r"""(function(){
  var out={version:(window.hospitalHomeUI||{}).version,
           allowed:(window.hospitalHomeUI||{}).allowedIds};
  var items=[].slice.call(document.querySelectorAll('[data-hh-home-card]'));
  out.count=items.length;
  out.detail=items.map(function(i){
    var t=(i.querySelector('[data-hh-row-title]')||{}).textContent||'';
    return {t:t.slice(0,18),vis:i.offsetParent!==null,inline:i.style.display};
  });
  return JSON.stringify(out);
})()"""


def main():
    s = V.Session("chrome", V.CHROME, 1920, 1080, "diag3")
    try:
        assert s.tab.login(V.VERIFY_USER, V.VERIFY_PWD)
        s.open(V.BASE + "/superset/welcome/", 9.0)
        print("before:", s.tab.eval(PROBE))
        # 手工执行与 h18 相同的过滤逻辑
        r = s.tab.eval(r"""(function(){
          try{
            var hu=window.hospitalHomeUI;if(!hu)return 'no homeUI';
            var items=[].slice.call(document.querySelectorAll('[data-hh-home-card]'));
            return 'items='+items.length+' allowedIds='+JSON.stringify(hu.allowedIds||null);
          }catch(e){return 'ERR '+e.message;}
        })()""")
        print("manual:", r)
    finally:
        s.close()


if __name__ == "__main__":
    main()
