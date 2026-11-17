# -*- coding: utf-8 -*-
"""20261107-BI-DASHBOARDS T2 口径与配置修复（计划 §6）。
只改本批图表（id>354）params / 名称 / 数据源；73 筛选 targets；74 新增门诊手术台数并重排 position_json。
凭据环境变量 ACC_ADMIN。"""
import json
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from bi_api import *  # noqa

DRY = "--dry" in sys.argv


def F(subject, op, comp, name):
    return {"clause": "WHERE", "expressionType": "SIMPLE", "subject": subject, "operator": op,
            "comparator": comp, "filterOptionName": name, "isExtra": False, "isNew": False, "sqlExpression": None}


s = admin()

# ---------- 1) 逐图修 params ----------
def patch_chart(cid, gran=None, adhoc=None, metric=None, name=None, datasource=None, drop_metrics=None):
    p, c = chart_params(s, cid)
    before = json.dumps(p, ensure_ascii=False)
    if gran:
        p["granularity_sqla"] = gran
    if adhoc is not None:
        p["adhoc_filters"] = adhoc
    if metric is not None:
        p["metric"] = metric
    if drop_metrics:
        p["metrics"] = [m for m in p["metrics"] if m.get("label") not in drop_metrics]
    extra = {}
    if name:
        extra["slice_name"] = name
    if datasource:
        p["datasource"] = "%d__table" % datasource
        extra["datasource_id"] = datasource
    if DRY:
        print("DRY chart %d: %s" % (cid, "gran/adhoc/name/ds" if (gran or adhoc or name or datasource) else "no-op"))
        return
    sc, err = put_params(s, cid, p, extra or None)
    c2 = get_chart(s, cid)
    p2 = json.loads(c2["params"])
    ok = (not gran or p2.get("granularity_sqla") == gran) and \
         (adhoc is None or p2.get("adhoc_filters") == adhoc) and \
         (not name or c2["slice_name"] == name) and \
         (not datasource or c2["datasource_id"] == datasource) and \
         (not drop_metrics or [m.get("label") for m in p2["metrics"]] == [m.get("label") for m in p["metrics"]])
    print("chart %d PUT=%s verify=%s %s" % (cid, sc, "OK" if ok else "MISMATCH", err[:120]))
    if not ok:
        print("  got:", json.dumps({"gran": p2.get("granularity_sqla"), "adhoc": p2.get("adhoc_filters"),
                                    "name": c2["slice_name"], "ds": c2["datasource_id"],
                                    "labels": [m.get("label") for m in p2.get("metrics", [])]}, ensure_ascii=False)[:400])


SB, SD = "STAT_BEGIN", "STAT_DATE"
CNT = {"expressionType": "SIMPLE", "column": {"column_name": "COUNT(*)"}, "aggregate": "SUM"}

# —— 72：granularity=STAT_BEGIN；378 排除总计；377 转归五项 ——
patch_chart(371, gran=SB)
patch_chart(372, gran=SB)
patch_chart(373, gran=SB)
patch_chart(374, gran=SB)
patch_chart(375, gran=SB)
patch_chart(376, gran=SB)
patch_chart(377, gran=SB, drop_metrics=["自动出院", "转院"])
patch_chart(378, gran=SB, adhoc=[F("KS", "NOT IN", ["总计", "合计"], "bi378_ex_total")])

# —— 73：granularity=STAT_DATE；KPI 取 17:00 桶并改名；381 换 ds326 超声 ——
D17 = lambda n: F("DTIME", "==", "17:00", n)
patch_chart(379, gran=SD, adhoc=[D17("bi379_d1700")], name="【BI】截至17:00挂号人次")
patch_chart(380, gran=SD, adhoc=[D17("bi380_d1700")], name="【BI】截至17:00缴费人次")
patch_chart(381, gran=SD, adhoc=[D17("bi381_d1700")], metric=CNT, datasource=326, name="【BI】截至17:00超声人次")
patch_chart(382, gran=SD, adhoc=[D17("bi382_d1700")], name="【BI】截至17:00采血人次")
patch_chart(383, gran=SD)
patch_chart(384, gran=SD)
patch_chart(385, gran=SD, name="【BI】门诊挂号分时段明细表")

# —— 74：granularity=STAT_BEGIN；386 只取合计行；387 排除合计；390/391 排除合计 ——
patch_chart(386, gran=SB, adhoc=[F("TJ_KSMC", "==", "合计", "bi386_total_row")], name="【BI】住院手术台数")
patch_chart(387, gran=SB, adhoc=[F("TJ_KSMC", "NOT IN", ["合计"], "bi387_ex_total")], name="【BI】住院手术科室 TOP15")
patch_chart(389, gran=SB)
patch_chart(390, gran=SB, adhoc=[F("KS", "NOT IN", ["合计"], "bi390_ex_total")])
patch_chart(391, gran=SB, adhoc=[F("KS", "NOT IN", ["合计"], "bi391_ex_total")])

# ---------- 2) 新增「门诊手术台数」并挂看板 74 ----------
NEW_PARAMS = {
    "viz_type": "big_number_total", "datasource": "345__table",
    "metric": {"expressionType": "SIMPLE", "column": {"column_name": "OPER_NUM"}, "aggregate": "SUM", "label": "门诊手术台数"},
    "granularity_sqla": SB,
    "adhoc_filters": [F("BRANCH_NAME", "IN", ["门诊"], "bi_mz_branch"), F("TJ_KSMC", "==", "合计", "bi_mz_total_row")],
    "compare_lag": "", "compare_suffix": "", "y_axis_format": ",d", "date_format": "smart_date",
    "subheader": "门诊分支合计行", "time_range": "No filter",
}
if DRY:
    print("DRY: would create chart 门诊手术台数 + re-layout d74 + fix d73 targets")
    sys.exit(0)

r = s.post(BASE + "/api/v1/chart/", json={
    "slice_name": "【BI】门诊手术台数", "viz_type": "big_number_total",
    "datasource_id": 345, "datasource_type": "table", "dashboards": [74],
    "params": json.dumps(NEW_PARAMS, ensure_ascii=False)}, timeout=60)
print("create chart ->", r.status_code, r.text[:200] if not r.ok else "")
new_id = r.json().get("id")
print("new chart id =", new_id)

# ---------- 3) 73 原生筛选 targets：325/324/322/326（去掉 323） ----------
d73 = get_dashboard(s, 73)
md = json.loads(d73["json_metadata"])
nf = md["native_filter_configuration"][0]
nf["targets"] = [{"datasetId": 325, "column": {"name": "STAT_DATE"}},
                 {"datasetId": 324, "column": {"name": "STAT_DATE"}},
                 {"datasetId": 322, "column": {"name": "STAT_DATE"}},
                 {"datasetId": 326, "column": {"name": "STAT_DATE"}}]
r = s.put(BASE + "/api/v1/dashboard/73", json={"json_metadata": json.dumps(md, ensure_ascii=False)}, timeout=60)
print("d73 targets PUT ->", r.status_code)
md2 = json.loads(get_dashboard(s, 73)["json_metadata"])
print("d73 targets now:", [t["datasetId"] for t in md2["native_filter_configuration"][0]["targets"]])

# ---------- 4) 74 position_json 重排：行1 门诊/住院/389，行2 387+390，行3 391 ----------
pos = json.loads(get_dashboard(s, 74)["position_json"])
for k in ("CHART-BI3-1-0", "CHART-BI3-1-1", "CHART-BI3-1-2", "CHART-BI3-2-0", "CHART-BI3-2-1", "CHART-BI3-3-0", "ROW-BI3-1", "ROW-BI3-2", "ROW-BI3-3"):
    pos.pop(k, None)
CH = lambda key, cid, w, h: {key: {"id": key, "type": "CHART", "children": [], "meta": {"chartId": cid, "width": w, "height": h}}}
ROW = lambda key, ch: {key: {"id": key, "type": "ROW", "children": ch, "meta": {"background": "BACKGROUND_TRANSPARENT"}}}
pos.update(CH("CHART-BI3-1-0", new_id, 3, 8))
pos.update(CH("CHART-BI3-1-1", 386, 3, 8))
pos.update(CH("CHART-BI3-1-2", 389, 6, 8))
pos.update(ROW("ROW-BI3-1", ["CHART-BI3-1-0", "CHART-BI3-1-1", "CHART-BI3-1-2"]))
pos.update(CH("CHART-BI3-2-0", 387, 6, 14))
pos.update(CH("CHART-BI3-2-1", 390, 6, 14))
pos.update(ROW("ROW-BI3-2", ["CHART-BI3-2-0", "CHART-BI3-2-1"]))
pos.update(CH("CHART-BI3-3-0", 391, 12, 14))
pos.update(ROW("ROW-BI3-3", ["CHART-BI3-3-0"]))
pos["GRID_ID"]["children"] = ["MD-TOP", "ROW-BI3-1", "ROW-BI3-2", "ROW-BI3-3"]
r = s.put(BASE + "/api/v1/dashboard/74", json={"position_json": json.dumps(pos, ensure_ascii=False)}, timeout=60)
print("d74 position PUT ->", r.status_code, r.text[:200] if not r.ok else "")
print("done")
