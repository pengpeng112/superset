# -*- coding: utf-8 -*-
"""诊断 /roles/list 页面状态 + 异常捕获（可重复运行）。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_rbac_frontend_polish as V


def once(tag):
    s = V.Session("chrome", V.CHROME, 1920, 1080, "diag-r9-" + tag)
    full = []
    try:
        assert s.tab.login("admin", V.ADMIN_PW)
        orig = s.tab.send

        def send2(method, params=None, timeout=90):
            r = orig(method, params, timeout)
            for ev in s.tab.drain():
                if ev.get("method") == "Runtime.exceptionThrown":
                    full.append(ev["params"].get("exceptionDetails", {}))
            return r
        s.tab.send = send2
        s.open(V.BASE + "/roles/list/", 10.0)
        for _ in range(12):
            s.tab.send("Runtime.evaluate", {"expression": "1"})
            time.sleep(1)
        state = s.tab.eval(r"""(function(){
          var t=(document.body.textContent||'');
          return JSON.stringify({
            denied:t.indexOf('访问被拒绝')>=0,
            rows:document.querySelectorAll('tr[data-test=\"table-row\"]').length,
            anyTr:document.querySelectorAll('tr').length,
            scope:document.querySelectorAll('.hh-role-scope').length,
            roleNames:[].slice.call(document.querySelectorAll('a[href*=\"/roles/show/\"]')).length});
        })()""")
        print(tag, "state:", state, "| exceptions:", len(full))
        for d in full[:2]:
            exc = d.get("exception", {})
            print("  MSG:", exc.get("description", "")[:260])
            for fr in d.get("stackTrace", {}).get("callFrames", [])[:5]:
                print("    at", fr.get("functionName"), str(fr.get("url", ""))[-60:], fr.get("lineNumber"))
    finally:
        s.close()


if __name__ == "__main__":
    once("a")
    once("b")
