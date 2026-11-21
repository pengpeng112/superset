# -*- coding: utf-8 -*-
"""阶段0c：10月显式窗权威对账 + Gamma 经 dashboard 上下文访问实测。输出到 nursing_sql_recon.json。"""
import json
import os
import sys
import time

sys.path.insert(0, r"F:\python\superset\migration\sources\20261107-BI-DASHBOARDS")
from bi_api import admin, guest, q, S, BASE  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OCT = "2026-10-01 : 2026-11-01"
W_NO = "KS NOT IN ('合计','总计','全院','计')"


def agg(col, label=None):
    return {"expressionType": "SIMPLE", "column": {"column_name": col}, "aggregate": "SUM", "label": label or col}


def sqlm(expr, label):
    return {"expressionType": "SQL", "sqlExpression": expr, "label": label}


def main():
    s = admin()
    g = guest()
    outp = os.path.join(HERE, "evidence", "nursing_sql_recon.json")
    rec = json.load(open(outp, encoding="utf-8"))
    rec["oct"] = {}

    def probe(key, ds, query, viz="table"):
        x = q(s, ds, query, viz=viz, force=True)
        rec["oct"][key] = {"http": x.get("http"), "sec": x.get("sec"), "rows": x.get("rows"),
                           "err": (x.get("err") or "")[:150], "data": (x.get("data") or [])[:60]}
        print("%-20s http=%s %.1fs rows=%s %s" % (key, x.get("http"), x.get("sec"), x.get("rows"),
                                                  json.dumps((x.get("data") or [])[:2], ensure_ascii=False)[:220]), flush=True)
        return x

    # 10 月权威对账（excl 合计）
    probe("ds350.Oct.KPI", 350, {"columns": [], "metrics": [agg("OPEN_DAYS", "开放床日"), agg("USED_DAYS", "占用床日"),
                                                            agg("DISCH_N", "出院"), agg("BED_END", "实有床位"), agg("OCC_DAYS", "出院者占用床日")],
                                  "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": OCT}],
                                  "extras": {"having": "", "where": W_NO}, "row_limit": 5})
    probe("ds350.Oct.useRate", 350, {"columns": [], "metrics": [sqlm("SUM(USED_DAYS)/NULLIF(SUM(OPEN_DAYS),0)", "病床使用率")],
                                     "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": OCT}],
                                     "extras": {"having": "", "where": W_NO}, "row_limit": 5})
    xbar = probe("ds350.Oct.byKS", 350, {"columns": ["KS"], "metrics": [agg("DISCH_N", "出院人数"), agg("USED_DAYS", "占用床日")],
                                         "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": OCT}],
                                         "extras": {"having": "", "where": W_NO}, "row_limit": 60, "order_desc": True})
    probe("ds351.Oct.levels", 351, {"columns": [], "metrics": [agg("SPEC_CARE", "特级护理"), agg("CRIT_ILL", "病危"), agg("CRIT_SEVERE", "病重"),
                                                               agg("GEN_LVL1", "普通护理"), agg("LVL2", "二级护理"), agg("LVL3", "三级护理")],
                                     "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": OCT}],
                                     "extras": {"having": "", "where": W_NO}, "row_limit": 5})
    # 明细和 = 合计行对账（byKS 出院之和 vs KPI 出院）
    rows = rec["oct"]["ds350.Oct.byKS"]["data"] or []
    ssum = sum((r.get("出院人数") or 0) for r in rows)
    kpi = (rec["oct"]["ds350.Oct.KPI"]["data"] or [{}])[0]
    rec["oct"]["recon_detail_vs_kpi"] = {"byKS_sum": ssum, "kpi_disch": kpi.get("出院"),
                                         "equal": ssum == kpi.get("出院"), "units": len(rows)}
    print("对账: byKS明细和=%s vs KPI出院=%s equal=%s units=%s" % (ssum, kpi.get("出院"), ssum == kpi.get("出院"), len(rows)), flush=True)

    # Gamma 经 dashboard 上下文访问实测：找 ds350/351 现役图表
    chart_map = {}
    page = 0
    while True:
        r = s.get(BASE + "/api/v1/chart/?q=" + json.dumps({"page": page, "page_size": 100}), timeout=60)
        for it in r.json()["result"]:
            chart_map[it["id"]] = it
        cnt = r.json().get("count", 0)
        if (page + 1) * 100 >= cnt:
            break
        page += 1
    ds_charts = {}
    for cid, it in chart_map.items():
        dsn = it.get("datasource_name") or ""
        full = dsn
        ds_charts.setdefault(it.get("datasource_id"), []).append(cid)
    rec["charts_by_ds"] = {str(k): v for k, v in ds_charts.items() if k in (350, 351, 349, 352, 355)}
    print("charts by ds:", rec["charts_by_ds"], flush=True)

    rec["gamma_dash_ctx"] = {}
    for ds in (350, 351):
        cids = ds_charts.get(ds) or []
        if not cids:
            rec["gamma_dash_ctx"][str(ds)] = {"note": "无现役图表，待 75 上线后按 dashboard_id 实测"}
            continue
        cid = cids[0]
        # 找该图表所在看板
        dids = []
        ch = s.get(BASE + "/api/v1/chart/%d" % cid, timeout=30).json()["result"]
        for dd in ch.get("dashboards") or []:
            dids.append(dd.get("id") or dd.get("value"))
        did = next((d for d in dids if d and d < 72), None) or (dids[0] if dids else None)
        if did:
            rr = g.post(BASE + "/api/v1/chart/data?form_data=%s&dashboard_id=%d" % (json.dumps({"slice_id": cid}), did),
                        json={"datasource": {"id": ds, "type": "table"}, "force": False,
                              "queries": [{"filters": [], "metrics": [agg("BED_END", "床位")], "row_limit": 1,
                                           "extras": {"having": "", "where": ""}}],
                              "form_data": {"datasource": "%d__table" % ds, "viz_type": "table", "slice_id": cid},
                              "result_format": "json", "result_type": "full"}, timeout=120)
            rec["gamma_dash_ctx"][str(ds)] = {"http": rr.status_code, "chart": cid, "dashboard": did,
                                              "body": rr.text[:200] if not rr.ok else ""}
        else:
            rec["gamma_dash_ctx"][str(ds)] = {"note": "图表无关联看板", "chart": cid}
        print("gamma dash-ctx ds%s -> %s" % (ds, rec["gamma_dash_ctx"][str(ds)]), flush=True)

    json.dump(rec, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("saved", outp)


if __name__ == "__main__":
    main()
