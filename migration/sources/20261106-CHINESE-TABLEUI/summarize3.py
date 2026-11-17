# -*- coding: utf-8 -*-
"""汇总 20261106-CHINESE-TABLEUI 验收：主矩阵 acc3 × 4 轮 + 必选条件页专项 acc3b × 4 轮。"""
import csv
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
rows = []
for f in sorted(glob.glob(os.path.join(HERE, "acc3-ctC-1920x1080.json")) +
                glob.glob(os.path.join(HERE, "acc3-ctC-1366x768.json")) +
                glob.glob(os.path.join(HERE, "acc3-ct87-1920x1080.json")) +
                glob.glob(os.path.join(HERE, "acc3-ct87-1366x768.json")) +
                glob.glob(os.path.join(HERE, "acc3b-ctC-1920x1080.json")) +
                glob.glob(os.path.join(HERE, "acc3b-ctC-1366x768.json")) +
                glob.glob(os.path.join(HERE, "acc3b-ct87-1920x1080.json")) +
                glob.glob(os.path.join(HERE, "acc3b-ct87-1366x768.json"))):
    rows.extend(json.load(open(f, encoding="utf-8")))

# 59 页 visit_id 1-99 大查询 >300s 的 4 项 FAIL：同一根因（业务慢查，与本批 verbose_name 变更无关——
# 汉化不进 SQL；该页数据集 337 的 4 列汉化已数据库级核验 columns_after.tsv 59/59），如实保留 FAIL 不掩饰
json.dump(rows, open(os.path.join(HERE, "chinese-tableui-acceptance.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
with open(os.path.join(HERE, "chinese-tableui-acceptance.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["browser", "browser_version", "user", "viewport", "verify_point", "check", "result", "detail"])
    for r in rows:
        w.writerow([r.get("browser"), r.get("browser_version"), r.get("user"), r.get("viewport"),
                    r.get("verify_point"), r.get("check"), r.get("result"), r.get("detail")])

n = len(rows)
fails = [r for r in rows if r["result"] == "FAIL"]
print("TOTAL=%d PASS=%d FAIL=%d" % (n, n - len(fails), len(fails)))
for r in fails:
    print("FAIL:", r.get("browser"), r.get("viewport"), r.get("check"), "|", (r.get("detail") or "")[:100])
