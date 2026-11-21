# -*- coding: utf-8 -*-
"""诊断探针：72/75 日期控件 DOM 结构 + 003158 首页最近使用卡片锚点。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_rbac_frontend_polish as V

PICKER = r"""(function(){
  var h=document.querySelectorAll('.hdt-picker').length;
  var inp=[].slice.call(document.querySelectorAll('.hdt-picker input')).map(function(i){return {al:i.getAttribute('aria-label'),v:i.value};});
  var fb=document.querySelector('[data-test="filter-bar"]');
  return JSON.stringify({h:h,inp:inp,fb:fb?fb.textContent.slice(0,160):''});
})()"""

RECENT = r"""(function(){
  return JSON.stringify([].slice.call(document.querySelectorAll('[data-hh-home-card]')).map(function(i){
    var a=i.querySelector('a');
    return {href:a?a.getAttribute('href'):null,vis:i.offsetParent!==null,
            title:((i.querySelector('[data-hh-row-title]')||{}).textContent||'').slice(0,30)};
  }));
})()"""


def main():
    s = V.Session("chrome", V.CHROME, 1920, 1080, "diag")
    try:
        assert s.tab.login("admin", V.ADMIN_PW)
        s.open(V.BASE + "/superset/dashboard/72/", 8.0)
        print("72 picker:", s.tab.eval(PICKER))
        s.open(V.BASE + "/superset/dashboard/75/", 8.0)
        print("75 picker:", s.tab.eval(PICKER))
    finally:
        s.close()
    s2 = V.Session("chrome", V.CHROME, 1920, 1080, "diag2")
    try:
        assert s2.tab.login(V.VERIFY_USER, V.VERIFY_PWD)
        s2.open(V.BASE + "/superset/welcome/", 8.0)
        print("recent:", s2.tab.eval(RECENT))
    finally:
        s2.close()


if __name__ == "__main__":
    main()
