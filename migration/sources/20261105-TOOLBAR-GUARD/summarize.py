# -*- coding: utf-8 -*-
"""汇总四轮验收 JSON 为 acceptance 汇总表（json+csv）。"""
import csv
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
rows = []
for f in sorted(glob.glob(os.path.join(HERE, "acc2-chromeG-1920x1080.json")) +
                glob.glob(os.path.join(HERE, "acc2-chromeG-1366x768.json")) +
                glob.glob(os.path.join(HERE, "acc2-c87-1920x1080.json")) +
                glob.glob(os.path.join(HERE, "acc2-c87-1366x768.json"))):
    data = json.load(open(f, encoding="utf-8"))
    rows.extend(data)

with open(os.path.join(HERE, "toolbar-guard-acceptance.json"), "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)
with open(os.path.join(HERE, "toolbar-guard-acceptance.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["browser", "browser_version", "user", "viewport", "verify_point", "check", "result", "detail"])
    for r in rows:
        w.writerow([r["browser"], r["browser_version"], r["user"], r["viewport"], r["verify_point"], r["check"], r["result"], r["detail"]])

n = len(rows)
fails = [r for r in rows if r["result"] == "FAIL"]
print("TOTAL=%d PASS=%d FAIL=%d" % (n, n - len(fails), len(fails)))
for r in fails:
    print("FAIL:", r["browser"], r["viewport"], r["check"], "|", r["detail"][:150])
