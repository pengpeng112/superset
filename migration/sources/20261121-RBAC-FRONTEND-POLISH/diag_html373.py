# -*- coding: utf-8 -*-
"""373 holder 完整 HTML + 同类 holder 计数。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_rbac_frontend_polish as V


def main():
    s = V.Session("chrome", V.CHROME, 1920, 1080, "diag-html")
    try:
        assert s.tab.login("admin", V.ADMIN_PW)
        s.open(V.BASE + "/superset/dashboard/72/", 14.0)
        for _ in range(8):
            if s.tab.eval("!!document.querySelector('[data-test=\"grid-content\"]')"):
                break
            time.sleep(4)
        time.sleep(8)
        print("holders-with-373:", s.tab.eval("document.querySelectorAll('[class*=\"dashboard-chart-id-373\"]').length"))
        print("text of each:", s.tab.eval(
            "[].slice.call(document.querySelectorAll('[class*=\"dashboard-chart-id-373\"]')).map(function(e){return (e.textContent||'').replace(/\\s+/g,' ').slice(0,50);}).join(' @@ ')"))
        html = s.tab.eval(
            "(function(){var e=document.querySelector('[class*=\"dashboard-chart-id-373\"]');if(!e)return 'none';var b=e.querySelector('.slice_container')||e;return b.innerHTML.slice(0,1800);})()")
        print("inner HTML:", html)
    finally:
        s.close()


if __name__ == "__main__":
    main()
