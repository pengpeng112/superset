# -*- coding: utf-8 -*-
"""计划核查：只读 API 核验（chart/data 查询属只读；登录只会更新 last_login，快照 G4 已剔除该字段）。
凭据环境变量 ACC_ADMIN / ACC_GUEST。输出 verify_plan_facts.json。"""
import json
import os
import re
import time

import requests

BASE = "http://127.0.0.1:18180"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = {}


def session(user, pw):
    s = requests.Session()
    r = s.get(BASE + "/login/", timeout=30)
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text).group(1)
    s.post(BASE + "/login/", data={"username": user, "password": pw, "csrf_token": tok}, timeout=30)
    me = s.get(BASE + "/api/v1/me/", timeout=30)
    return s, (me.json().get("result", {}).get("username") if me.ok else None)


def q(s, ds, query, form_data=None, force=False, viz="table"):
    fd = {"datasource": "%d__table" % ds, "viz_type": viz}
    if form_data:
        fd.update(form_data)
    payload = {"datasource": {"id": ds, "type": "table"}, "force": force,
               "queries": [dict({"filters": [], "row_limit": 1000, "extras": {"having": "", "where": ""}}, **query)],
               "form_data": fd, "result_format": "json", "result_type": "full"}
    t0 = time.time()
    rr = s.post(BASE + "/api/v1/chart/data", json=payload, timeout=300)
    dt = round(time.time() - t0, 1)
    if not rr.ok:
        return {"http": rr.status_code, "sec": dt, "err": rr.text[:200]}
    r0 = rr.json()["result"][0]
    return {"http": 200, "sec": dt, "rows": r0.get("rowcount"), "data": r0.get("data"),
            "sql_has_0901": "2026-09-01" in (r0.get("query") or ""), "is_cached": r0.get("is_cached")}


def S(col):
    return {"expressionType": "SIMPLE", "column": {"column_name": col}, "aggregate": "SUM", "label": "v"}


def TR(col, rng):
    return {"col": col, "op": "TEMPORAL_RANGE", "val": rng}


def main():
    admin, who = session("admin", os.environ["ACC_ADMIN"])
    print("admin login:", who)
    SEP, OCT = "2026-09-01 : 2026-10-01", "2026-10-01 : 2026-11-01"
    # 1) 日期联动是否真的进入 SQL：347 门诊人次 默认/9月/10月
    OUT["347_men_zhens"] = {
        "default": q(admin, 347, {"metrics": [S("MEN_ZHENS")]}),
        "sep": q(admin, 347, {"metrics": [S("MEN_ZHENS")], "filters": [TR("STAT_BEGIN", SEP)]}),
        "oct": q(admin, 347, {"metrics": [S("MEN_ZHENS")], "filters": [TR("STAT_BEGIN", OCT)]}),
    }
    OUT["338_sep"] = {
        "chuyuan": q(admin, 338, {"metrics": [S("CHUYUAN")], "filters": [TR("STAT_BEGIN", SEP)]}),
        "curr": q(admin, 338, {"metrics": [S("CURR")], "filters": [TR("STAT_BEGIN", SEP)]}),
        "ksdm_rows": q(admin, 338, {"columns": ["KSDM"], "metrics": [S("CHUYUAN")], "filters": [TR("STAT_BEGIN", SEP)], "row_limit": 1000}),
    }
    # 2) 345：合计翻倍 + 分支切换（filters 用 val 键）
    OUT["345"] = {
        "sum_all": q(admin, 345, {"metrics": [S("OPER_NUM")]}),
        "sum_ex_total": q(admin, 345, {"metrics": [S("OPER_NUM")], "filters": [{"col": "TJ_KSMC", "op": "NOT IN", "val": ["合计"]}]}),
        "total_row": q(admin, 345, {"columns": ["TJ_KSMC", "OPER_NUM", "BRANCH_NAME"], "filters": [{"col": "TJ_KSMC", "op": "IN", "val": ["合计"]}]}),
        "menzhen_total_row": q(admin, 345, {"columns": ["TJ_KSMC", "OPER_NUM", "BRANCH_NAME"],
                                            "filters": [{"col": "TJ_KSMC", "op": "IN", "val": ["合计"]},
                                                        {"col": "BRANCH_NAME", "op": "IN", "val": ["门诊"]}]}),
    }
    # 3) 348/350 合计行存在
    OUT["348_total_rows"] = q(admin, 348, {"columns": ["KS", "DISCH_N"], "filters": [{"col": "KS", "op": "IN", "val": ["总计", "合计"]}]})
    OUT["350_total_rows"] = q(admin, 350, {"columns": ["KS", "DISCH_N"], "filters": [{"col": "KS", "op": "IN", "val": ["总计", "合计"]}]})
    # 4) 时段桶累计：325 指定工作日 2026-11-06
    DAY = "2026-11-06 : 2026-11-07"
    b = q(admin, 325, {"columns": ["DTIME"], "metrics": [S("COUNT(*)")], "filters": [TR("STAT_DATE", DAY)], "row_limit": 50})
    OUT["325_buckets_20261106"] = b
    # 5) 取药 323 冷查耗时（force=true 绕过缓存，真实打 Oracle）
    m323 = {"expressionType": "SQL", "sqlExpression": 'SUM("COUNT(DISTINCT(B.RCPT_NO))")', "label": "v"}
    OUT["323_cold"] = {
        "today_force": q(admin, 323, {"metrics": [m323]}, force=True),
        "20261106_force": q(admin, 323, {"metrics": [m323], "filters": [TR("STAT_DATE", DAY)]}, force=True),
    }
    OUT["322_cold_20261106_force"] = q(admin, 322, {"metrics": [S("COUNT(*)")], "filters": [TR("STAT_DATE", DAY)]}, force=True)
    OUT["326_cold_20261106_force"] = q(admin, 326, {"metrics": [S("COUNT(*)")], "filters": [TR("STAT_DATE", DAY)]}, force=True)
    # 6) 普通员工 003158：经看板授权取数（DASHBOARD_RBAC 依赖 dashboard_roles + dashboard_slices）
    guest, gwho = session("003158", os.environ["ACC_GUEST"])
    print("guest login:", gwho)
    OUT["guest_login"] = gwho
    OUT["guest_371_on_72"] = q(guest, 347, {"metrics": [S("MEN_ZHENS")]}, form_data={"slice_id": 371, "dashboardId": 72}, viz="big_number_total")
    OUT["guest_379_on_73"] = q(guest, 325, {"metrics": [S("COUNT(*)")]}, form_data={"slice_id": 379, "dashboardId": 73}, viz="big_number_total")
    OUT["guest_386_on_74"] = q(guest, 345, {"metrics": [S("OPER_NUM")]}, form_data={"slice_id": 386, "dashboardId": 74}, viz="big_number_total")
    OUT["guest_dash74_meta"] = guest.get(BASE + "/api/v1/dashboard/74", timeout=30).status_code
    OUT["guest_dash72_meta"] = guest.get(BASE + "/api/v1/dashboard/72", timeout=30).status_code
    with open(os.path.join(HERE, "verify_plan_facts.json"), "w", encoding="utf-8") as f:
        json.dump(OUT, f, ensure_ascii=False, indent=1)

    def v(x):
        try:
            return x["data"][0]["v"]
        except Exception:
            return x.get("err") or x.get("http")
    print("347 门诊人次 default/sep/oct:", v(OUT["347_men_zhens"]["default"]), v(OUT["347_men_zhens"]["sep"]), v(OUT["347_men_zhens"]["oct"]),
          "| sep sql 含 2026-09-01:", OUT["347_men_zhens"]["sep"].get("sql_has_0901"))
    print("338 sep 出院/在院:", v(OUT["338_sep"]["chuyuan"]), v(OUT["338_sep"]["curr"]), "| KSDM 行数:", OUT["338_sep"]["ksdm_rows"].get("rows"))
    print("345 SUM 全部/排除合计:", v(OUT["345"]["sum_all"]), v(OUT["345"]["sum_ex_total"]),
          "| 合计行:", OUT["345"]["total_row"].get("data"), "| 门诊合计行:", OUT["345"]["menzhen_total_row"].get("data"))
    print("348 合计行:", OUT["348_total_rows"].get("data"), "| 350 合计行:", OUT["350_total_rows"].get("data"))
    bd = OUT["325_buckets_20261106"].get("data") or []
    print("325 2026-11-06 桶数:", len(bd), "| 首尾:", bd[:2], bd[-1:], "| SUM 全桶:", sum((r.get("v") or 0) for r in bd))
    for k in ("today_force", "20261106_force"):
        x = OUT["323_cold"][k]
        print("323 取药冷查", k, "%ss" % x.get("sec"), "value:", v(x))
    print("322 采血冷查 %ss | 326 超声冷查 %ss" % (OUT["322_cold_20261106_force"].get("sec"), OUT["326_cold_20261106_force"].get("sec")))
    for k in ("guest_371_on_72", "guest_379_on_73", "guest_386_on_74"):
        x = OUT[k]
        print("003158", k, "http=%s" % x.get("http"), "value:", v(x))
    print("003158 GET dashboard 72/74 meta:", OUT["guest_dash72_meta"], OUT["guest_dash74_meta"])


if __name__ == "__main__":
    main()
