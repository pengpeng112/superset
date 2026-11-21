# -*- coding: utf-8 -*-
"""最后 2 项补测（真 Chrome 单会话）：B2 34目录裁剪（IAB 平台不可测，Chrome 覆盖）+ 41 xlsx 落盘。
完成后 revoke-user 还原 003158。
"""
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
    s = V.Session("chrome", V.CHROME, 1920, 1080, "final2")
    try:
        assert s.tab.login(V.VERIFY_USER, V.VERIFY_PWD)
        if open_mounted(s, V.BASE + "/superset/dashboard/34/"):
            d34 = s.j(V.DIR_STATE)
            g26 = [g for g in d34["groups"] if g.startswith("26:")]
            vis = [g for g in d34["groups"] if g.split(":")[1] == "1"]
            ok = d34["showcase"] and d34["k"] == "1" and d34["cards"] == ["75"] and \
                len(g26) == 1 and "3 项" in g26[0] and len(vis) == 1
            idx = next((i for i, c in enumerate(d["checks"]) if c["name"] == "B2-iab-1920 34仅护理组+单卡75"), None)
            rec = {"n": (d["checks"][idx]["n"] if idx is not None else len(d["checks"]) + 1),
                   "name": "B-chrome 34仅护理组+单卡75（IAB Electron 不渲染 dashboard，由 Chrome 单会话覆盖）",
                   "pass": ok, "detail": str(d34["groups"])[:120] + " k=" + str(d34["k"])}
            if idx is not None:
                d["checks"][idx] = rec
            else:
                d["checks"].append(rec)
            print("[%s] B-34 %s | %s" % ("PASS" if ok else "FAIL", rec["name"], rec["detail"][:110]), flush=True)

        s.open(V.BASE + "/superset/dashboard/41/", 10.0)
        for _ in range(15):
            q = s.j(V.QUERY_STATE)
            if (q.get("rows") or 0) > 0:
                break
            time.sleep(3)
        for f in os.listdir(V.DOWNLOADS):
            os.remove(os.path.join(V.DOWNLOADS, f))
        s.tab.eval("(document.querySelector('.hh-btn-xlsx')||{}).click&&document.querySelector('.hh-btn-xlsx').click()")
        got = None
        deadline = time.time() + 90
        while time.time() < deadline:
            time.sleep(2)
            fs_ = [x for x in os.listdir(V.DOWNLOADS) if not x.endswith(".crdownload")]
            if fs_:
                got = (fs_[0], os.path.getsize(os.path.join(V.DOWNLOADS, fs_[0])))
                if got[1] > 4096:
                    break
        idx2 = next((i for i, c in enumerate(d["checks"]) if c["name"] == "B-deep 41 xlsx 文件落盘"), None)
        okf = bool(got) and got[1] > 4096
        rec2 = {"n": (d["checks"][idx2]["n"] if idx2 is not None else len(d["checks"]) + 1),
                "name": "B-chrome 41 xlsx 文件落盘（IAB 下载通道限制，由 Chrome 单会话覆盖）",
                "pass": okf, "detail": str(got)}
        if idx2 is not None:
            d["checks"][idx2] = rec2
        else:
            d["checks"].append(rec2)
        print("[%s] B-xlsx %s | %s" % ("PASS" if okf else "FAIL", rec2["name"], rec2["detail"]), flush=True)
    finally:
        s.close()
    json.dump(d, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    fails = [c for c in d["checks"] if not c["pass"]]
    print("FINAL2 DONE: total=%d fails=%d" % (len(d["checks"]), len(fails)))
    for f in fails:
        print("  FAIL:", f["name"], f["detail"][:90])


if __name__ == "__main__":
    main()
