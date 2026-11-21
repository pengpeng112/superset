# -*- coding: utf-8 -*-
"""阶段1b：建 BI_护理级别人日构成长表（ds374 已验证模式：Jinja 头 + 内联视图 + CROSS JOIN 标签 + CASE 展开），
并把 398 饼图改为 单度量 SUM(VAL) + groupby=级别（两步 PUT：datasource_id 与 params 分开防 500）。
同步：看板 filter targets 补新数据集；ledger 登记 new_datasets；冷查实测记录。
凭据环境变量 ACC_ADMIN。
"""
import io
import json
import os
import sys
import time

sys.path.insert(0, r"F:\python\superset\migration\sources\20261107-BI-DASHBOARDS")
from bi_api import admin, q, BASE  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER_PATH = os.path.join(HERE, "bi_enhance_ledger.json")
TABLE_NAME = "BI_护理级别人日构成长表"

sql351 = io.open(os.path.join(HERE, "evidence", "ds351_sql_full.sql"), encoding="utf-8").read()
lines = sql351.splitlines()
# 头 3 行 Jinja
header = "\n".join(lines[:3])
body = "\n".join(lines[3:])
# 剥离内联视图不允许的尾部 ORDER BY
import re
body = re.sub(r"\nORDER BY[^\n]*\s*$", "\n", body)
# 内层 g CTE 的 GROUPING SETS 合计行 ks='合计'；错误行 ks=NULL——WHERE 过滤

SQL_LT = (header + "\n"
          + "SELECT v.stat_begin, m.lvl AS 级别,\n"
          + "  CASE m.lvl WHEN '特级护理' THEN v.spec_care WHEN '病危' THEN v.crit_ill WHEN '病重' THEN v.crit_severe\n"
          + "       WHEN '普通护理' THEN v.gen_lvl1 WHEN '二级护理' THEN v.lvl2 ELSE v.lvl3 END AS val\n"
          + "FROM (\n" + body + "\n) v\n"
          + "CROSS JOIN (\n"
          + "  SELECT '特级护理' AS lvl FROM dual UNION ALL SELECT '病危' FROM dual UNION ALL SELECT '病重' FROM dual\n"
          + "  UNION ALL SELECT '普通护理' FROM dual UNION ALL SELECT '二级护理' FROM dual UNION ALL SELECT '三级护理' FROM dual\n"
          + ") m\n"
          + "WHERE v.ks NOT IN ('合计','总计','全院','计')\n"
          + "  AND CASE m.lvl WHEN '特级护理' THEN v.spec_care WHEN '病危' THEN v.crit_ill WHEN '病重' THEN v.crit_severe\n"
          + "       WHEN '普通护理' THEN v.gen_lvl1 WHEN '二级护理' THEN v.lvl2 ELSE v.lvl3 END > 0")

io.open(os.path.join(HERE, "evidence", "ds_nursing_levels.sql"), "w", encoding="utf-8", newline="").write(SQL_LT)
print("SQL_LT len=%d" % len(SQL_LT))


def agg(col, label=None):
    return {"expressionType": "SIMPLE", "column": {"column_name": col}, "aggregate": "SUM", "label": label or col}


def main():
    global s
    s = admin()
    ledger = json.load(open(LEDGER_PATH, encoding="utf-8"))

    # 找已有数据集（幂等）
    r = s.get(BASE + "/api/v1/dataset/?q=" + json.dumps({"filters": [{"col": "table_name", "opr": "eq", "value": TABLE_NAME}]}), timeout=60)
    dj = r.json()
    dsid = dj["result"][0]["id"] if dj.get("count") else None

    if not dsid:
        r = s.post(BASE + "/api/v1/dataset/", json={
            "database": 2, "schema": "", "table_name": TABLE_NAME, "sql": SQL_LT, "owners": []}, timeout=120)
        if r.status_code not in (200, 201):
            print("create dataset -> %s %s" % (r.status_code, r.text[:400]))
            raise SystemExit("ABORT: dataset create failed")
        dsid = r.json().get("id")
        s.put(BASE + "/api/v1/dataset/%d" % dsid, json={"main_dttm_col": "STAT_BEGIN"}, timeout=60)
        got = s.get(BASE + "/api/v1/dataset/%d" % dsid, timeout=60).json()["result"]
        print("created dataset id=%s cols=%s main=%s" % (dsid,
              [(c["column_name"], c["type"]) for c in got["columns"]], got.get("main_dttm_col")))
    else:
        print("dataset exists id=%s" % dsid)
    ledger["new_datasets"] = [{"type": "dataset", "id": dsid, "table_name": TABLE_NAME,
                               "sql_file": "evidence/ds_nursing_levels.sql", "pattern": "ds374 同构（Jinja头+内联视图+标签CROSS JOIN+CASE展开）"}]
    json.dump(ledger, open(LEDGER_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 冷查实测
    x = q(s, dsid, {"columns": ["级别"], "metrics": [agg("VAL", "人日")], "row_limit": 10}, viz="pie", force=True)
    print("cold query: http=%s %.1fs rows=%s %s" % (x.get("http"), x.get("sec"), x.get("rows"),
                                                    json.dumps(x.get("data"), ensure_ascii=False)[:300]))
    ledger["new_datasets"][0]["cold_query_seconds"] = x.get("sec")
    ledger["new_datasets"][0]["cold_query_rows"] = x.get("rows")
    json.dump(ledger, open(LEDGER_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 398 两步重指向（datasource_id 与 params 分开）
    r1 = s.put(BASE + "/api/v1/chart/398", json={"datasource_id": dsid, "datasource_type": "table"}, timeout=60)
    print("step1 datasource_id PUT:", r1.status_code, "" if r1.ok else r1.text[:200])
    params = {"viz_type": "pie", "datasource": "%d__table" % dsid, "granularity_sqla": "STAT_BEGIN",
              "metric": agg("VAL", "人日"), "groupby": ["级别"], "adhoc_filters": [],
              "row_limit": 10, "donut": True, "show_legend": True, "legendPosition": "right",
              "show_labels": True, "label_type": "name_value", "number_format": ",d",
              "outerRadius": 70, "innerRadius": 40, "color_scheme": "supersetColors",
              "time_range": "No filter", "date_format": "smart_date"}
    r2 = s.put(BASE + "/api/v1/chart/398", json={"params": json.dumps(params, ensure_ascii=False)}, timeout=60)
    print("step2 params PUT:", r2.status_code, "" if r2.ok else r2.text[:200])
    # query_context 同步
    qcx = {"datasource": {"id": dsid, "type": "table"}, "force": False,
           "queries": [{"columns": ["级别"], "metrics": [agg("VAL", "人日")], "filters": [],
                        "extras": {"having": "", "where": ""}, "orderby": [], "row_limit": 10, "order_desc": True}],
           "form_data": {"datasource": "%d__table" % dsid, "viz_type": "pie"}, "result_format": "json", "result_type": "full"}
    r3 = s.put(BASE + "/api/v1/chart/398", json={"query_context": json.dumps(qcx, ensure_ascii=False)}, timeout=60)
    print("step3 query_context PUT:", r3.status_code)

    # 看板 filter targets 补新数据集
    d = s.get(BASE + "/api/v1/dashboard/75", timeout=30).json()["result"]
    jm = json.loads(d["json_metadata"])
    nfc = jm.get("native_filter_configuration", [])
    if nfc and all(t.get("datasetId") != dsid for t in nfc[0].get("targets", [])):
        nfc[0]["targets"].append({"datasetId": dsid, "column": {"name": "STAT_BEGIN"}})
        r4 = s.put(BASE + "/api/v1/dashboard/75", json={"json_metadata": json.dumps(jm, ensure_ascii=False)}, timeout=60)
        print("dashboard targets PUT:", r4.status_code)
    print("DONE ds=%s" % dsid)


if __name__ == "__main__":
    main()
