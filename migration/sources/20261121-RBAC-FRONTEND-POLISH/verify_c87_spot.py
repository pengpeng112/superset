# -*- coding: utf-8 -*-
"""Chromium 87 兼容最小抽测（单组合、单会话，~8 项关键断言）。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_rbac_frontend_polish as V

OUT = os.path.join(V.EVID, "iab_acceptance.json")


def open_mounted(s, url, tries=3):
    for r in range(tries):
        s.open(url, 12.0 if r == 0 else 9.0)
        for _ in range(3):
            ok = s.tab.eval(
                "!!(document.querySelector('[data-test=\"grid-content\"]') && document.querySelector('.dashboard-markdown,.dashboard-component-chart-holder,.error-page-content,#hh-denied-card'))")
            if ok:
                return True
            time.sleep(4)
    return False


def main():
    d = json.load(open(OUT, encoding="utf-8"))
    s = V.Session("c87", V.C87, 1366, 768, "c87-spot")
    try:
        assert s.tab.login(V.VERIFY_USER, V.VERIFY_PWD)
        s.open(V.BASE + "/superset/welcome/", 9.0)
        st = s.j(V.HOME_STATE)
        d["checks"].append({"n": len(d["checks"]) + 1, "name": "C87 003158 零权限侧栏收起+引导卡",
                            "pass": bool(st["nonav"]) and bool(st["guide"]) and not st["cats"],
                            "detail": "nonav=%s guide=%s cats=%s" % (st["nonav"], st["guide"], str(st["cats"])[:60])})
        print("[%s] C87 003158 零权限态" % ("PASS" if (st["nonav"] and st["guide"]) else "FAIL"), flush=True)
        s.open(V.BASE + "/superset/dashboard/46/", 7.0)
        dd = s.j(V.DENIED_STATE)
        d["checks"].append({"n": len(d["checks"]) + 1, "name": "C87 /46 角色提示卡",
                            "pass": bool(dd["card"]) and "报表授权_绩效考核管理" in (dd["text"] or ""),
                            "detail": (dd["text"] or "")[:80]})
        print("[%s] C87 /46 提示卡" % ("PASS" if (dd["card"] and "绩效考核" in (dd["text"] or "")) else "FAIL"), flush=True)
        s.close()

        s = V.Session("c87", V.C87, 1366, 768, "c87-spot-adm")
        assert s.tab.login(V.ADMIN, V.ADMIN_PW)
        s.open(V.BASE + "/superset/welcome/", 9.0)
        st = s.j(V.HOME_STATE)
        bi_vis = sorted(x.split(":")[0] for x in st["bi"] if x.split(":")[1] == "1")
        cats_vis = sorted(x.split(":")[0] for x in st["cats"] if x.split(":")[1] == "1")
        okc1 = bi_vis == ["72", "73", "74", "75"] and cats_vis == ["25", "26", "27", "28", "29", "30", "31", "33"] and st["kybNav"]
        d["checks"].append({"n": len(d["checks"]) + 1, "name": "C87 admin 4驾驶舱9分类",
                            "pass": okc1, "detail": str(bi_vis) + str(cats_vis)})
        print("[%s] C87 admin 全景" % ("PASS" if okc1 else "FAIL"), flush=True)
        if open_mounted(s, V.BASE + "/superset/dashboard/72/"):
            time.sleep(6)
            d72 = s.j(V.DASH72_STATE)
            okk = d72.get("bn373") == "5,276"
            d["checks"].append({"n": len(d["checks"]) + 1, "name": "C87 72 KPI=5,276 十月真值",
                                "pass": okk, "detail": "bn373=%r h378=%s" % (d72.get("bn373"), d72.get("h378"))})
            print("[%s] C87 72 KPI=%s" % ("PASS" if okk else "FAIL", d72.get("bn373")), flush=True)
        if open_mounted(s, V.BASE + "/superset/dashboard/75/"):
            d75 = s.j(V.DASH75_STATE)
            ok75 = d75.get("subOK") and not d75.get("subBad")
            d["checks"].append({"n": len(d["checks"]) + 1, "name": "C87 75 副标题=选定期间",
                                "pass": ok75, "detail": str(d75)})
            print("[%s] C87 75 副标题" % ("PASS" if ok75 else "FAIL"), flush=True)
            s.tab.eval("(function(){var b=document.getElementById('hh-present-btn');if(b)b.click();return 1;})()")
            time.sleep(2)
            p = s.j(V.PRESENT_STATE)
            okp = p.get("mode") and "山东省第二人民医院" in p.get("title", "") and "全院护理工作量" in p.get("title", "")
            d["checks"].append({"n": len(d["checks"]) + 1, "name": "C87 投屏抬头完整",
                                "pass": bool(okp), "detail": p.get("title", "")[:60]})
            print("[%s] C87 投屏抬头" % ("PASS" if okp else "FAIL"), flush=True)
        s.poll_errors()
        d["checks"].append({"n": len(d["checks"]) + 1, "name": "C87 全程 0 pageerror",
                            "pass": len(s.pageerrors) == 0, "detail": str(s.pageerrors[:3])})
        print("[%s] C87 pageerror=%d" % ("PASS" if len(s.pageerrors) == 0 else "FAIL", len(s.pageerrors)), flush=True)
    finally:
        s.close()
    json.dump(d, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    fails = [c for c in d["checks"] if not c["pass"]]
    print("C87-SPOT DONE: total=%d fails=%d" % (len(d["checks"]), len(fails)))


if __name__ == "__main__":
    main()
