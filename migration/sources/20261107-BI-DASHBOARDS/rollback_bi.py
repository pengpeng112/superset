# -*- coding: utf-8 -*-
"""20261107-BI-DASHBOARDS 一键回退：删除本批新增的 BI 看板、图表与数据集（ledger 驱动）。
用法：ACC_ADMIN=... python rollback_bi.py [--dry-run] [--all]
默认只删 ledger 中 preexisting!=True 的对象；--all 连本批创建过的全部一起删。
删除顺序：看板 → 图表 → 数据集（先图表后数据集，避免数据集仍被图表引用）。
凭据环境变量 ACC_ADMIN。"""
import json
import os
import re
import sys

import requests

BASE = "http://127.0.0.1:18180"
HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER_PATH = os.path.join(HERE, "bi_created_ledger.json")

s = requests.Session()


def login():
    r = s.get(BASE + "/login/", timeout=30)
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text).group(1)
    s.post(BASE + "/login/", data={"username": "admin", "password": os.environ["ACC_ADMIN"], "csrf_token": tok}, timeout=30)
    rt = s.get(BASE + "/api/v1/security/csrf_token/", timeout=30)
    s.headers["X-CSRFToken"] = rt.json()["result"]
    s.headers["Referer"] = BASE + "/"
    print("login ok")


def main():
    dry = "--dry-run" in sys.argv
    all_flag = "--all" in sys.argv
    led = json.load(open(LEDGER_PATH, encoding="utf-8"))
    if not dry:
        login()
    n = 0
    # 1) 看板
    for d in led.get("dashboards", []):
        if not all_flag and d.get("preexisting"):
            continue
        if dry:
            print("DRY dashboard %s (%s)" % (d["id"], d["title"]))
        else:
            r = s.delete(BASE + "/api/v1/dashboard/%d" % d["id"], timeout=60)
            print("dashboard %s (%s) -> %s" % (d["id"], d["title"], r.status_code))
        n += 1
    # 2) 图表
    for c in led.get("charts", []):
        if not all_flag and c.get("preexisting"):
            continue
        if dry:
            print("DRY chart %s (%s)" % (c["id"], c["title"]))
        else:
            r = s.delete(BASE + "/api/v1/chart/%d" % c["id"], timeout=60)
            print("chart %s (%s) -> %s" % (c["id"], c["title"], r.status_code))
        n += 1
    # 3) 数据集
    for t in led.get("datasets", []):
        if not all_flag and t.get("preexisting"):
            continue
        if dry:
            print("DRY dataset %s (%s)" % (t["id"], t["table_name"]))
        else:
            r = s.delete(BASE + "/api/v1/dataset/%d" % t["id"], timeout=60)
            print("dataset %s (%s) -> %s" % (t["id"], t["table_name"], r.status_code))
        n += 1
    print("%s %d objects" % ("would delete" if dry else "deleted", n))


if __name__ == "__main__":
    main()
