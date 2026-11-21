# -*- coding: utf-8 -*-
"""诊断 /75 'TypeError: Permissions check failed' 完整堆栈与投屏标题。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_rbac_frontend_polish as V


def main():
    s = V.Session("chrome", V.CHROME, 1920, 1080, "diag-perm")
    full = []
    try:
        assert s.tab.login("admin", V.ADMIN_PW)
        # 捕获完整异常
        orig = s.tab.send

        def send2(method, params=None, timeout=90):
            r = orig(method, params, timeout)
            for ev in s.tab.drain():
                if ev.get("method") == "Runtime.exceptionThrown":
                    d = ev["params"].get("exceptionDetails", {})
                    txt = json.dumps(d, ensure_ascii=False)
                    full.append(txt[:3000])
            return r
        s.tab.send = send2
        s.open(V.BASE + "/superset/dashboard/75/", 9.0)
        print("after load errors:", len(full))
        for t in full[:2]:
            print("EXC:", t[:1200])
        full2 = list(full)
        s.tab.eval("(function(){var b=document.getElementById('hh-present-btn');if(b)b.click();return 1;})()")
        time.sleep(2.5)
        for _ in range(6):
            s.tab.send("Runtime.evaluate", {"expression": "1"})
            time.sleep(0.5)
        new = [t for t in full if t not in full2]
        print("after present errors:", len(new))
        for t in new[:2]:
            print("EXC2:", t[:1500])
        print("present:", s.tab.eval(V.PRESENT_STATE))
        print("titleCache probe:", s.tab.eval("(document.querySelector('.hh-pres-title')||{}).textContent||''"))
    finally:
        s.close()


if __name__ == "__main__":
    main()
