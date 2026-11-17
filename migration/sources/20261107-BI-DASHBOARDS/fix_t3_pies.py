# -*- coding: utf-8 -*-
"""20261107-BI-DASHBOARDS T3.3 饼图：新建只读长表数据集（ds338 UNPIVOT / ds345 双拷贝）→ 冷查预检 → 377/389 转 pie → 看板筛选 targets 增补。
凭据环境变量 ACC_ADMIN。--skip-create 跳过建数据集（重跑时）。"""
import io
import json
import os
import re
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from bi_api import *  # noqa

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP_CREATE = "--skip-create" in sys.argv

s = admin()

# ---------- SQL 构造 ----------
src338 = io.open(os.path.join(HERE, "evidence/bi_sql/ds338.sql"), encoding="utf-8").read().strip()
SQL_A = (src338
         + "\n)\nUNPIVOT (人数 FOR 转归 IN (RECOVER AS '治愈', EFFECT AS '好转', UNTREAT AS '未愈', DIED AS '死亡', OTHER_N AS '其他'))"
         .replace("WITH input_bounds", "SELECT stat_begin, 转归, 人数 FROM (\nWITH input_bounds", 1))
# 修正拼接：SELECT 头要在最前
SQL_A = "SELECT stat_begin, 转归, 人数 FROM (\n" + src338 + "\n)\nUNPIVOT (人数 FOR 转归 IN (RECOVER AS '治愈', EFFECT AS '好转', UNTREAT AS '未愈', DIED AS '死亡', OTHER_N AS '其他'))"

src345 = io.open(os.path.join(HERE, "evidence/bi_sql/ds345.sql"), encoding="utf-8").read().strip()
m = re.search(r"\n(WITH input_bounds .*)$", src345, re.S)
assert m, "ds345 body not found"
body = m.group(1)
hdr_tf = [ln for ln in src345.splitlines() if ln.startswith("{% set tf")]
SQL_B = ("\n".join(hdr_tf)
         + "\nSELECT '门诊' AS branch_name, t.oper_num, t.stat_begin FROM (\n{% set branch = '0' %}\n" + body
         + "\n) t WHERE t.tj_ksmc = '合计'\nUNION ALL\n"
         + "SELECT '住院' AS branch_name, t.oper_num, t.stat_begin FROM (\n{% set branch = '1' %}\n" + body
         + "\n) t WHERE t.tj_ksmc = '合计'\nORDER BY branch_name")
io.open(os.path.join(HERE, "evidence/bi_sql/ds_unpivot_zhuangui.sql"), "w", encoding="utf-8", newline="").write(SQL_A)
io.open(os.path.join(HERE, "evidence/bi_sql/ds_branch_total.sql"), "w", encoding="utf-8", newline="").write(SQL_B)
print("SQL_A len=%d, SQL_B len=%d（原文已落 evidence/bi_sql/）" % (len(SQL_A), len(SQL_B)))

# ---------- 建数据集（columns 显式注册） ----------
def create_dataset(table_name, sql, cols):
    r = s.post(BASE + "/api/v1/dataset/", json={
        "database": 2, "schema": "", "table_name": table_name, "sql": sql,
        "columns": cols, "owners": []}, timeout=120)
    if r.status_code not in (200, 201):
        print("create %s -> %s %s" % (table_name, r.status_code, r.text[:300]))
        return None
    dsid = r.json().get("id")
    r2 = s.put(BASE + "/api/v1/dataset/%d" % dsid, json={"main_dttm_col": "STAT_BEGIN"}, timeout=60)
    got = s.get(BASE + "/api/v1/dataset/%d" % dsid, timeout=60).json()["result"]
    print("created %s id=%s main_dttm PUT=%s cols=%s" % (
        table_name, dsid, r2.status_code,
        [(c["column_name"], c["type"], c["is_dttm"]) for c in got["columns"]]))
    return dsid

if SKIP_CREATE:
    ids = {}
    for t in ("BI_出院转归构成长表", "BI_手术分支合计两行"):
        r = s.get(BASE + "/api/v1/dataset/?q=" + json.dumps({"filters": [{"col": "table_name", "opr": "eq", "value": t}]}), timeout=60)
        ids[t] = r.json()["result"]["data"][0]["id"]
    DS_A, DS_B = ids["BI_出院转归构成长表"], ids["BI_手术分支合计两行"]
    print("reuse DS_A=%s DS_B=%s" % (DS_A, DS_B))
else:
    DS_A = create_dataset("BI_出院转归构成长表", SQL_A, [
        {"column_name": "STAT_BEGIN", "type": "DATETIME", "is_dttm": True, "groupby": False, "filterable": True},
        {"column_name": "转归", "type": "STRING", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "人数", "type": "INT", "is_dttm": False, "groupby": False, "filterable": True},
    ])
    DS_B = create_dataset("BI_手术分支合计两行", SQL_B, [
        {"column_name": "BRANCH_NAME", "type": "STRING", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "OPER_NUM", "type": "INT", "is_dttm": False, "groupby": False, "filterable": True},
        {"column_name": "STAT_BEGIN", "type": "DATETIME", "is_dttm": True, "groupby": False, "filterable": True},
    ])
    assert DS_A and DS_B and DS_A > 372 and DS_B > 372, "dataset id 异常"

print("DS_A=%s DS_B=%s" % (DS_A, DS_B))

# ---------- 冷查预检（force，<10s）+ 对账 ----------
t0 = time.time()
xa = q(s, DS_A, {"columns": ["转归"], "metrics": [S("人数")]}, force=True, viz="pie")
ta = time.time() - t0
rows_a = xa.get("data") or []
print("DS_A 冷查 %.1fs http=%s rows=%s %s" % (ta, xa.get("http"), xa.get("rows"), json.dumps(rows_a, ensure_ascii=False)))
t0 = time.time()
xb = q(s, DS_B, {"columns": ["BRANCH_NAME"], "metrics": [S("OPER_NUM")]}, force=True, viz="pie")
tb = time.time() - t0
rows_b = xb.get("data") or []
print("DS_B 冷查 %.1fs http=%s rows=%s %s" % (tb, xb.get("http"), xb.get("rows"), json.dumps(rows_b, ensure_ascii=False)))
ok_cold = ta < 10 and tb < 10 and xa.get("http") == 200 and xb.get("http") == 200
sum_a = sum((r.get("人数") or 0) for r in rows_a)
va = {r.get("BRANCH_NAME"): r.get("OPER_NUM") for r in rows_b}
print("冷查<10s: %s | DS_A 五项和=%s | DS_B 门诊=%s 住院=%s" % (ok_cold, sum_a, va.get("门诊"), va.get("住院")))
if not ok_cold:
    print("ABORT: 冷查超时，饼图不上线（保留表格）")
    sys.exit(1)

# ---------- 377 / 389 转 pie ----------
def pie_params(ds, group, col, label):
    return {"viz_type": "pie", "datasource": "%d__table" % ds, "granularity_sqla": "STAT_BEGIN",
            "metric": {"expressionType": "SIMPLE", "column": {"column_name": col}, "aggregate": "SUM", "label": label},
            "groupby": [group], "adhoc_filters": [], "row_limit": 100,
            "donut": True, "show_legend": True, "legendPosition": "right", "show_labels": True,
            "label_type": "name_value", "number_format": ",d", "outerRadius": 70, "innerRadius": 40,
            "color_scheme": "supersetColors", "time_range": "No filter", "date_format": "smart_date",
            "show_percentage": True, "show_total": True}

sc, err = put_params(s, 377, pie_params(DS_A, "转归", "人数", "人数"), {"viz_type": "pie", "datasource_id": DS_A, "slice_name": "【BI】全院出院患者转归构成（饼图）"})
c = get_chart(s, 377)
print("377 pie PUT=%s col=%s ds=%s pviz=%s" % (sc, c["viz_type"], c["datasource_id"], json.loads(c["params"]).get("viz_type")), err[:100])
sc, err = put_params(s, 389, pie_params(DS_B, "BRANCH_NAME", "OPER_NUM", "手术台数"), {"viz_type": "pie", "datasource_id": DS_B, "slice_name": "【BI】门诊与住院手术量构成（饼图）"})
c = get_chart(s, 389)
print("389 pie PUT=%s col=%s ds=%s pviz=%s" % (sc, c["viz_type"], c["datasource_id"], json.loads(c["params"]).get("viz_type")), err[:100])

# ---------- 看板筛选 targets 增补新数据集 ----------
for did, extra in ((72, DS_A), (74, DS_B)):
    d = get_dashboard(s, did)
    md = json.loads(d["json_metadata"])
    nf = md["native_filter_configuration"][0]
    tset = [t["datasetId"] for t in nf["targets"]]
    if extra not in tset:
        nf["targets"].append({"datasetId": extra, "column": {"name": "STAT_BEGIN"}})
    r = s.put(BASE + "/api/v1/dashboard/%d" % did, json={"json_metadata": json.dumps(md, ensure_ascii=False)}, timeout=60)
    md2 = json.loads(get_dashboard(s, did)["json_metadata"])
    print("d%d targets PUT=%s now=%s" % (did, r.status_code, [t["datasetId"] for t in md2["native_filter_configuration"][0]["targets"]]))

print("done")
