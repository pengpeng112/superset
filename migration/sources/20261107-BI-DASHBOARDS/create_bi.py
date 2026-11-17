# -*- coding: utf-8 -*-
"""20261107-BI-DASHBOARDS 创建脚本（幂等）：3 个 BI 驾驶舱 + 20 张图表（全部新增对象）。

- 图表一律引用现有已对账数据集（347/338/348/322/323/324/325/326/345/350），不新建数据集、不触碰现有对象。
- 每图创建后立即 /api/v1/chart/data 预检（必须 200 且 rows>0），耗时记录 ledger。
- 看板 position_json + 原生 filter_time（BI-1 默认 2026-09-01~09-30；BI-2 空默认=SQL 今日兜底；BI-3 空默认=上月兜底），
  published=True，dashboard_roles 绑 Gamma(id=4)。
- 幂等：按 slice_name / dashboard_title 查重，已存在则复用。
- ledger：bi_created_ledger.json 实时记录 {type,id,uuid,title}；配套 rollback_bi.py 一键清理。
凭据环境变量 ACC_ADMIN。
"""
import json
import os
import re
import sys
import time

import requests

BASE = "http://127.0.0.1:18180"
HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER_PATH = os.path.join(HERE, "bi_created_ledger.json")
LEDGER = {"created_at": "", "charts": [], "dashboards": [], "precheck": []}
GAMMA_ID = 4
W_KSDM = "KSDM NOT IN ('总计','计','合计','全院')"
W_KS = "KS NOT IN ('总计','计','合计','全院')"

s = requests.Session()
CSRF = ""


def login():
    global CSRF
    r = s.get(BASE + "/login/", timeout=30)
    CSRF = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text).group(1)
    s.post(BASE + "/login/", data={"username": "admin", "password": os.environ["ACC_ADMIN"], "csrf_token": CSRF}, timeout=30)
    r2 = s.get(BASE + "/api/v1/chart/?q=(page_size:1)", timeout=30)
    assert r2.ok, "API 登录失败: %s" % r2.status_code
    rt = s.get(BASE + "/api/v1/security/csrf_token/", timeout=30)
    assert rt.ok, "csrf_token API 失败"
    api_csrf = rt.json()["result"]
    s.headers["X-CSRFToken"] = api_csrf
    s.headers["Referer"] = BASE + "/"
    print("login ok, api csrf acquired")


def agg(col, label=None):
    return {"expressionType": "SIMPLE", "column": {"column_name": col}, "aggregate": "SUM", "label": label}


def sqlm(expr, label):
    return {"expressionType": "SQL", "sqlExpression": expr, "label": label}


def api_get(url, q=None):
    return s.get(BASE + url + ("?q=" + json.dumps(q, separators=(",", ":")) if q else ""), timeout=60)


_ALL_CHARTS = None
_ALL_DASHBOARDS = None


def list_all_charts():
    global _ALL_CHARTS
    if _ALL_CHARTS is None:
        out = []
        page = 0
        while True:
            r = s.get(BASE + "/api/v1/chart/?q=(page:%d,page_size:100)" % page, timeout=60)
            r.raise_for_status()
            j = r.json()
            for c in j.get("ids", []):
                d = s.get(BASE + "/api/v1/chart/%d" % c, timeout=30).json()["result"]
                out.append((c, d.get("slice_name", "")))
            if len(j.get("ids", [])) < 100:
                break
            page += 1
        _ALL_CHARTS = out
    return _ALL_CHARTS


def find_chart(slice_name):
    for cid, nm in list_all_charts():
        if nm == slice_name:
            return cid
    return None


def find_dashboard(title):
    global _ALL_DASHBOARDS
    if _ALL_DASHBOARDS is None:
        r = s.get(BASE + "/api/v1/dashboard/?q=(page_size:100)", timeout=60)
        r.raise_for_status()
        _ALL_DASHBOARDS = [(d["id"], d.get("dashboard_title", "")) for d in r.json().get("result", [])]
    for did, t in _ALL_DASHBOARDS:
        if t == title:
            return did
    return None


def record_ledger():
    LEDGER["created_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(LEDGER, f, ensure_ascii=False, indent=1)


def precheck(name, ds_id, query, min_rows=1):
    # 最小合法键构造（与后端 schema 实测兼容；真实运行时前端 buildQuery 生成完整 QueryContext）
    qk = dict({"filters": [], "row_limit": 50000, "extras": {"having": "", "where": ""}}, **query)
    payload = {"datasource": {"id": ds_id, "type": "table"}, "force": False,
               "queries": [qk],
               "form_data": {"datasource": "%d__table" % ds_id, "viz_type": "table"},
               "result_format": "json", "result_type": "full"}
    t0 = time.time()
    rr = s.post(BASE + "/api/v1/chart/data", json=payload, timeout=300)
    dt = round(time.time() - t0, 1)
    ok = rr.ok
    rows = rr.json()["result"][0].get("rowcount") if ok else None
    rec = {"name": name, "dataset": ds_id, "http": rr.status_code, "rows": rows, "seconds": dt}
    LEDGER["precheck"].append(rec)
    print("  precheck %-36s %5.1fs http=%s rows=%s" % (name, dt, rr.status_code, rows))
    if not ok or (rows or 0) < min_rows:
        print("  ERROR BODY:", rr.text[:400])
        raise SystemExit("ABORT: precheck failed %s" % json.dumps(rec, ensure_ascii=False))
    record_ledger()
    return dt


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
    r2 = s.get(BASE + "/api/v1/chart/%d" % sid, timeout=30)
    uuid = r2.json()["result"].get("uuid")
    LEDGER["charts"].append({"type": "chart", "id": sid, "uuid": uuid, "title": spec["name"]})
    record_ledger()
    print("  created chart id=%s %s" % (sid, spec["name"]))
    dt = precheck("chart:" + spec["name"], spec["ds"], spec["query"], spec.get("min_rows", 1))
    rec = next(c for c in LEDGER["charts"] if c["id"] == sid)
    rec["precheck_seconds"] = dt
    record_ledger()
    return sid


def qc(ds, q):
    return {"datasource": {"id": ds, "type": "table"}, "force": False,
            "queries": [dict({"filters": [], "extras": {"having": "", "where": ""}, "applied_time_extras": {},
                              "orderby": [], "annotation_layers": [], "series_limit": 0,
                              "group_others_when_limit_reached": False, "order_desc": True,
                              "url_params": {}, "custom_params": {}, "custom_form_data": {},
                              "post_processing": [], "time_offsets": [], "row_limit": 50000}, **q)],
            "form_data": {"datasource": "%d__table" % ds}, "result_format": "json", "result_type": "full"}


def big_number(ds, metric, label, where=None):
    q = {"metrics": [metric]}
    if where:
        q["extras"] = {"having": "", "where": where}
    params = {"viz_type": "big_number_total", "datasource": "%d__table" % ds, "metric": metric,
              "compare_lag": "", "compare_suffix": "", "y_axis_format": ",d", "date_format": "smart_date",
              "subheader": "", "time_range": None}
    return {"ds": ds, "viz": "big_number_total", "params": params, "query": q, "min_rows": 1}


def dist_bar(ds, groupby, metric, where=None, limit=15, label=None):
    q = {"columns": groupby, "metrics": [metric], "row_limit": limit, "order_desc": True}
    if where:
        q["extras"] = {"having": "", "where": where}
    params = {"viz_type": "dist_bar", "datasource": "%d__table" % ds, "metrics": [metric], "groupby": groupby,
              "row_limit": limit, "order_desc": True, "y_axis_format": ",d", "show_legend": False,
              "x_ticks_layout": "auto", "color_scheme": "supersetColors", "seriesType": "bar",
              "show_value": True, "rich_tooltip": True, "time_range": None}
    return {"ds": ds, "viz": "dist_bar", "params": params, "query": q, "min_rows": 3}


def pie_chart(ds, metrics, where=None):
    q = {"metrics": metrics}
    if where:
        q["extras"] = {"having": "", "where": where}
    params = {"viz_type": "pie", "datasource": "%d__table" % ds, "metrics": metrics, "groupby": [],
              "donut": True, "show_legend": True, "legendPosition": "right", "show_labels": True,
              "label_type": "name_value", "number_format": ",d", "outerRadius": 70, "innerRadius": 40,
              "color_scheme": "supersetColors", "time_range": None}
    return {"ds": ds, "viz": "pie", "params": params, "query": q, "min_rows": 1}


def table_chart(ds, groupby, metrics, where=None, order_desc=True, limit=50):
    q = {"columns": groupby, "metrics": metrics, "row_limit": limit, "order_desc": order_desc}
    if where:
        q["extras"] = {"having": "", "where": where}
    params = {"viz_type": "table", "datasource": "%d__table" % ds, "query_mode": "aggregate",
              "groupby": groupby, "metrics": metrics, "row_limit": limit, "page_length": 25,
              "server_pagination": False, "include_search": True, "include_time": False,
              "order_desc": order_desc, "table_timestamp_format": "%Y-%m-%d", "time_range": None,
              "column_config": {}}
    return {"ds": ds, "viz": "table", "params": params, "query": q, "min_rows": 3}


def create_dashboard(spec):
    """spec: {title, slug, desc_md, chart_ids:[(id,w,h)] rows: [[(cid,w,h),...]], filter:{...}}"""
    did = find_dashboard(spec["title"])
    if did:
        print("  dashboard exists id=%s %s" % (did, spec["title"]))
        rec = next((d for d in LEDGER["dashboards"] if d["id"] == did), None)
        if not rec:
            r = s.get(BASE + "/api/v1/dashboard/%d" % did, timeout=30)
            LEDGER["dashboards"].append({"type": "dashboard", "id": did, "uuid": r.json()["result"].get("id", "") and r.json()["result"].get("uuid"),
                                         "title": spec["title"], "preexisting": True})
            record_ledger()
        return did
    r = s.post(BASE + "/api/v1/dashboard/", json={"dashboard_title": spec["title"], "slug": spec["slug"]}, timeout=60)
    if r.status_code not in (200, 201):
        print(r.text[:500])
        raise SystemExit("ABORT: dashboard create failed " + spec["title"])
    did = r.json()["id"]
    r2 = s.get(BASE + "/api/v1/dashboard/%d" % did, timeout=30)
    uuid = r2.json()["result"].get("uuid")
    LEDGER["dashboards"].append({"type": "dashboard", "id": did, "uuid": uuid, "title": spec["title"]})
    record_ledger()
    print("  created dashboard id=%s %s" % (did, spec["title"]))
    # 图表关联：position_json 的 CHART 节点在后端 save 时自动同步 dashboard_slices
    # position_json
    pos = {"DASHBOARD_VERSION_KEY": "v2", "ROOT_ID": {"id": "ROOT_ID", "type": "ROOT", "children": ["GRID_ID"]},
           "GRID_ID": {"id": "GRID_ID", "type": "GRID", "children": []}}
    children = []
    ri = 0
    md_id = "MD-TOP"
    pos[md_id] = {"id": md_id, "type": "MARKDOWN", "children": [],
                  "meta": {"width": 12, "height": 4, "background": "BACKGROUND_TRANSPARENT",
                           "text": spec["desc_md"], "code": spec["desc_md"]}}
    children.append(md_id)
    for row in spec["rows"]:
        ri += 1
        rid = "ROW-BI%d-%d" % (spec["no"], ri)
        node_children = []
        for ci, (cid, w, h) in enumerate(row):
            key = "CHART-BI%d-%d-%d" % (spec["no"], ri, ci)
            pos[key] = {"id": key, "type": "CHART", "children": [], "meta": {"chartId": cid, "width": w, "height": h}}
            node_children.append(key)
        pos[rid] = {"id": rid, "type": "ROW", "children": node_children, "meta": {"background": "BACKGROUND_TRANSPARENT"}}
        children.append(rid)
    pos["GRID_ID"]["children"] = children
    r4 = s.put(BASE + "/api/v1/dashboard/%d" % did, json={"position_json": json.dumps(pos, ensure_ascii=False)}, timeout=60)
    if not r4.ok:
        print(r4.text[:400])
        raise SystemExit("ABORT: position_json failed")
    # json_metadata：原生 filter_time + 横向筛选条
    r5 = s.put(BASE + "/api/v1/dashboard/%d" % did, json={"json_metadata": json.dumps(spec["json_metadata"], ensure_ascii=False)}, timeout=60)
    if not r5.ok:
        print(r5.text[:400])
        raise SystemExit("ABORT: json_metadata failed")
    # 发布 + Gamma
    r6 = s.put(BASE + "/api/v1/dashboard/%d" % did, json={"published": True}, timeout=60)
    if not r6.ok:
        raise SystemExit("ABORT: publish failed")
    r7 = s.put(BASE + "/api/v1/dashboard/%d/roles" % did, json={"roles": [GAMMA_ID]}, timeout=60)
    print("  dashboard %s configured (published, roles gamma=%s)" % (did, r7.status_code))
    rec = next(d for d in LEDGER["dashboards"] if d["id"] == did)
    rec["published"] = True
    rec["roles"] = [GAMMA_ID]
    record_ledger()
    return did


def filter_md(fid, name, targets, default_range=None, extra=None):
    ddm = {"extraFormData": {}, "filterState": {}}
    if default_range:
        ddm = {"extraFormData": {"time_range": default_range}, "filterState": {"value": default_range}}
    md = {"filter_bar_orientation": "HORIZONTAL",
          "native_filter_configuration": [{
              "id": fid, "name": name, "filterType": "filter_time",
              "targets": targets, "defaultDataMask": ddm, "cascadeParentIds": [],
              "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
              "controlValues": {"enableEmptyFilter": False},
              "type": "NATIVE_FILTER", "chartsInScope": None, "tabsInScope": [],
              "description": extra or "选择日期范围后点击“查询”，全部图表联动刷新。"}]}
    return md


def main():
    login()
    # ---------- BI-1 全院医疗运营核心指标总览 ----------
    print("== BI-1 预检 ==")
    precheck("BI1 KPI 门诊", 347, {"metrics": [agg("MEN_ZHENS")], "extras": {"having": "", "where": W_KSDM}})
    precheck("BI1 KPI 急诊观察", 347, {"metrics": [sqlm("SUM(JIZHENS)+SUM(GUANCHA)", "急诊与观察室人次")], "extras": {"having": "", "where": W_KSDM}})
    precheck("BI1 KPI 出院", 338, {"metrics": [agg("CHUYUAN")], "extras": {"having": "", "where": W_KSDM}})
    precheck("BI1 KPI 在院", 338, {"metrics": [agg("CURR")], "extras": {"having": "", "where": W_KSDM}})
    precheck("BI1 TOP15 门诊", 347, {"columns": ["KSDM"], "metrics": [agg("MEN_ZHENS")], "extras": {"having": "", "where": W_KSDM}, "row_limit": 15, "order_desc": True})
    precheck("BI1 TOP15 出院", 338, {"columns": ["KSDM"], "metrics": [agg("CHUYUAN")], "extras": {"having": "", "where": W_KSDM}, "row_limit": 15, "order_desc": True})
    precheck("BI1 转归饼", 338, {"metrics": [agg("RECOVER", "治愈"), agg("EFFECT", "好转"), agg("UNTREAT", "未愈"),
                                             agg("DIED", "死亡"), agg("OTHER_N", "其他"), agg("WILL_N", "自动出院"), agg("XFER", "转院")],
                                  "extras": {"having": "", "where": W_KSDM}})
    precheck("BI1 明细表", 348, {"columns": ["KS"], "metrics": [agg("DISCH_N", "出院人数"), agg("BED_END", "月末实有病床"),
                                                 agg("DEATH_RATE", "病死率(%)"), agg("OCC_DAYS", "出院者占用总床日")],
                                  "extras": {"having": "", "where": W_KS}, "row_limit": 50, "order_desc": True})
    print("== BI-1 创建 ==")
    b1 = []
    b1.append(mk_chart(big_number(347, agg("MEN_ZHENS", "门急诊总诊疗人次"), "门急诊总诊疗人次", W_KSDM) | {"name": "【BI】门急诊总诊疗人次"}))
    b1.append(mk_chart(big_number(347, sqlm("SUM(JIZHENS)+SUM(GUANCHA)", "急诊与观察室人次"), "急诊与观察室人次", W_KSDM) | {"name": "【BI】急诊与观察室人次"}))
    b1.append(mk_chart(big_number(338, agg("CHUYUAN", "住院出院总人数"), "住院出院总人数", W_KSDM) | {"name": "【BI】住院出院总人数"}))
    b1.append(mk_chart(big_number(338, agg("CURR", "月末实际在院人数"), "月末实际在院人数", W_KSDM) | {"name": "【BI】月末实际在院人数"}))
    b1c1 = mk_chart(dist_bar(347, ["KSDM"], agg("MEN_ZHENS", "门急诊诊疗人次"), W_KSDM) | {"name": "【BI】临床科室门急诊诊疗人次 TOP15"})
    b1c2 = mk_chart(dist_bar(338, ["KSDM"], agg("CHUYUAN", "出院人数"), W_KSDM) | {"name": "【BI】临床科室出院人数 TOP15"})
    b1c3 = mk_chart(pie_chart(338, [agg("RECOVER", "治愈"), agg("EFFECT", "好转"), agg("UNTREAT", "未愈"),
                                    agg("DIED", "死亡"), agg("OTHER_N", "其他"), agg("WILL_N", "自动出院"), agg("XFER", "转院")], W_KSDM)
                    | {"name": "【BI】全院出院患者转归构成"})
    b1c4 = mk_chart(table_chart(348, ["KS"], [agg("DISCH_N", "出院人数"), agg("BED_END", "月末实有病床"),
                                               agg("DEATH_RATE", "病死率(%)"), agg("OCC_DAYS", "出院者占用总床日")], W_KS)
                    | {"name": "【BI】各科室核心运营指标排行明细表"})
    d1 = create_dashboard({
        "no": 1, "title": "全院医疗运营核心指标总览（BI 驾驶舱）", "slug": "bi-overview",
        "desc_md": "**全院医疗运营核心指标总览**　基于月工作报表（门诊/住院）已对账数据集；默认展示上一完整月（2026-09），顶部日期筛选联动全部图表。柱图与排行均已排除“合计/总计”行。",
        "rows": [[(b1[0], 3, 8), (b1[1], 3, 8), (b1[2], 3, 8), (b1[3], 3, 8)],
                 [(b1c1, 6, 14), (b1c2, 6, 14)],
                 [(b1c3, 5, 14), (b1c4, 7, 14)]],
        "json_metadata": filter_md("NATIVE-FILTER-BI1-DATE", "统计日期",
                                    [{"datasetId": 347, "column": {"name": "STAT_BEGIN"}},
                                     {"datasetId": 338, "column": {"name": "STAT_BEGIN"}},
                                     {"datasetId": 348, "column": {"name": "STAT_BEGIN"}}],
                                    default_range="2026-09-01 : 2026-10-01",
                                    extra="按月选择日期范围后点击“查询”，全部图表联动刷新。"),
    })

    # ---------- BI-2 门急诊流量与窗口负荷 ----------
    print("== BI-2 预检 ==")
    RC = lambda c: {"expressionType": "SIMPLE", "column": {"column_name": c}, "aggregate": "SUM"}
    precheck("BI2 KPI 挂号", 325, {"metrics": [RC("COUNT(*)")]})
    precheck("BI2 KPI 缴费", 324, {"metrics": [RC("COUNT(*)")]})
    precheck("BI2 KPI 取药", 323, {"metrics": [sqlm('SUM("COUNT(DISTINCT(B.RCPT_NO))")', "取药人次")]})
    precheck("BI2 KPI 采血", 322, {"metrics": [RC("COUNT(*)")]})
    precheck("BI2 挂号时段", 325, {"columns": ["DTIME"], "metrics": [RC("COUNT(*)")], "row_limit": 20})
    precheck("BI2 采血时段", 322, {"columns": ["DTIME"], "metrics": [RC("COUNT(*)")], "row_limit": 20})
    precheck("BI2 明细", 325, {"columns": ["DTIME", "STAT_DATE"], "metrics": [RC("COUNT(*)")], "row_limit": 30})
    print("== BI-2 创建 ==")
    b2 = []
    b2.append(mk_chart(big_number(325, RC("COUNT(*)"), "今日挂号人次") | {"name": "【BI】门诊挂号人次"}))
    b2.append(mk_chart(big_number(324, RC("COUNT(*)"), "今日缴费人次") | {"name": "【BI】门诊缴费人次"}))
    b2.append(mk_chart(big_number(323, sqlm('SUM("COUNT(DISTINCT(B.RCPT_NO))")', "取药人次"), "今日取药人次") | {"name": "【BI】门诊取药人次"}))
    b2.append(mk_chart(big_number(322, RC("COUNT(*)"), "今日采血人次") | {"name": "【BI】门诊采血人次"}))
    b2c1 = mk_chart(dist_bar(325, ["DTIME"], RC("COUNT(*)"), limit=20) | {"name": "【BI】门诊挂号全天分时段流量"})
    b2c2 = mk_chart(dist_bar(322, ["DTIME"], RC("COUNT(*)"), limit=20) | {"name": "【BI】门诊采血全天分时段流量"})
    b2c3 = mk_chart(table_chart(325, ["DTIME", "STAT_DATE"], [RC("COUNT(*)")], order_desc=False, limit=30)
                    | {"name": "【BI】各窗口分时段负荷明细对照表"})
    d2 = create_dashboard({
        "no": 2, "title": "门急诊流量与窗口负荷监测中心（BI 驾驶舱）", "slug": "bi-outpatient-flow",
        "desc_md": "**门急诊流量与窗口负荷监测中心**　挂号/缴费/取药/采血四大窗口当日人次与全天分时段（半小时桶）波峰分布；本中心按单日统计，默认今日，请选择单一日期后点击“查询”。",
        "rows": [[(b2[0], 3, 8), (b2[1], 3, 8), (b2[2], 3, 8), (b2[3], 3, 8)],
                 [(b2c1, 6, 14), (b2c2, 6, 14)],
                 [(b2c3, 12, 14)]],
        "json_metadata": filter_md("NATIVE-FILTER-BI2-DATE", "统计日期",
                                    [{"datasetId": 325, "column": {"name": "STAT_DATE"}},
                                     {"datasetId": 322, "column": {"name": "STAT_DATE"}},
                                     {"datasetId": 323, "column": {"name": "STAT_DATE"}},
                                     {"datasetId": 324, "column": {"name": "STAT_DATE"}}],
                                    default_range=None,
                                    extra="本中心按单日统计：请选择单一日期（起始=结束当天）；默认今日。"),
    })

    # ---------- BI-3 手术与住院医疗质量 ----------
    print("== BI-3 预检 ==")
    precheck("BI3 KPI 手术台数", 345, {"metrics": [agg("OPER_NUM")]})
    precheck("BI3 科室手术 TOP15", 345, {"columns": ["TJ_KSMC"], "metrics": [agg("OPER_NUM")], "row_limit": 15, "order_desc": True})
    precheck("BI3 门诊住院饼", 345, {"columns": ["BRANCH_NAME"], "metrics": [agg("OPER_NUM")]})
    precheck("BI3 病区出院 TOP15", 350, {"columns": ["KS"], "metrics": [agg("DISCH_N")], "extras": {"having": "", "where": W_KS}, "row_limit": 15, "order_desc": True})
    precheck("BI3 质量表", 350, {"columns": ["KS"], "metrics": [agg("DISCH_N"), agg("BED_END"), agg("CURE_RATE"), agg("DEATH_RATE")],
                                  "extras": {"having": "", "where": W_KS}, "row_limit": 50, "order_desc": True})
    print("== BI-3 创建 ==")
    b3 = []
    b3.append(mk_chart(big_number(345, agg("OPER_NUM", "手术总台数"), "手术总台数") | {"name": "【BI】手术总台数"}))
    b3c1 = mk_chart(dist_bar(345, ["TJ_KSMC"], agg("OPER_NUM", "手术台数"), limit=15) | {"name": "【BI】手术科室分布 TOP15"})
    b3c2 = mk_chart(pie_chart(345, [agg("OPER_NUM", "手术台数")]) | {"name": "【BI】门诊与住院手术量构成"})
    # 门诊/住院两扇区需要 BRANCH_NAME 维度：pie 单 metric + groupby
    b3c2 = mk_chart({"ds": 345, "viz": "pie",
                     "params": {"viz_type": "pie", "datasource": "345__table", "metrics": [agg("OPER_NUM", "手术台数")],
                                "groupby": ["BRANCH_NAME"], "donut": True, "show_legend": True,
                                "legendPosition": "right", "show_labels": True, "label_type": "name_value",
                                "number_format": ",d", "outerRadius": 70, "innerRadius": 40,
                                "color_scheme": "supersetColors", "time_range": None},
                     "query": {"columns": ["BRANCH_NAME"], "metrics": [agg("OPER_NUM")], "row_limit": 10},
                     "min_rows": 1} | {"name": "【BI】门诊与住院手术量构成"})
    b3c3 = mk_chart(dist_bar(350, ["KS"], agg("DISCH_N", "出院人数"), W_KS) | {"name": "【BI】各病区出院人数 TOP15"})
    b3c4 = mk_chart(table_chart(350, ["KS"], [agg("DISCH_N", "出院人数"), agg("BED_END", "月末实有病床"),
                                               agg("CURE_RATE", "治愈率(%)"), agg("DEATH_RATE", "病死率(%)")], W_KS)
                    | {"name": "【BI】各病区核心质量指标汇总表"})
    d3 = create_dashboard({
        "no": 3, "title": "手术与住院医疗质量可视化分析（BI 驾驶舱）", "slug": "bi-surgery-quality",
        "desc_md": "**手术与住院医疗质量可视化分析**　手术科室分布、门诊/住院手术构成与各病区出院、床位与转归质量指标（数据源：手术量统计、护理工作量月报已对账数据集；均排除合计行）。",
        "rows": [[(b3[0], 3, 8), (b3c1, 5, 8), (b3c2, 4, 8)],
                 [(b3c3, 6, 14), (b3c4, 6, 14)]],
        "json_metadata": filter_md("NATIVE-FILTER-BI3-DATE", "统计日期",
                                    [{"datasetId": 345, "column": {"name": "STAT_BEGIN"}},
                                     {"datasetId": 350, "column": {"name": "STAT_BEGIN"}}],
                                    default_range=None,
                                    extra="选择日期范围后点击“查询”，全部图表联动刷新。"),
    })

    print("== DONE ==")
    print("dashboards:", d1, d2, d3)
    record_ledger()


if __name__ == "__main__":
    main()
