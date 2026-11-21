# -*- coding: utf-8 -*-
"""C 深页专项补测：每页最多 3 次 reload 挂载自愈（SPA 半启动自愈上限提升）。"""
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
        print("  (mount retry %d for %s)" % (r + 1, url), flush=True)
    return False


def main():
    d = json.load(open(OUT, encoding="utf-8"))
    s = V.Session("chrome", V.CHROME, 1920, 1080, "single-c2")
    try:
        assert s.tab.login(V.ADMIN, V.ADMIN_PW)

        # 34 全景 + h16 + h17
        if open_mounted(s, V.BASE + "/superset/dashboard/34/"):
            d34 = s.j(V.DIR_STATE)
            vis_groups = sorted(g.split(":")[0] for g in d34["groups"] if g.split(":")[1] == "1")
            ok34 = vis_groups == ["25", "26", "27", "28", "29", "30", "31", "33", "kyb"] and \
                d34["cards"] == ["72", "73", "74", "75"]
            d["checks"] = [c for c in d["checks"] if c["name"] != "C-deep 34 全9组+4卡"]
            d["checks"].append({"n": len(d["checks"]) + 1, "name": "C-deep 34 全9组+4卡", "pass": ok34,
                                "detail": str(vis_groups) + " cards=" + str(d34["cards"])})
            print("[%s] C-deep 34 全9组+4卡 | %s" % ("PASS" if ok34 else "FAIL", str(vis_groups)), flush=True)
            s.tab.eval("(function(){var li=document.querySelector('li[data-hh-cat-group=\"33\"] .hh-cat-toggle');if(li)li.click();return 1;})()")
            time.sleep(3)
            kids33 = s.j("(function(){var li=document.querySelector('li[data-hh-cat-group=\"33\"]');return li?li.querySelectorAll('.hh-cat-report').length:-1;})()")
            d["checks"] = [c for c in d["checks"] if c["name"] != "C-deep h16 下钻33=6行"]
            d["checks"].append({"n": len(d["checks"]) + 1, "name": "C-deep h16 下钻33=6行",
                                "pass": kids33 == 6, "detail": "kids=%s" % kids33})
            print("[%s] C-deep h16 下钻33=6行 | kids=%s" % ("PASS" if kids33 == 6 else "FAIL", kids33), flush=True)
            s.tab.eval("(function(){var b=document.querySelector('li[data-hh-cat-group=\"33\"] .hh-fav-btn');if(b)b.click();return 1;})()")
            time.sleep(1.5)
            s.open(V.BASE + "/superset/welcome/", 8.0)
            st2 = s.j(V.HOME_STATE)
            d["checks"] = [c for c in d["checks"] if c["name"] != "C-deep h17 收藏面板"]
            d["checks"].append({"n": len(d["checks"]) + 1, "name": "C-deep h17 收藏面板",
                                "pass": bool(st2["favPanel"]), "detail": "fav=%s" % st2["favPanel"]})
            print("[%s] C-deep h17 收藏面板 | fav=%s" % ("PASS" if st2["favPanel"] else "FAIL", st2["favPanel"]), flush=True)
            s.open(V.BASE + "/superset/dashboard/34/", 6.0)
            s.tab.eval("(function(){var h=document.querySelector('#hh-dir-fav-box .hh-fav-clear');if(h)h.click();return 1;})()")
            time.sleep(1.2)

        # f14 / 42
        if open_mounted(s, V.BASE + "/superset/dashboard/40/"):
            q = s.j(V.QUERY_STATE)
            okf14 = bool(q.get("single")) and bool(q.get("chartMax"))
            d["checks"] = [c for c in d["checks"] if c["name"] != "C-deep f14 单表锁高回归"]
            d["checks"].append({"n": len(d["checks"]) + 1, "name": "C-deep f14 单表锁高回归",
                                "pass": okf14, "detail": str(q)[:110]})
            print("[%s] C-deep f14 单表锁高回归 | %s" % ("PASS" if okf14 else "FAIL", str(q)[:90]), flush=True)
        if open_mounted(s, V.BASE + "/superset/dashboard/42/"):
            q = s.j(V.DUO42_STATE)
            ok42 = q.get("duo") and q.get("chartMax") == "368px" and \
                len(q.get("holderHeights") or []) == 2 and all(h >= 400 for h in q["holderHeights"]) and \
                all(p >= 1 for p in q["pagers"])
            d["checks"] = [c for c in d["checks"] if c["name"] != "C-deep 42双表456/368px"]
            d["checks"].append({"n": len(d["checks"]) + 1, "name": "C-deep 42双表456/368px",
                                "pass": ok42, "detail": str(q)})
            print("[%s] C-deep 42双表456/368px | %s" % ("PASS" if ok42 else "FAIL", str(q)[:110]), flush=True)

        # 75 副标题 + 投屏期间
        if open_mounted(s, V.BASE + "/superset/dashboard/75/"):
            d75 = s.j(V.DASH75_STATE)
            ok75 = d75.get("subOK") and not d75.get("subBad")
            d["checks"] = [c for c in d["checks"] if c["name"] != "C-deep 75 副标题=选定期间"]
            d["checks"].append({"n": len(d["checks"]) + 1, "name": "C-deep 75 副标题=选定期间",
                                "pass": ok75, "detail": str(d75)})
            print("[%s] C-deep 75 副标题=选定期间 | %s" % ("PASS" if ok75 else "FAIL", str(d75)), flush=True)
            s.tab.eval("(function(){var b=document.getElementById('hh-present-btn');if(b)b.click();return 1;})()")
            time.sleep(2)
            p = s.j(V.PRESENT_STATE)
            okpd = "2026-10-01 至 2026-10-31" in p.get("period", "")
            d["checks"] = [c for c in d["checks"] if c["name"] != "C-deep 投屏期间含端"]
            d["checks"].append({"n": len(d["checks"]) + 1, "name": "C-deep 投屏期间含端",
                                "pass": okpd, "detail": p.get("period", "")})
            print("[%s] C-deep 投屏期间含端 | %s" % ("PASS" if okpd else "FAIL", p.get("period", "")), flush=True)
            s.tab.eval("(function(){document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));return 1;})()")
            time.sleep(1.2)

        # 72 三项
        if open_mounted(s, V.BASE + "/superset/dashboard/72/"):
            time.sleep(6)
            d72 = s.j(V.DASH72_STATE)
            win_ok = (d72.get("period", "").find("2026-10-01 至 2026-10-31") >= 0 or
                      d72.get("queryTR", "").find("2026-10-01 : 2026-11-0") >= 0)
            for name, okv, det in (
                ("C-deep 72 默认窗2026-10", win_ok, "period=%s queryTR=%s" % (d72.get("period"), d72.get("queryTR"))),
                ("C-deep 72 KPI=十月真值5,276", d72.get("bn373") == "5,276", "bn373=%r" % d72.get("bn373")),
                ("C-deep 378 高度≥280px", (d72.get("h378") or 0) >= 280, "h=%s" % d72.get("h378")),
            ):
                d["checks"] = [c for c in d["checks"] if c["name"] != name]
                d["checks"].append({"n": len(d["checks"]) + 1, "name": name, "pass": bool(okv), "detail": det})
                print("[%s] %s | %s" % ("PASS" if okv else "FAIL", name, det), flush=True)
    finally:
        s.close()
    json.dump(d, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    fails = [c for c in d["checks"] if not c["pass"]]
    print("C-RETRY DONE: total=%d fails=%d" % (len(d["checks"]), len(fails)))
    for f in fails:
        print("  FAIL:", f["name"], f["detail"][:90])


if __name__ == "__main__":
    main()
