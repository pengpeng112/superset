# -*- coding: utf-8 -*-
"""20261108-FINAL-CLOSEOUT 任务3元数据采集：全量看板 → 标题/发布/角色/图表/数据集 + 目录归属。
看板-图表-数据集-角色走生产元库 SQL（经 remote_exec 思路由调用方注入，本脚本直接读本地 sql/ 导出的
sweep_meta.tsv）；目录归属走 Superset API（分类目录 Markdown 链接解析，同 home-ui parseReports 规则）。"""
import json
import os
import re

import requests

BASE = os.environ.get("ACC_BASE", "http://127.0.0.1:18180")
HERE = os.path.dirname(os.path.abspath(__file__))
CATALOGS = [25, 26, 27, 28, 29, 30, 31, 33]


def session(user, pw):
    s = requests.Session()
    r = s.get(BASE + "/login/", timeout=30)
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text).group(1)
    s.post(BASE + "/login/", data={"username": user, "password": pw, "csrf_token": tok}, timeout=30)
    return s


def parse_reports(code):
    items = []
    for m in re.finditer(r"- \[([^\]]+)\]\((/superset/dashboard/[^)]+)\)", code):
        did = Number = 0
        mm = re.search(r"/dashboard/(\d+)/", m.group(2))
        if mm:
            did = int(mm.group(1))
        items.append(did)
    return items


def main():
    s = session("admin", os.environ["ACC_ADMIN"])
    # 目录归属
    cat_of = {}
    for cid in CATALOGS:
        r = s.get(BASE + "/api/v1/dashboard/%d" % cid, timeout=30).json()["result"]
        pos = r["position_json"]
        if isinstance(pos, str):
            pos = json.loads(pos)
        code = ""
        for k in pos or {}:
            node = pos[k]
            if not isinstance(node, dict):
                continue
            meta = node.get("meta", {}) or {}
            if isinstance(meta.get("code"), str) and "- [" in meta["code"]:
                code = meta["code"]
                break
        for did in parse_reports(code):
            cat_of[did] = r["dashboard_title"].strip()
    with open(os.path.join(HERE, "catalog_map.json"), "w", encoding="utf-8") as f:
        json.dump(cat_of, f, ensure_ascii=False, indent=1)
    print("catalog_map:", len(cat_of), "entries")
    for k in sorted(cat_of):
        print(k, "->", cat_of[k])


if __name__ == "__main__":
    main()
