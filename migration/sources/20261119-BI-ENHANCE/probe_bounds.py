# -*- coding: utf-8 -*-
"""探 ds350 三种时间窗的生成 SQL 边界差异（解 8060/5315/10630 之谜）。"""
import json
import re
import sys

sys.path.insert(0, r"F:\python\superset\migration\sources\20261107-BI-DASHBOARDS")
from bi_api import admin, q  # noqa: E402


def agg(col, label=None):
    return {"expressionType": "SIMPLE", "column": {"column_name": col}, "aggregate": "SUM", "label": label or col}


s = admin()
x1 = q(s, 350, {"columns": [], "metrics": [agg("DISCH_N", "出院")], "row_limit": 5}, viz="table", force=True)
x2 = q(s, 350, {"columns": [], "metrics": [agg("DISCH_N", "出院")],
                "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": "2026-10-01 : 2026-11-01"}], "row_limit": 5}, viz="table", force=True)
x3 = q(s, 350, {"columns": [], "metrics": [agg("DISCH_N", "出院")],
                "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": "Latest month"}], "row_limit": 5}, viz="table", force=True)
print("no-filter  rows=%s %s" % (x1["rows"], json.dumps(x1["data"][:1])))
print("explicit   rows=%s %s" % (x2["rows"], json.dumps(x2["data"][:1])))
print("latestmon  rows=%s %s" % (x3["rows"], json.dumps(x3["data"][:1])))


def bounds(sql):
    return re.findall(r"'(NULL|\d{4}-\d{2}-\d{2}[^']*)'", sql)[:8]


print("no-filter bounds:", bounds(x1["sql"]))
print("explicit  bounds:", bounds(x2["sql"]))
print("latestmon bounds:", bounds(x3["sql"]))
open("evidence/ds350_sql_noFilter.sql", "w", encoding="utf-8").write(x1["sql"])
open("evidence/ds350_sql_explicit.sql", "w", encoding="utf-8").write(x2["sql"])
open("evidence/ds350_sql_latestMonth.sql", "w", encoding="utf-8").write(x3["sql"])
