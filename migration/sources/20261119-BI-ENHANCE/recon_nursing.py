# -*- coding: utf-8 -*-
"""20261119-BI-ENHANCE 阶段0：护理/病区数据集只读勘察 + SQL 对账 + Gamma 权限排雷。
输出 evidence/nursing_sql_recon.json。凭据环境变量 ACC_ADMIN / ACC_GUEST。
只读：全部经 /api/v1/chart/data 与 GET 接口，不写任何元数据。
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, r"F:\python\superset\migration\sources\20261107-BI-DASHBOARDS")
import bi_api  # noqa: E402
from bi_api import admin, guest, q, S, BASE  # noqa: E402

def agg(col, label=None):
    return {"expressionType": "SIMPLE", "column": {"column_name": col}, "aggregate": "SUM", "label": label or col}

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = []

CAND_IDS = [350, 344, 357, 338, 348, 347, 345, 373, 374]


def dataset_meta(s, dsid):
    r = s.get(BASE + "/api/v1/dataset/%d" % dsid, timeout=60)
    if not r.ok:
        return {"id": dsid, "error": r.status_code}
    res = r.json()["result"]
    cols = []
    for c in res.get("columns", []):
        cols.append({"name": c.get("column_name"), "verbose": c.get("verbose_name"),
                     "type": c.get("type"), "is_dttm": c.get("is_dttm"), "groupby": c.get("groupby")})
    return {"id": dsid, "table_name": res.get("table_name"), "kind": res.get("kind"),
            "sql": (res.get("sql") or "")[:1200], "database": res.get("database", {}).get("id") if isinstance(res.get("database"), dict) else res.get("database"),
            "owners": len(res.get("owners") or []),
            "columns": [c for c in cols if c["name"]],
            "main_dttm": res.get("main_dttm_col")}


def guest_can(s_guest, dsid):
    """Gamma 权限探测：GET dataset（无 CSRF 要求；403=无权限，200=有）。"""
    r = s_guest.get(BASE + "/api/v1/dataset/%d" % dsid, timeout=60)
    return {"http": r.status_code, "ok": r.status_code == 200}


def main():
    s = admin()
    g = guest()
    rec = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "datasets": {}, "gamma": {}, "recon": {}, "counts": {}, "dashboard75_free": None}
    # 全库数据集名扫描（找护理/病区相关）
    names = {}
    page = 0
    while True:
        r = s.get(BASE + "/api/v1/dataset/?q=" + json.dumps({"page": page, "page_size": 100}), timeout=60)
        d = r.json()
        for it in d["result"]:
            names[it["id"]] = it.get("table_name") or it.get("name")
        if not d.get("count") or (page + 1) * 100 >= d["count"]:
            break
        page += 1
    rec["counts"]["datasets"] = len(names)
    nursing_ids = [i for i, n in names.items() if n and re.search(r"护理|病区|床位", n)]
    rec["nursing_datasets"] = {str(i): names[i] for i in nursing_ids}
    print("nursing-related datasets:", rec["nursing_datasets"], flush=True)

    for dsid in sorted(set(CAND_IDS + nursing_ids)):
        rec["datasets"][str(dsid)] = dataset_meta(s, dsid)
        rec["gamma"][str(dsid)] = guest_can(g, dsid)
        print("ds%s: %s gamma=%s" % (dsid, rec["datasets"][str(dsid)].get("table_name"), rec["gamma"][str(dsid)]), flush=True)

    # 看板 id 75 是否空闲
    r = s.get(BASE + "/api/v1/dashboard/75", timeout=30)
    rec["dashboard75_free"] = (r.status_code == 404)
    r = s.get(BASE + "/api/v1/dashboard/?q=" + json.dumps({"page_size": 100}), timeout=60)
    rec["counts"]["dashboards"] = r.json()["count"]
    r = s.get(BASE + "/api/v1/chart/?q=" + json.dumps({"page_size": 1}), timeout=60)
    rec["counts"]["charts"] = r.json()["count"]
    print("dashboard75_free=%s counts=%s" % (rec["dashboard75_free"], rec["counts"]), flush=True)
    # 角色计数（接口可能不可用，容错）
    try:
        r = s.get(BASE + "/api/v1/roles/?q=" + json.dumps({"page_size": 1}), timeout=30)
        rec["counts"]["roles"] = r.json().get("count", "?") if r.ok else "?"
    except Exception:
        rec["counts"]["roles"] = "?"

    out = os.path.join(HERE, "evidence", "nursing_sql_recon.json")
    json.dump(rec, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("saved", out)


if __name__ == "__main__":
    main()
