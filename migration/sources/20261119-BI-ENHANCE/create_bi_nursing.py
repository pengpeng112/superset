# -*- coding: utf-8 -*-
"""20261119-BI-ENHANCE 阶段1：创建第 4 个 BI 驾驶舱（slug=bi-nursing-bed）。
继承 20261107-BI-DASHBOARDS 铁律：
  ①柱图/饼图排除 合计/总计/全院 行（adhoc NOT IN）；
  ②饼图度量 label 绝不与物理列名同名（防 ORA-00935）；
  ③全部对象 UUID/ID 记入 bi_enhance_ledger.json，rollback_bi_enhance.py 支持 --dry-run。
数据集零新建（复用 ds350 护理月报主表 + ds351 护理日报主表）；零 SQL/口径改动。
默认时间窗 = 2026-10-01 : 2026-11-01（阶段0 核实的最新完整月，十月出院 5315）。
凭据环境变量 ACC_ADMIN。
"""
import json
import os
import sys
import time

sys.path.insert(0, r"F:\python\superset\migration\sources\20261107-BI-DASHBOARDS")
from bi_api import admin, q, BASE  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER_PATH = os.path.join(HERE, "bi_enhance_ledger.json")
LEDGER = {"created_at": "", "batch": "20261119-BI-ENHANCE", "charts": [], "dashboards": [],
          "gamma_grants": [], "precheck": [], "new_datasets": []}
GAMMA_ID = 4
DS_MONTH = 350   # 护理工作量月报表·主表（月度，STAT_BEGIN=月初标记）
DS_DAY = 351     # 护理工作量日报表·主表（分级护理，当前统计日快照口径）
DEFAULT_RANGE = "2026-10-01 : 2026-11-01"
W_EXCL = {"clause": "WHERE", "expressionType": "SIMPLE", "subject": "KS",
          "operator": "NOT IN", "comparator": ["合计", "总计", "全院", "计"],
          "filterOptionName": "bi4_ex_total", "isExtra": False, "isNew": False, "sqlExpression": None}

s = None


def agg(col, label=None):
    return {"expressionType": "SIMPLE", "column": {"column_name": col}, "aggregate": "SUM",
            "label": label or col, "hasCustomLabel": bool(label)}


def sqlm(expr, label):
    return {"expressionType": "SQL", "sqlExpression": expr, "label": label}


def record_ledger():
    with open(LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(LEDGER, f, ensure_ascii=False, indent=1)


def find_chart(name):
    r = s.get(BASE + "/api/v1/chart/?q=" + json.dumps({"filters": [{"col": "slice_name", "opr": "eq", "value": name}]}), timeout=30)
    d = r.json()
    if d.get("count") and d["count"] > 0:
        return d["result"][0]["id"]
    r2 = s.get(BASE + "/api/v1/chart/?q=(page_size:1)", timeout=30)
    return None


def find_dashboard(slug):
    r = s.get(BASE + "/api/v1/dashboard/?q=" + json.dumps({"filters": [{"col": "slug", "opr": "eq", "value": slug}]}), timeout=30)
    d = r.json()
    if d.get("count") and d["count"] > 0:
        return d["result"][0]["id"]
    return None


def precheck(name, ds, query, min_rows=1):
    qk = dict({"filters": [], "row_limit": 50000, "extras": {"having": "", "where": ""}}, **query)
    payload = {"datasource": {"id": ds, "type": "table"}, "force": True,
               "queries": [qk],
               "form_data": {"datasource": "%d__table" % ds, "viz_type": "table"},
               "result_format": "json", "result_type": "full"}
    t0 = time.time()
    rr = s.post(BASE + "/api/v1/chart/data", json=payload, timeout=300)
    dt = round(time.time() - t0, 1)
    ok = rr.ok
    rows = rr.json()["result"][0].get("rowcount") if ok else None
    data0 = rr.json()["result"][0].get("data") if ok else None
    rec = {"name": name, "dataset": ds, "http": rr.status_code, "rows": rows, "seconds": dt}
    LEDGER["precheck"].append(rec)
    print("  precheck %-34s %5.1fs http=%s rows=%s %s" % (name, dt, rr.status_code, rows,
          json.dumps((data0 or [])[:2], ensure_ascii=False)[:160]), flush=True)
    if not ok or (rows or 0) < min_rows:
        print("  ERROR BODY:", rr.text[:400])
        raise SystemExit("ABORT: precheck failed %s" % json.dumps(rec, ensure_ascii=False))
    record_ledger()
    return dt, data0


def qc(ds, qq):
    return {"datasource": {"id": ds, "type": "table"}, "force": False,
            "queries": [dict({"filters": [], "extras": {"having": "", "where": ""}, "applied_time_extras": {},
                              "orderby": [], "annotation_layers": [], "series_limit": 0,
                              "group_others_when_limit_reached": False, "order_desc": True,
                              "url_params": {}, "custom_params": {}, "custom_form_data": {},
                              "post_processing": [], "time_offsets": [], "row_limit": 50000}, **qq)],
            "form_data": {"datasource": "%d__table" % ds}, "result_format": "json", "result_type": "full"}


def mk_chart(spec):
    """spec: {name, ds, viz, params, query, min_rows}"""
    sid = find_chart(spec["name"])
    if sid:
        print("  chart exists id=%s %s" % (sid, spec["name"]))
        rec = next((c for c in LEDGER["charts"] if c["id"] == sid), None)
        if not rec:
            r = s.get(BASE + "/api/v1/chart/%d" % sid, timeout=30)
            LEDGER["charts"].append({"type": "chart", "id": sid, "uuid": r.json()["result"].get("uuid"),
                                     "title": spec["name"], "preexisting": True})
            record_ledger()
        return sid
    body = {
        "slice_name": spec["name"],
        "datasource_id": spec["ds"],
        "datasource_type": "table",
        "viz_type": spec["viz"],
        "params": json.dumps(spec["params"], ensure_ascii=False),
        "query_context": json.dumps(qc(spec["ds"], spec["query"]), ensure_ascii=False),
    }
    r = s.post(BASE + "/api/v1/chart/", json=body, timeout=60)
    if r.status_code not in (200, 201):
        print(r.text[:600])
        raise SystemExit("ABORT: chart create failed: " + spec["name"])
    sid = r.json()["id"]
    uuid = s.get(BASE + "/api/v1/chart/%d" % sid, timeout=30).json()["result"].get("uuid")
    LEDGER["charts"].append({"type": "chart", "id": sid, "uuid": uuid, "title": spec["name"]})
    record_ledger()
    print("  created chart id=%s %s" % (sid, spec["name"]))
    dt, _ = precheck("chart:" + spec["name"], spec["ds"], spec["query"], spec.get("min_rows", 1))
    rec = next(c for c in LEDGER["charts"] if c["id"] == sid)
    rec["precheck_seconds"] = dt
    record_ledger()
    return sid


def kpi_big_number(ds, metric, title, subheader=""):
    q = {"metrics": [metric]}
    params = {"viz_type": "big_number_total", "datasource": "%d__table" % ds, "metric": metric,
              "granularity_sqla": "STAT_BEGIN", "adhoc_filters": [W_EXCL],
              "compare_lag": "", "compare_suffix": "", "y_axis_format": ",d",
              "date_format": "smart_date", "subheader": subheader, "time_range": "No filter"}
    return {"ds": ds, "viz": "big_number_total", "params": params, "query": q, "min_rows": 1}


def main():
    global s
    s = admin()
    LEDGER["created_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    did = find_dashboard("bi-nursing-bed")
    if did:
        print("dashboard bi-nursing-bed exists id=%s — 幂等续作（图表按名复用，元数据重配）" % did)
        r0 = s.get(BASE + "/api/v1/dashboard/%d" % did, timeout=30).json()["result"]
        LEDGER["dashboards"].append({"type": "dashboard", "id": did, "uuid": r0.get("uuid"), "slug": "bi-nursing-bed",
                                     "title": "全院护理工作量与病区床位效率分析", "roles": [GAMMA_ID], "resumed": True})
        record_ledger()

    print("== 预检（force 冷查）==")
    # KPI 预检（十月显式窗）
    oct_q = {"metrics": [agg("OPEN_DAYS", "开放床日")],
             "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": DEFAULT_RANGE}]}
    precheck("KPI 开放床日", DS_MONTH, oct_q)
    precheck("KPI 占用床日", DS_MONTH, dict(oct_q, metrics=[agg("USED_DAYS", "占用床日")]))
    precheck("KPI 出院", DS_MONTH, dict(oct_q, metrics=[agg("DISCH_N", "出院")]))
    precheck("KPI 使用率", DS_MONTH, dict(oct_q, metrics=[sqlm("SUM(USED_DAYS)/NULLIF(SUM(OPEN_DAYS),0)", "病床使用率")]))
    precheck("TOP15 柱图", DS_MONTH, {"columns": ["KS"], "metrics": [agg("DISCH_N", "出院人数")],
                                      "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": DEFAULT_RANGE}],
                                      "row_limit": 15, "order_desc": True})
    precheck("饼图级别", DS_DAY, {"metrics": [agg("SPEC_CARE", "特级护理"), agg("CRIT_ILL", "病危"), agg("CRIT_SEVERE", "病重"),
                                             agg("GEN_LVL1", "普通护理"), agg("LVL2", "二级护理"), agg("LVL3", "三级护理")],
                                  "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": DEFAULT_RANGE}]})
    precheck("汇总表", DS_MONTH, {"columns": ["KS"], "metrics": [agg("DISCH_N", "出院人数"), agg("BED_END", "月末实有病床")],
                                  "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": DEFAULT_RANGE}],
                                  "row_limit": 50})

    print("== 创建图表 ==")
    charts = []
    # 第一层 KPI ×4（ds350，十月）
    charts.append(mk_chart(kpi_big_number(DS_MONTH, agg("OPEN_DAYS", "实际开放总床日数"), "实际开放总床日数", "2026-10 全院合计") | {"name": "【BI】实际开放总床日数"}))
    charts.append(mk_chart(kpi_big_number(DS_MONTH, agg("USED_DAYS", "实际占用总床日数"), "实际占用总床日数", "2026-10 全院合计") | {"name": "【BI】实际占用总床日数"}))
    charts.append(mk_chart(kpi_big_number(DS_MONTH, agg("DISCH_N", "出院总人数"), "出院总人数", "2026-10 全院合计") | {"name": "【BI】出院总人数"}))
    charts.append(mk_chart({
        "ds": DS_MONTH, "viz": "big_number_total",
        "params": {"viz_type": "big_number_total", "datasource": "%d__table" % DS_MONTH,
                   "metric": sqlm("SUM(USED_DAYS)/NULLIF(SUM(OPEN_DAYS),0)", "病床使用率"),
                   "granularity_sqla": "STAT_BEGIN", "adhoc_filters": [W_EXCL],
                   "compare_lag": "", "compare_suffix": "", "y_axis_format": ".1%",
                   "date_format": "smart_date", "subheader": "占用床日/开放床日", "time_range": "No filter"},
        "query": {"metrics": [sqlm("SUM(USED_DAYS)/NULLIF(SUM(OPEN_DAYS),0)", "病床使用率")]},
        "min_rows": 1} | {"name": "【BI】病床使用率"}))
    # 第二层左：TOP15 柱图（echarts_timeseries_bar，390 母版）
    charts.append(mk_chart({
        "ds": DS_MONTH, "viz": "echarts_timeseries_bar",
        "params": {"viz_type": "echarts_timeseries_bar", "datasource": "%d__table" % DS_MONTH,
                   "granularity_sqla": "STAT_BEGIN", "x_axis": "KS", "groupby": [],
                   "metrics": [agg("DISCH_N", "出院人数")], "adhoc_filters": [W_EXCL],
                   "row_limit": 15, "order_desc": True, "sort_by_metric": True, "truncate_metric": True,
                   "show_value": True, "show_legend": False, "rich_tooltip": True,
                   "y_axis_format": ",d", "color_scheme": "supersetColors", "time_range": "No filter"},
        "query": {"columns": ["KS"], "metrics": [agg("DISCH_N", "出院人数")],
                  "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": DEFAULT_RANGE}],
                  "row_limit": 15, "order_desc": True},
        "min_rows": 3} | {"name": "【BI】各护理单元出院人数 TOP15"}))
    # 第二层右：环形饼（389 母版；度量 label 均与物理列名不同，防 ORA-00935）
    charts.append(mk_chart({
        "ds": DS_DAY, "viz": "pie",
        "params": {"viz_type": "pie", "datasource": "%d__table" % DS_DAY,
                   "granularity_sqla": "STAT_BEGIN",
                   "metrics": [agg("SPEC_CARE", "特级护理"), agg("CRIT_ILL", "病危"), agg("CRIT_SEVERE", "病重"),
                               agg("GEN_LVL1", "普通护理"), agg("LVL2", "二级护理"), agg("LVL3", "三级护理")],
                   "groupby": [], "adhoc_filters": [W_EXCL],
                   "row_limit": 10, "donut": True, "show_legend": True, "legendPosition": "right",
                   "show_labels": True, "label_type": "name_value", "number_format": ",d",
                   "outerRadius": 70, "innerRadius": 40, "color_scheme": "supersetColors",
                   "time_range": "No filter", "date_format": "smart_date"},
        "query": {"metrics": [agg("SPEC_CARE", "特级护理"), agg("CRIT_ILL", "病危"), agg("CRIT_SEVERE", "病重"),
                              agg("GEN_LVL1", "普通护理"), agg("LVL2", "二级护理"), agg("LVL3", "三级护理")],
                  "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": DEFAULT_RANGE}]},
        "min_rows": 1} | {"name": "【BI】护理级别人日结构"}))
    # 第三层：汇总表（391 母版；比率列沿用 391 的 SUM 语义——月窗内每单元 1 行）
    charts.append(mk_chart({
        "ds": DS_MONTH, "viz": "table",
        "params": {"viz_type": "table", "datasource": "%d__table" % DS_MONTH, "query_mode": "aggregate",
                   "groupby": ["KS"],
                   "metrics": [agg("DISCH_N", "出院人数"), agg("BED_END", "月末实有病床"),
                               agg("OPEN_DAYS", "实际开放总床日"), agg("USED_DAYS", "实际占用总床日"),
                               agg("OCC_DAYS", "出院者占用总床日"),
                               sqlm("SUM(USED_DAYS)/NULLIF(SUM(OPEN_DAYS),0)", "病床使用率"),
                               agg("TURNOVER", "病床周转次数"), agg("AVG_LOS", "平均住院日"),
                               agg("CURE_RATE", "治愈率(%)"), agg("DEATH_RATE", "病死率(%)")],
                   "adhoc_filters": [W_EXCL],
                   "row_limit": 50, "page_length": 25, "server_pagination": False,
                   "include_search": True, "include_time": False, "order_desc": True,
                   "table_timestamp_format": "%Y-%m-%d", "time_range": "No filter",
                   "column_config": {}, "granularity_sqla": "STAT_BEGIN"},
        "query": {"columns": ["KS"], "metrics": [agg("DISCH_N", "出院人数"), agg("BED_END", "月末实有病床")],
                  "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": DEFAULT_RANGE}],
                  "row_limit": 50},
        "min_rows": 3} | {"name": "【BI】各护理单元工作量与床位效率明细汇总表"}))

    print("== 创建/续配看板 ==")
    if not did:
        r = s.post(BASE + "/api/v1/dashboard/", json={"dashboard_title": "全院护理工作量与病区床位效率分析", "slug": "bi-nursing-bed"}, timeout=60)
        if r.status_code not in (200, 201):
            print(r.text[:500])
            raise SystemExit("ABORT: dashboard create failed")
        did = r.json()["id"]
        uuid = s.get(BASE + "/api/v1/dashboard/%d" % did, timeout=30).json()["result"].get("uuid")
        LEDGER["dashboards"].append({"type": "dashboard", "id": did, "uuid": uuid, "slug": "bi-nursing-bed",
                                     "title": "全院护理工作量与病区床位效率分析", "roles": [GAMMA_ID]})
        record_ledger()
        print("  created dashboard id=%s uuid=%s" % (did, uuid))

    desc_md = ("**全院护理工作量与病区床位效率分析**　基于护理工作量月报表（ds350）与护理日报表（ds351）已对账数据集；"
               "默认展示 2026-10（顶部日期筛选联动全部图表）。柱图与汇总表均排除“合计”行；"
               "护理级别人日结构为当前统计日快照口径（日报源表仅保留最新统计日级别数据）。")
    pos = {"DASHBOARD_VERSION_KEY": "v2", "ROOT_ID": {"id": "ROOT_ID", "type": "ROOT", "children": ["GRID_ID"]},
           "GRID_ID": {"id": "GRID_ID", "type": "GRID", "children": []}}
    rows_spec = [[(charts[0], 3, 8), (charts[1], 3, 8), (charts[2], 3, 8), (charts[3], 3, 8)],
                 [(charts[4], 7, 14), (charts[5], 5, 14)],
                 [(charts[6], 12, 14)]]
    children = []
    pos["MD-TOP"] = {"id": "MD-TOP", "type": "MARKDOWN", "children": [],
                     "meta": {"width": 12, "height": 4, "background": "BACKGROUND_TRANSPARENT",
                              "text": desc_md, "code": desc_md}}
    children.append("MD-TOP")
    for ri, row in enumerate(rows_spec, 1):
        rid = "ROW-BI4-%d" % ri
        node_children = []
        for ci, (cid, w, h) in enumerate(row):
            key = "CHART-BI4-%d-%d" % (ri, ci)
            pos[key] = {"id": key, "type": "CHART", "children": [], "meta": {"chartId": cid, "width": w, "height": h}}
            node_children.append(key)
        pos[rid] = {"id": rid, "type": "ROW", "children": node_children, "meta": {"background": "BACKGROUND_TRANSPARENT"}}
        children.append(rid)
    pos["GRID_ID"]["children"] = children
    r4 = s.put(BASE + "/api/v1/dashboard/%d" % did, json={"position_json": json.dumps(pos, ensure_ascii=False)}, timeout=60)
    if not r4.ok:
        print(r4.text[:400])
        raise SystemExit("ABORT: position_json failed")
    jm = {"filter_bar_orientation": "HORIZONTAL",
          "native_filter_configuration": [{
              "id": "NATIVE-FILTER-BI4-DATE", "name": "统计日期", "filterType": "filter_time",
              "targets": [{"datasetId": DS_MONTH, "column": {"name": "STAT_BEGIN"}},
                          {"datasetId": DS_DAY, "column": {"name": "STAT_BEGIN"}}],
              "defaultDataMask": {"extraFormData": {"time_range": DEFAULT_RANGE},
                                  "filterState": {"value": DEFAULT_RANGE}, "ownState": {}},
              "cascadeParentIds": [], "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
              "controlValues": {"enableEmptyFilter": False},
              "type": "NATIVE_FILTER", "chartsInScope": charts, "tabsInScope": [],
              "description": "选择日期范围后点击“查询”，全部图表联动刷新。"}],
          "timed_refresh_immune_slices": [], "expanded_slices": {}, "refresh_frequency": 0,
          "color_scheme": "", "label_colors": {}, "shared_label_colors": {}, "map_label_colors": {},
          "color_scheme_domain": [], "cross_filters_enabled": False,
          "default_filters": "{}",
          "chart_configuration": dict(("%d" % c, {"id": c, "crossFilters": {"chartsInScope": [], "scope": "global"}}) for c in charts),
          "global_chart_configuration": {"chartsInScope": charts, "scope": {"excluded": [], "rootPath": ["ROOT_ID"]}}}
    r5 = s.put(BASE + "/api/v1/dashboard/%d" % did, json={"json_metadata": json.dumps(jm, ensure_ascii=False)}, timeout=60)
    if not r5.ok:
        print(r5.text[:400])
        raise SystemExit("ABORT: json_metadata failed")
    r6 = s.put(BASE + "/api/v1/dashboard/%d" % did, json={"published": True}, timeout=60)
    if not r6.ok:
        raise SystemExit("ABORT: publish failed")
    r7 = s.put(BASE + "/api/v1/dashboard/%d/roles" % did, json={"roles": [GAMMA_ID]}, timeout=60)
    rec = next(d for d in LEDGER["dashboards"] if d["id"] == did)
    rec["published"] = True
    rec["roles_put_status"] = r7.status_code
    record_ledger()
    print("  dashboard %s configured (published, gamma=%s)" % (did, r7.status_code))
    print("DONE did=%s charts=%s" % (did, charts))


if __name__ == "__main__":
    main()
