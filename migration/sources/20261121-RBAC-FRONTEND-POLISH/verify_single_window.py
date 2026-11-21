# -*- coding: utf-8 -*-
"""单窗口轻量补测（应用户要求不再多实例矩阵）：
一个 Chrome 会话顺序跑完 IAB 无法覆盖的 dashboard 深页断言：
  B 深页：41 出数+xlsx 回执、75 副标题（grant 已在位）
  C 全量：admin 首页/34 全景、h16 下钻、h17 收藏、f14 锁高、roles 11 说明、
         75 投屏抬头+Esc、72 十月窗+KPI 真值 5,276+378 高度、42 双表
结果追加合并进 evidence/iab_acceptance.json（runner 标记区分）。
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_rbac_frontend_polish as V

OUT = os.path.join(V.EVID, "iab_acceptance.json")


def load():
    return json.load(open(OUT, encoding="utf-8"))


def save(d):
    json.dump(d, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def add(d, name, ok, detail=""):
    d["checks"].append({"n": len(d["checks"]) + 1, "name": name,
                        "pass": bool(ok), "detail": str(detail)[:250]})
    print("[%s] %s | %s" % ("PASS" if ok else "FAIL", name, str(detail)[:120]), flush=True)


def main():
    d = load()
    assert V.ADMIN_PW, "ACC_ADMIN"

    # ===== B 深页（003158 护理部角色，grant 仍在位）=====
    s = V.Session("chrome", V.CHROME, 1920, 1080, "single-b")
    try:
        assert s.tab.login(V.VERIFY_USER, V.VERIFY_PWD)
        s.open(V.BASE + "/superset/dashboard/41/", 10.0)
        q = {}
        for _ in range(20):
            q = s.j(V.QUERY_STATE)
            if (q.get("rows") or 0) > 0:
                break
            time.sleep(3)
        add(d, "B-deep 41 出数+导出可用", (q.get("rows") or 0) > 0 and q.get("xlsxEnabled") is True,
            "rows=%s sum=%s" % (q.get("rows"), (q.get("summary") or "")[:60]))
        add(d, "B-deep 41 f14 单表锁高", bool(q.get("single")) and bool(q.get("chartMax")), str(q)[:100])
        for f in os.listdir(V.DOWNLOADS):
            os.remove(os.path.join(V.DOWNLOADS, f))
        s.tab.eval("(document.querySelector('.hh-btn-xlsx')||{}).click&&document.querySelector('.hh-btn-xlsx').click()")
        receipt = ""
        deadline = time.time() + 90
        while time.time() < deadline:
            time.sleep(3)
            receipt = s.tab.eval("((document.querySelector('.hh-qt-summary')||{}).textContent||'')") or ""
            if "已导出" in receipt:
                break
        got = None
        for _ in range(8):
            fs_ = [x for x in os.listdir(V.DOWNLOADS) if x.endswith(".xlsx")]
            if fs_:
                got = (fs_[0], os.path.getsize(os.path.join(V.DOWNLOADS, fs_[0])))
                break
            time.sleep(1)
        add(d, "B-deep 41 xlsx 导出回执", "已导出" in receipt and ".xlsx" in receipt, receipt[:80])
        add(d, "B-deep 41 xlsx 文件落盘", bool(got) and got[1] > 4096, str(got))

        s.open(V.BASE + "/superset/dashboard/75/", 10.0)
        d75 = s.j(V.DASH75_STATE)
        add(d, "B-deep 75 副标题无2026-10硬编码", d75.get("subOK") and not d75.get("subBad"), str(d75))
        s.poll_errors()
        add(d, "B-deep pageerror=0/无未预期404", len(s.pageerrors) == 0 and len(s.http404) == 0,
            "err=%s 404=%s" % (s.pageerrors[:2], s.http404[:2]))
    finally:
        s.close()

    # ===== C 全量（admin）=====
    s = V.Session("chrome", V.CHROME, 1920, 1080, "single-c")
    try:
        assert s.tab.login(V.ADMIN, V.ADMIN_PW)
        s.open(V.BASE + "/superset/welcome/", 9.0)
        st = s.j(V.HOME_STATE)
        bi_vis = sorted(x.split(":")[0] for x in st["bi"] if x.split(":")[1] == "1")
        cats_vis = sorted(x.split(":")[0] for x in st["cats"] if x.split(":")[1] == "1")
        add(d, "C-deep admin 4驾驶舱9分类", bi_vis == ["72", "73", "74", "75"] and
            cats_vis == ["25", "26", "27", "28", "29", "30", "31", "33"] and st["kybNav"],
            str(bi_vis) + str(cats_vis))

        s.open(V.BASE + "/superset/dashboard/34/", 9.0)
        d34 = s.j(V.DIR_STATE)
        vis_groups = sorted(g.split(":")[0] for g in d34["groups"] if g.split(":")[1] == "1")
        add(d, "C-deep 34 全9组+4卡", vis_groups == ["25", "26", "27", "28", "29", "30", "31", "33", "kyb"] and
            d34["cards"] == ["72", "73", "74", "75"], str(vis_groups) + " cards=" + str(d34["cards"]))
        s.tab.eval("(function(){var li=document.querySelector('li[data-hh-cat-group=\"33\"] .hh-cat-toggle');if(li)li.click();return 1;})()")
        time.sleep(3)
        kids33 = s.j("(function(){var li=document.querySelector('li[data-hh-cat-group=\"33\"]');return li?li.querySelectorAll('.hh-cat-report').length:-1;})()")
        add(d, "C-deep h16 下钻33=6行", kids33 == 6, "kids=%s" % kids33)
        s.tab.eval("(function(){var b=document.querySelector('li[data-hh-cat-group=\"33\"] .hh-fav-btn');if(b)b.click();return 1;})()")
        time.sleep(1.5)
        s.open(V.BASE + "/superset/welcome/", 7.0)
        st2 = s.j(V.HOME_STATE)
        add(d, "C-deep h17 收藏面板", bool(st2["favPanel"]), "fav=%s" % st2["favPanel"])
        s.open(V.BASE + "/superset/dashboard/34/", 6.0)
        s.tab.eval("(function(){var h=document.querySelector('#hh-dir-fav-box .hh-fav-clear');if(h)h.click();return 1;})()")
        time.sleep(1.2)

        s.open(V.BASE + "/superset/dashboard/40/", 9.0)
        q = s.j(V.QUERY_STATE)
        add(d, "C-deep f14 单表锁高回归", bool(q.get("single")) and bool(q.get("chartMax")), str(q)[:110])

        s.open(V.BASE + "/superset/dashboard/42/", 9.0)
        q = s.j(V.DUO42_STATE)
        add(d, "C-deep 42双表456/368px", q.get("duo") and q.get("chartMax") == "368px" and
            len(q.get("holderHeights") or []) == 2 and all(h >= 400 for h in q["holderHeights"]) and
            all(p >= 1 for p in q["pagers"]), str(q))

        s.open(V.BASE + "/roles/list/", 8.0)
        for _ in range(3):
            if s.tab.eval("document.querySelectorAll('.table tbody tr').length") > 0:
                break
            time.sleep(4)
        s.tab.eval("(function(){var t=document.querySelector('#filter_form a.dropdown-toggle');if(t)t.click();return 1;})()")
        time.sleep(0.8)
        s.tab.eval("(function(){var a=document.querySelector('a.filter[name=\"name\"]');if(a)a.click();return 1;})()")
        time.sleep(0.8)
        s.tab.eval("(function(){var inp=document.querySelector('#filter_form input[type=\"text\"]');if(!inp)return 0;"
                   "var set=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
                   "set.call(inp,'报表授权');inp.dispatchEvent(new Event('input',{bubbles:true}));"
                   "inp.dispatchEvent(new Event('change',{bubbles:true}));"
                   "var btn=document.querySelector('#filter_form button[type=\"submit\"]')||document.querySelector('#filter_form .btn');"
                   "if(btn)btn.click();return 1;})()")
        time.sleep(4)
        r = s.j(V.ROLES_STATE)
        add(d, "C-deep roles 11条管辖说明", (r.get("count") or 0) >= 11 and
            all("管辖：" in x for x in r.get("sample") or []), "count=%s %s" % (r.get("count"), (r.get("sample") or [])[:1]))

        s.open(V.BASE + "/superset/dashboard/75/", 10.0)
        d75 = s.j(V.DASH75_STATE)
        add(d, "C-deep 75 副标题=选定期间", d75.get("subOK") and not d75.get("subBad"), str(d75))
        s.tab.eval("(function(){var b=document.getElementById('hh-present-btn');if(b)b.click();return 1;})()")
        time.sleep(2)
        p = s.j(V.PRESENT_STATE)
        add(d, "C-deep 投屏抬头完整", p.get("mode") and p.get("bar") and
            "山东省第二人民医院" in p.get("title", "") and "全院护理工作量与病区床位效率分析" in p.get("title", ""), p.get("title", ""))
        add(d, "C-deep 投屏期间含端", "2026-10-01 至 2026-10-31" in p.get("period", ""), p.get("period", ""))
        s.tab.eval("(function(){document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));return 1;})()")
        time.sleep(1.2)
        p2 = s.j(V.PRESENT_STATE)
        add(d, "C-deep Esc 退出投屏", not p2.get("mode") and not p2.get("bar"), str(p2))

        s.open(V.BASE + "/superset/dashboard/72/", 12.0)
        d72 = s.j(V.DASH72_STATE)
        win_ok = (d72.get("period", "").find("2026-10-01 至 2026-10-31") >= 0 or
                  d72.get("queryTR", "").find("2026-10-01 : 2026-11-0") >= 0)
        add(d, "C-deep 72 默认窗2026-10", win_ok, "period=%s queryTR=%s" % (d72.get("period"), d72.get("queryTR")))
        add(d, "C-deep 72 KPI=十月真值5,276", d72.get("bn373") == "5,276", "bn373=%r" % d72.get("bn373"))
        add(d, "C-deep 378 高度≥280px", (d72.get("h378") or 0) >= 280, "h=%s" % d72.get("h378"))
        s.poll_errors()
        add(d, "C-deep pageerror=0/无未预期404", len(s.pageerrors) == 0 and len(s.http404) == 0,
            "err=%s 404=%s" % (s.pageerrors[:2], s.http404[:2]))
    finally:
        s.close()

    save(d)
    fails = [c for c in d["checks"] if not c["pass"]]
    print("SINGLE-WINDOW DONE: total=%d fails=%d" % (len(d["checks"]), len(fails)))
    for f in fails:
        print("  FAIL:", f["name"], f["detail"][:90])


if __name__ == "__main__":
    main()
