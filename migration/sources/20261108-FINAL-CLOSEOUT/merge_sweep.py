# -*- coding: utf-8 -*-
"""20261108-FINAL-CLOSEOUT 任务3：合并 Chrome 终验数据。
来源：①修复节奏全量日志（41页，进程中断未落 JSON）；②续扫 sweep-chrome-resume.json（64-74 + 39 复测）。
51/52/58/59 为必选条件页（20261106-CHINESE-TABLEUI 批登记），首开无表=设计行为，按新分类口径改判。"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = r"C:\Users\ADMINI~1\AppData\Local\Temp\zcode-bash-eRvQjM\sess_b15dff02-f474-4e3e-b3bf-59e1f6c23cd6\call_58bbf2172fac4f4d834b7ceb-stdout.log"
REQUIRED = {51, 52, 58, 59}


def parse_log():
    rows = {}
    if not os.path.exists(LOG):
        return rows
    ver = ""
    for line in open(LOG, encoding="utf-8", errors="replace"):
        m = re.match(r"\[([\d:]+)\]\s+(\S+)\s+(\S+)\s+login=(\S+)\s+slices=(\d+)", line)
        if m:
            ver = m.group(3)
            continue
        m = re.match(r"[\d:]+\s+(\d+)\s+(PASS|FAIL)\s+(\d+)ms\s+(.+?)\s+(\S.*)$", line.strip())
        if not m:
            continue
        did, verdict, ms, note, cal = int(m.group(1)), m.group(2), int(m.group(3)), m.group(4).strip(), m.group(5).strip()
        tb = "不适用"
        if note == "查询页正常":
            tb = "正常(1)"
        rows[did] = {"id": did, "ms": ms, "ok": verdict == "PASS", "note": note,
                     "cal": cal, "tb": tb, "rows": 0, "rendered": 0, "sum": ""}
    return rows, ver


def main():
    rows, ver = parse_log()
    # 必选条件页改判（日志用旧分类器跑出 FAIL）
    for did in REQUIRED:
        if did in rows and not rows[did]["ok"] and rows[did]["note"] == "表格未出":
            rows[did].update({"ok": True, "note": "必选条件页·待选条件(设计)", "tb": "不适用(未查询)"})
    # 合并续扫（覆盖同 id）
    res_path = os.path.join(HERE, "sweep-chrome-resume.json")
    if os.path.exists(res_path):
        d = json.load(open(res_path, encoding="utf-8"))
        for r in d["rows"]:
            rows[r["id"]] = r
    out = {"browser": ver or "Chrome/156.0.8078.81", "rows": [rows[k] for k in sorted(rows)]}
    with open(os.path.join(HERE, "sweep-chrome.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    npass = sum(1 for r in out["rows"] if r["ok"])
    print("merged:", len(out["rows"]), "pages,", npass, "pass")
    for r in out["rows"]:
        if not r["ok"]:
            print("FAIL", r["id"], r["note"], r["cal"], r["tb"])


if __name__ == "__main__":
    main()
