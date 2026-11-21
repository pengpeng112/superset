# -*- coding: utf-8 -*-
"""诊断 /roles/list：①.hh-role-scope 是否渲染（C3 count=0）②晚到 pageerror 完整堆栈。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_rbac_frontend_polish as V


def main():
    s = V.Session("chrome", V.CHROME, 1920, 1080, "diag-roles")
    full = []
    try:
        assert s.tab.login("admin", V.ADMIN_PW)
        orig = s.tab.send

        def send2(method, params=None, timeout=90):
            r = orig(method, params, timeout)
            for ev in s.tab.drain():
                if ev.get("method") == "Runtime.exceptionThrown":
                    d = ev["params"].get("exceptionDetails", {})
                    full.append(json.dumps(d, ensure_ascii=False)[:2500])
            return r
        s.tab.send = send2
        s.open(V.BASE + "/roles/list/", 8.0)
        for _ in range(16):
            s.tab.send("Runtime.evaluate", {"expression": "1"})
            time.sleep(1)
        print("roles page errors:", len(full))
        for t in full[:2]:
            print("EXC:", t[:1400])
        print("table rows:", s.tab.eval("document.querySelectorAll('.ant-table-tbody tr[data-test=table-row]').length"))
        print("scope count:", s.tab.eval("document.querySelectorAll('.hh-role-scope').length"))
        print("first cells:", s.tab.eval(r"""(function(){
          var rows=[].slice.call(document.querySelectorAll('.ant-table-tbody tr[data-test=\"table-row\"]')).slice(0,4);
          return JSON.stringify(rows.map(function(r){
            var c=r.querySelector('[data-test=\"table-row-cell\"]')||r.querySelector('td');
            return {html:(c?c.innerHTML:'').slice(0,90),title:c?c.getAttribute('title'):null};
          }));
        })()"""))
        print("rolesZh loaded:", s.tab.eval("typeof window.hospitalRolesZh"))
    finally:
        s.close()


if __name__ == "__main__":
    main()
