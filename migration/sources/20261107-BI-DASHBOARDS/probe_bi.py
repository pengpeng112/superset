# -*- coding: utf-8 -*-
"""20261107-BI-DASHBOARDS 预检：每个拟用图表的 chart/data 查询真实耗时（默认窗/指定窗）。
凭据环境变量 ACC_ADMIN。全部只读。"""
import json
import os
import re
import sys
import time

import requests

BASE = "http://127.0.0.1:18180"
s = requests.Session()
s.headers["User-Agent"] = "bi-probe/1.0"


def login():
    r = s.get(BASE + "/login/", timeout=30)
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text).group(1)
    s.post(BASE + "/login/", data={"username": "admin", "password": os.environ["ACC_ADMIN"], "csrf_token": tok}, timeout=30)
    return tok


def query(name, ds_id, q, expect_rows=None):
    payload = {
        "datasource": {"id": ds_id, "type": "table"},
        "force": False,
        "queries": [dict({
            "filters": [], "extras": {"having": "", "where": ""}, "applied_time_extras": {},
            "orderby": [], "annotation_layers": [], "series_limit": 0,
            "group_others_when_limit_reached": False, "order_desc": True,
            "url_params": {}, "custom_params": {}, "custom_form_data": {},
            "post_processing": [], "time_offsets": [], "row_limit": 50000,
        }, **q)],
        "form_data": {"datasource": "%d__table" % ds_id, "viz_type": "table"},
        "result_format": "json", "result_type": "full",
    }
    t0 = time.time()
    rr = s.post(BASE + "/api/v1/chart/data", json=payload, timeout=300)
    dt = time.time() - t0
    ok = rr.ok
    rows = None
    if ok:
        j = rr.json()
        r0 = j["result"][0]
        rows = r0.get("rowcount")
        data = (r0.get("data") or [{}])[:2]
        print("%-38s %5.1fs rows=%s ok sample=%s" % (name, dt, rows, json.dumps(data, ensure_ascii=False)[:160]))
    else:
        print("%-38s %5.1fs HTTP %s %s" % (name, dt, rr.status_code, rr.text[:160]))
    return ok and (expect_rows is None or (rows or 0) > 0)


def adhoc_metric(label, expr):
    return {"expressionType": "SIMPLE", "column": None, "aggregate": None,
            "sqlExpression": expr, "label": label}


def simple_agg(col, agg):
    return {"expressionType": "SIMPLE", "column": {"column_name": col}, "aggregate": agg}


NOT_TOTAL = {"col": "KS", "op": "NOT IN", "value": ["总计", "计", "合计", "全院"]}


def main():
    login()
    KSDM_NT = {"col": "KSDM", "op": "NOT IN", "value": ["总计", "计", "合计", "全院"]}
    # BI-1
    query("KPI 门诊人次 347", 347, {"metrics": [simple_agg("MEN_ZHENS", "SUM")], "filters": [KSDM_NT]})
    query("KPI 急诊+观察 347", 347, {"metrics": [adhoc_metric("急诊观察", "SUM(JIZHENS)+SUM(GUANCHA)")], "filters": [KSDM_NT]})
    query("KPI 出院人数 338", 338, {"metrics": [simple_agg("CHUYUAN", "SUM")]})
    query("KPI 在院人数 338", 338, {"metrics": [simple_agg("CURR", "SUM")]})
    query("TOP15 门诊 347", 347, {"columns": ["KSDM"], "metrics": [simple_agg("MEN_ZHENS", "SUM")],
                                   "filters": [KSDM_NT], "row_limit": 16, "orderby": [[simple_agg("MEN_ZHENS", "SUM"), False]]})
    query("TOP15 出院 338", 338, {"columns": ["KSDM"], "metrics": [simple_agg("CHUYUAN", "SUM")],
                                   "row_limit": 16, "orderby": [[simple_agg("CHUYUAN", "SUM"), False]]})
    query("明细 348", 348, {"columns": ["KS"], "metrics": [simple_agg("DISCH_N", "SUM"), simple_agg("BED_END", "SUM"),
                                                            simple_agg("DEATH_RATE", "AVG")], "filters": [
        {"col": "KS", "op": "NOT IN", "value": ["总计", "计", "合计", "全院"]}]})
    # 转归构成（338 计行横列：先看计行的值）
    query("338 计行样本", 338, {"columns": ["KSDM", "RECOVER", "EFFECT", "UNTREAT", "DIED", "OTHER_N"],
                                 "filters": [{"col": "KSDM", "op": "IN", "value": ["总计", "计", "合计", "全院"]}]})
    # BI-2
    for ds, nm in ((325, "挂号"), (322, "采血"), (323, "取药"), (324, "缴费"), (326, "超声")):
        query("KPI %s %d" % (nm, ds), ds, {"metrics": [{"expressionType": "SIMPLE",
                                                        "column": {"column_name": "COUNT(*)"}, "aggregate": "SUM"}]})
    query("时段柱图 325", 325, {"columns": ["DTIME"], "metrics": [{"expressionType": "SIMPLE",
                                                                   "column": {"column_name": "COUNT(*)"}, "aggregate": "SUM"}]})
    # BI-3
    query("345 科室手术", 345, {"columns": ["TJ_KSMC"], "metrics": [simple_agg("OPER_NUM", "SUM")], "row_limit": 20})
    query("345 门诊住院饼", 345, {"columns": ["BRANCH_NAME"], "metrics": [simple_agg("OPER_NUM", "SUM")]})
    query("345 KPI 台数", 345, {"metrics": [simple_agg("OPER_NUM", "SUM")]})
    # 365 聚合可行性（剂型结构）——耗时决策
    query("365 剂型聚合(测速)", 365, {"columns": ["剂型"],
                                       "metrics": [{"expressionType": "SIMPLE", "column": {"column_name": "发药数量"}, "aggregate": "SUM"}],
                                       "row_limit": 30})


if __name__ == "__main__":
    main()
