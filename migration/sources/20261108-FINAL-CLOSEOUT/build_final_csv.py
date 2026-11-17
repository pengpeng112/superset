# -*- coding: utf-8 -*-
"""20261108-FINAL-CLOSEOUT 任务3：合成《全系统看板终验总表-20261108.csv》。
输入：sweep_meta.tsv（生产元库）+ catalog_map.json（目录归属）+ sweep-chrome.json + sweep-c87.json（双浏览器探针）。"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

CAT_NAME = {
    25: "月报", 26: "护理部报表", 27: "门诊", 28: "急诊", 29: "手术",
    30: "门诊流量监测", 31: "绩效考核监测", 33: "质控科报表",
}


def cat_of(did, title):
    if did == 34:
        return "总目录"
    if did in CAT_NAME:
        return "分类目录/" + CAT_NAME[did]
    if did in (1, 2):
        return "病案专项"
    if did == 32:
        return "主报表/" + "质控科报表"  # 32 挂质控科目录（catalog_map 实测）
    if 35 <= did <= 60:
        with open(os.path.join(HERE, "catalog_map.json"), encoding="utf-8") as f:
            m = json.load(f)
        base = m.get(str(did), "")
        base = base.replace("统计报表·", "")
        return "主报表/" + (base or "未归类")
    if 61 <= did <= 70:
        return "抗菌药物监测"
    if did in (72, 73, 74):
        return "可视化驾驶舱"
    return "其他"


def load_sweep(tag):
    with open(os.path.join(HERE, "sweep-%s.json" % tag), encoding="utf-8") as f:
        d = json.load(f)
    return {r["id"]: r for r in d["rows"]}, d.get("browser", "")


def main():
    meta = {}
    with open(os.path.join(HERE, "sweep_meta.tsv"), encoding="utf-8") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) < 6 or not p[0].isdigit():
                continue
            meta[int(p[0])] = {
                "title": p[1],
                "published": {"t": "已发布", "f": "未发布"}.get(p[2], p[2]),
                "roles": p[3].replace("(未绑定)", "未绑定(仅Admin)"),
                "slices": p[4].replace("(无)", "无"),
                "datasets": p[5].replace("(无)", "无"),
            }
    chrome, chrome_ver = load_sweep("chrome")
    c87, c87_ver = load_sweep("c87")

    def st_text(row):
        if row is None:
            return "未测"
        return ("正常·" + row["note"]) if row["ok"] else ("异常·" + row["note"])

    rows = []
    for did in sorted(meta):
        m = meta[did]
        cr, kr = chrome.get(did), c87.get(did)
        ms = ""
        if cr and cr.get("ms", -1) > 0:
            ms = cr["ms"]
        elif kr and kr.get("ms", -1) > 0:
            ms = kr["ms"]
        cal = (cr or kr or {}).get("cal", "-")
        tb = (cr or kr or {}).get("tb", "-")
        rows.append([
            did, m["title"], cat_of(did, m["title"]), m["slices"], m["datasets"],
            m["published"], m["roles"], cal, tb, st_text(cr), st_text(kr), ms,
        ])
    out = os.path.join(HERE, "全系统看板终验总表-20261108.csv")
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["看板ID", "看板名称", "所属分类", "挂载图表ID", "数据集ID", "发布状态",
                    "绑定角色", "日历控件状态", "工具条状态", "Chrome渲染状态", "Chromium87渲染状态",
                    "首屏响应耗时(ms)"])
        w.writerows(rows)
    print("saved", out, "rows:", len(rows))
    fails = [(r[0], r[9], r[10]) for r in rows if "异常" in r[9] or "异常" in r[10] or "未测" in r[9] or "未测" in r[10]]
    for fd in fails:
        print("CHECK:", fd)


if __name__ == "__main__":
    main()
